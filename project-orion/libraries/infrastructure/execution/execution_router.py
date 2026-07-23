"""Execution Router - Routes execution requests to registered broker adapters.

Supports primary broker routing, automatic failover, health-based routing,
broker priority configuration, capability-based routing, and hot adapter
registration/removal.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.execution.models import Order, OrderType
from libraries.infrastructure.execution.broker_adapter import BrokerAdapter


@dataclass(frozen=True, slots=True)
class RoutingTarget:
    """A potential routing target with metadata."""

    broker_name: str
    priority: int = 100
    health_score: float = 1.0
    latency_ms: float = 0.0
    supported_symbols: frozenset[str] = frozenset()
    supported_order_types: frozenset[OrderType] = frozenset()
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports_symbol(self, symbol: str) -> bool:
        if not self.supported_symbols:
            return True
        return symbol.upper() in {s.upper() for s in self.supported_symbols}

    def supports_order_type(self, order_type: OrderType) -> bool:
        if not self.supported_order_types:
            return True
        return order_type in self.supported_order_types


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """The result of a routing decision."""

    selected_broker: str
    fallback_used: bool = False
    fallback_reason: str = ""
    candidates_evaluated: int = 0
    routing_latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class RouterNotReadyError(Exception):
    """Raised when the router has no registered adapters."""


class NoSuitableBrokerError(Exception):
    """Raised when no broker can handle the request."""


@dataclass(frozen=True, slots=True)
class ExecutionRouterConfig:
    """Configuration for the ExecutionRouter."""

    min_health_score: float = 0.5
    enable_fallback: bool = True
    fallback_min_health: float = 0.2
    prefer_lowest_latency: bool = True
    routing_timeout_seconds: float = 5.0


class ExecutionRouter:
    """Routes execution requests to registered broker adapters.

    Supports:
    - Primary broker routing with configurable priority
    - Automatic failover to backup brokers
    - Health-score-based routing
    - Capability-based routing (symbols, order types)
    - Hot adapter registration/removal at runtime
    - Observable routing decisions via events
    """

    def __init__(self, config: ExecutionRouterConfig | None = None) -> None:
        self._config = config or ExecutionRouterConfig()
        self._adapters: dict[str, BrokerAdapter] = {}
        self._targets: dict[str, RoutingTarget] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> ExecutionRouterConfig:
        return self._config

    async def register_adapter(
        self,
        adapter: BrokerAdapter,
        target: RoutingTarget | None = None,
    ) -> None:
        """Register a broker adapter for routing.

        Args:
            adapter: The broker adapter instance.
            target: Routing metadata (defaults from adapter).
        """
        async with self._lock:
            name = adapter.broker_name
            self._adapters[name] = adapter
            if target is None:
                target = RoutingTarget(broker_name=name)
            self._targets[name] = target

    async def unregister_adapter(self, broker_name: str) -> None:
        """Remove a broker adapter from routing.

        Args:
            broker_name: Name of the broker to remove.
        """
        async with self._lock:
            self._adapters.pop(broker_name, None)
            self._targets.pop(broker_name, None)

    async def update_health(self, broker_name: str, health_score: float) -> None:
        """Update health score for a registered broker.

        Args:
            broker_name: Name of the broker.
            health_score: New health score (0.0 to 1.0).
        """
        async with self._lock:
            if broker_name in self._targets:
                target = self._targets[broker_name]
                self._targets[broker_name] = RoutingTarget(
                    broker_name=target.broker_name,
                    priority=target.priority,
                    health_score=max(0.0, min(1.0, health_score)),
                    latency_ms=target.latency_ms,
                    supported_symbols=target.supported_symbols,
                    supported_order_types=target.supported_order_types,
                    is_active=target.is_active,
                    metadata=target.metadata,
                )

    async def route(self, order: Order) -> RoutingDecision:
        """Route an order to the optimal broker adapter.

        Args:
            order: The order to route.

        Returns:
            RoutingDecision with selected broker.

        Raises:
            RouterNotReadyError: If no adapters are registered.
            NoSuitableBrokerError: If no broker can handle the order.
        """
        async with self._lock:
            if not self._adapters:
                raise RouterNotReadyError("No broker adapters registered for routing")

            # Collect eligible candidates sorted by priority (lower = higher)
            candidates: list[tuple[str, BrokerAdapter, RoutingTarget]] = []

            for name, adapter in self._adapters.items():
                target = self._targets.get(name)
                if target is None:
                    target = RoutingTarget(broker_name=name)

                if not target.is_active:
                    continue
                if not adapter.is_connected:
                    continue
                if target.health_score < self._config.min_health_score:
                    continue
                if not target.supports_symbol(order.symbol):
                    continue
                if not target.supports_order_type(order.order_type):
                    continue

                candidates.append((name, adapter, target))

            if not candidates:
                if self._config.enable_fallback:
                    return await self._fallback_route(order)
                raise NoSuitableBrokerError(
                    f"No suitable broker found for order {order.order_id} "
                    f"(symbol={order.symbol}, type={order.order_type.value})"
                )

            # Sort by priority (ascending), health (descending), latency (ascending)
            candidates.sort(
                key=lambda c: (
                    c[2].priority,
                    -c[2].health_score,
                    c[2].latency_ms if self._config.prefer_lowest_latency else 0,
                )
            )

            selected = candidates[0]

            return RoutingDecision(
                selected_broker=selected[0],
                fallback_used=False,
                candidates_evaluated=len(candidates),
                timestamp=datetime.now(timezone.utc),
            )

    async def _fallback_route(self, order: Order) -> RoutingDecision:
        """Attempt fallback routing with relaxed constraints."""
        candidates: list[tuple[str, BrokerAdapter, RoutingTarget]] = []

        for name, adapter in self._adapters.items():
            target = self._targets.get(name, RoutingTarget(broker_name=name))
            if not target.is_active:
                continue
            if not adapter.is_connected:
                continue
            # Relax health check for fallback
            if target.health_score < self._config.fallback_min_health:
                continue
            candidates.append((name, adapter, target))

        if not candidates:
            raise NoSuitableBrokerError(
                f"Fallback routing failed for order {order.order_id} "
                f"(symbol={order.symbol}, type={order.order_type.value})"
            )

        candidates.sort(key=lambda c: (-c[2].health_score, c[2].latency_ms))

        return RoutingDecision(
            selected_broker=candidates[0][0],
            fallback_used=True,
            fallback_reason="Primary criteria not met; used relaxed constraints",
            candidates_evaluated=len(candidates),
            timestamp=datetime.now(timezone.utc),
        )

    async def get_adapter(self, broker_name: str) -> BrokerAdapter | None:
        """Get a registered adapter by name."""
        async with self._lock:
            return self._adapters.get(broker_name)

    async def get_active_adapters(self) -> list[tuple[str, BrokerAdapter, RoutingTarget]]:
        """Get all registered adapters with their routing targets."""
        async with self._lock:
            return [
                (name, adapter, self._targets.get(name, RoutingTarget(broker_name=name)))
                for name, adapter in self._adapters.items()
            ]

    async def adapter_count(self) -> int:
        """Return the number of registered adapters."""
        async with self._lock:
            return len(self._adapters)

