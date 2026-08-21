"""Order Router.

Selects the optimal execution provider based on broker availability,
latency, health, supported symbols, and smart routing compatibility.
Extensible for future smart routing strategies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from libraries.domain.execution.exceptions import RoutingError
from libraries.domain.execution.models import Order, OrderType


@dataclass(frozen=True, slots=True)
class BrokerCapabilities:
    """Capabilities of a broker execution endpoint."""

    broker_id: str
    broker_name: str
    supported_symbols: frozenset[str] = frozenset()
    supported_order_types: frozenset[OrderType] = frozenset()
    latency_ms: float = 0.0
    health_score: float = 1.0  # 0-1
    is_available: bool = True
    max_volume: float = float("inf")
    supports_market_orders: bool = True
    supports_limit_orders: bool = True
    supports_stop_orders: bool = True
    supports_trailing_stops: bool = False
    supports_oco: bool = False
    supports_ioc: bool = True
    supports_fok: bool = True
    weight: float = 1.0  # for weighted scoring

    def supports_order_type(self, order_type: OrderType) -> bool:
        if self.supported_order_types:
            return order_type in self.supported_order_types
        # Fallback to capability flags
        mapping = {
            OrderType.MARKET: self.supports_market_orders,
            OrderType.LIMIT: self.supports_limit_orders,
            OrderType.STOP: self.supports_stop_orders,
            OrderType.TRAILING_STOP: self.supports_trailing_stops,
            OrderType.OCO: self.supports_oco,
            OrderType.IOC: self.supports_ioc,
            OrderType.FOK: self.supports_fok,
        }
        return mapping.get(order_type, False)


@dataclass(frozen=True, slots=True)
class RouterScore:
    """Scored broker routing option."""

    broker_id: str
    broker_name: str
    score: float  # 0-100, higher = better
    latency_ms: float
    health_score: float
    estimated_slippage_pips: float = 0.0
    reason: str = ""

    @property
    def is_preferred(self) -> bool:
        return self.score >= 80.0

    @property
    def summary(self) -> str:
        return (
            f"Broker {self.broker_name} ({self.broker_id}): "
            f"score={self.score:.1f}, latency={self.latency_ms:.1f}ms, "
            f"health={self.health_score:.2f}"
        )


@dataclass(frozen=True, slots=True)
class RoutingResult:
    """Result of order routing."""

    selected_broker: str
    broker_order_id: str | None = None
    all_scores: tuple[RouterScore, ...] = ()
    routing_time_ms: float = 0.0
    fallback_used: bool = False
    fallback_reason: str = ""


@dataclass(frozen=True, slots=True)
class OrderRouterConfig:
    """Configuration for the OrderRouter."""

    min_health_score: float = 0.5
    max_latency_ms: float = 1000.0
    latency_weight: float = 0.3
    health_weight: float = 0.4
    availability_weight: float = 0.3
    enable_fallback: bool = True
    prefer_lowest_latency: bool = True


class OrderRouter:
    """Routes orders to the optimal broker.

    Extensible for future smart routing strategies by injecting
    custom scoring functions.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        config: OrderRouterConfig | None = None,
    ) -> None:
        self._config = config or OrderRouterConfig()
        self._brokers: dict[str, BrokerCapabilities] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> OrderRouterConfig:
        return self._config

    async def register_broker(self, capabilities: BrokerCapabilities) -> None:
        """Register a broker for routing.

        Args:
            capabilities: Broker capabilities.
        """
        async with self._lock:
            self._brokers[capabilities.broker_id] = capabilities

    async def unregister_broker(self, broker_id: str) -> None:
        """Unregister a broker.

        Args:
            broker_id: Broker identifier.
        """
        async with self._lock:
            self._brokers.pop(broker_id, None)

    async def update_broker_health(self, broker_id: str, health_score: float) -> None:
        """Update health score for a broker.

        Args:
            broker_id: Broker identifier.
            health_score: New health score (0-1).
        """
        async with self._lock:
            if broker_id in self._brokers:
                existing = self._brokers[broker_id]
                self._brokers[broker_id] = BrokerCapabilities(
                    **{**existing.__dict__, "health_score": health_score}
                )

    async def route(
        self,
        order: Order,
        symbol: str | None = None,
    ) -> RoutingResult:
        """Route an order to the optimal broker.

        Args:
            order: The order to route.
            symbol: Override symbol for routing.

        Returns:
            RoutingResult with selected broker.

        Raises:
            RoutingError: If no suitable broker is found.
        """
        async with self._lock:
            if not self._brokers:
                raise RoutingError("No brokers registered for routing")

            route_symbol = symbol or order.symbol

            # Score all eligible brokers
            scores: list[RouterScore] = []
            for broker in self._brokers.values():
                if not broker.is_available:
                    continue
                if broker.health_score < self._config.min_health_score:
                    continue
                if broker.latency_ms > self._config.max_latency_ms:
                    continue
                if route_symbol not in broker.supported_symbols:
                    continue
                if not broker.supports_order_type(order.order_type):
                    continue

                score = self._compute_score(broker, order)
                scores.append(score)

            if not scores:
                # Fallback: try with relaxed constraints
                if self._config.enable_fallback:
                    return await self._fallback_route(order, route_symbol)
                raise RoutingError(
                    f"No eligible broker found for order {order.order_id} "
                    f"(symbol={route_symbol}, type={order.order_type.value})"
                )

            # Sort by score descending, then by latency ascending
            scores.sort(key=lambda s: (-s.score, s.latency_ms))

            return RoutingResult(
                selected_broker=scores[0].broker_id,
                all_scores=tuple(scores),
                fallback_used=False,
            )

    async def _fallback_route(
        self,
        order: Order,
        symbol: str,
    ) -> RoutingResult:
        """Attempt fallback routing with relaxed constraints."""
        scores: list[RouterScore] = []
        for broker in self._brokers.values():
            if not broker.is_available:
                continue
            if symbol not in broker.supported_symbols:
                continue
            if not broker.supports_order_type(order.order_type):
                continue

            score = self._compute_score(broker, order, relaxed=True)
            scores.append(score)

        if not scores:
            raise RoutingError(
                f"Fallback routing failed for order {order.order_id} "
                f"(symbol={symbol}, type={order.order_type.value})"
            )

        scores.sort(key=lambda s: (-s.score, s.latency_ms))

        return RoutingResult(
            selected_broker=scores[0].broker_id,
            all_scores=tuple(scores),
            fallback_used=True,
            fallback_reason="Primary criteria not met; used relaxed constraints",
        )

    def _compute_score(
        self,
        broker: BrokerCapabilities,
        order: Order,
        relaxed: bool = False,
    ) -> RouterScore:
        """Compute a routing score for a broker.

        Score is 0-100 based on:
        - Health (0-40 points): broker health score
        - Latency (0-30 points): inverse of normalized latency
        - Availability (0-30 points): broker availability

        Extensible: override this method for custom smart routing.
        """
        max_lat = float("inf") if relaxed else self._config.max_latency_ms

        # Health score component (0-40)
        health_component = broker.health_score * 40.0

        # Latency component (0-30): inverse exponential
        if broker.latency_ms <= 0:
            latency_component = 30.0
        else:
            normalized_latency = min(broker.latency_ms / (max_lat or 100.0), 1.0)
            latency_component = 30.0 * (1.0 - normalized_latency)

        # Availability component (0-30)
        availability_component = 30.0 if broker.is_available else 0.0

        total = health_component + latency_component + availability_component

        # Bonus for preferred capabilities
        if order.order_type == OrderType.MARKET and broker.supports_market_orders:
            total += 5.0
        if order.order_type == OrderType.LIMIT and broker.supports_limit_orders:
            total += 5.0
        if broker.supports_trailing_stops and order.order_type == OrderType.TRAILING_STOP:
            total += 10.0

        # Apply broker weight
        total *= broker.weight

        return RouterScore(
            broker_id=broker.broker_id,
            broker_name=broker.broker_name,
            score=round(min(total, 100.0), 2),
            latency_ms=broker.latency_ms,
            health_score=broker.health_score,
            reason="Primary route" if not relaxed else "Fallback route",
        )

    async def get_available_brokers(self) -> list[BrokerCapabilities]:
        """Return list of registered brokers."""
        async with self._lock:
            return list(self._brokers.values())

    async def broker_count(self) -> int:
        """Return number of registered brokers."""
        async with self._lock:
            return len(self._brokers)
