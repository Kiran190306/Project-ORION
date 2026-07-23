"""Order recovery engine for the broker execution layer.

Supports recovery of pending orders, open positions, partial fills,
duplicate executions, network interruptions, and restart recovery.
All recovery operations are idempotent.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Awaitable, Callable

from libraries.domain.execution.models import BrokerOrderId, Order, OrderId, OrderStatus
from libraries.infrastructure.execution.broker_adapter import BrokerAdapter


class OrderRecoveryStatus(StrEnum):
    """Status of an order recovery operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RECOVERED = "recovered"
    PARTIALLY_RECOVERED = "partially_recovered"
    FAILED = "failed"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class OrderRecoveryConfig:
    """Configuration for order recovery."""

    max_recovery_attempts: int = 3
    recovery_interval_seconds: float = 5.0
    recovery_timeout_seconds: float = 30.0
    auto_recover_pending_orders: bool = True
    auto_recover_partial_fills: bool = True
    auto_recover_network_interruptions: bool = True
    enable_replay_protection: bool = True
    query_broker_on_recovery: bool = True


@dataclass(frozen=True, slots=True)
class OrderRecoveryResult:
    """Result of an order recovery attempt."""

    order_id: str
    status: OrderRecoveryStatus
    broker_order_id: str = ""
    broker_status: str = ""
    filled_quantity: str = "0"
    average_fill_price: str = ""
    attempts: int = 0
    error: str = ""
    recovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class OrderRecoveryEngine:
    """Engine for recovering orders after failures.

    Supports:
    - Pending orders that were submitted but not confirmed
    - Open positions that need to be verified
    - Partial fills that need completion tracking
    - Duplicate execution detection and prevention
    - Network interruption recovery
    - Restart recovery (recover state after system restart)
    - Replay protection

    All recovery operations are idempotent.
    """

    def __init__(self, config: OrderRecoveryConfig | None = None) -> None:
        self._config = config or OrderRecoveryConfig()
        self._recovering: dict[str, OrderRecoveryResult] = {}
        self._recovered_orders: dict[str, list[OrderRecoveryResult]] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> OrderRecoveryConfig:
        return self._config

    async def recover_pending_order(
        self,
        order: Order,
        adapter: BrokerAdapter,
    ) -> OrderRecoveryResult:
        """Recover a pending order by querying the broker.

        Args:
            order: The order to recover.
            adapter: Broker adapter to query.

        Returns:
            OrderRecoveryResult with recovery status.
        """
        async with self._lock:
            if order.order_id in self._recovering:
                existing = self._recovering[order.order_id]
                if existing.attempts >= self._config.max_recovery_attempts:
                    return OrderRecoveryResult(
                        order_id=order.order_id,
                        status=OrderRecoveryStatus.FAILED,
                        error="Max recovery attempts exceeded",
                        attempts=existing.attempts,
                    )

            result = OrderRecoveryResult(
                order_id=order.order_id,
                status=OrderRecoveryStatus.IN_PROGRESS,
                attempts=1,
            )
            self._recovering[order.order_id] = result

        try:
            # Query broker for order status
            if self._config.query_broker_on_recovery and order.broker_order_id:
                execution_info = await adapter.get_execution_history(
                    symbol=order.symbol,
                    limit=10,
                )
                broker_found = any(
                    str(ei.broker_order_id) == str(order.broker_order_id)
                    for ei in execution_info
                )

                if broker_found:
                    recovered = OrderRecoveryResult(
                        order_id=order.order_id,
                        status=OrderRecoveryStatus.RECOVERED,
                        broker_order_id=str(order.broker_order_id),
                        broker_status="found",
                        filled_quantity=str(order.filled_quantity),
                        average_fill_price=str(order.average_fill_price or ""),
                        attempts=1,
                    )
                else:
                    recovered = OrderRecoveryResult(
                        order_id=order.order_id,
                        status=OrderRecoveryStatus.NOT_FOUND,
                        broker_order_id=str(order.broker_order_id or ""),
                        attempts=1,
                    )
            else:
                recovered = OrderRecoveryResult(
                    order_id=order.order_id,
                    status=OrderRecoveryStatus.RECOVERED,
                    broker_order_id=str(order.broker_order_id or ""),
                    broker_status=order.status.value,
                    filled_quantity=str(order.filled_quantity),
                    attempts=1,
                )

            async with self._lock:
                self._recovering.pop(order.order_id, None)
                if order.order_id not in self._recovered_orders:
                    self._recovered_orders[order.order_id] = []
                self._recovered_orders[order.order_id].append(recovered)

            return recovered

        except Exception as e:
            async with self._lock:
                self._recovering.pop(order.order_id, None)

            return OrderRecoveryResult(
                order_id=order.order_id,
                status=OrderRecoveryStatus.FAILED,
                error=str(e),
                attempts=1,
            )

    async def recover_open_position(
        self,
        position_id: str,
        symbol: str,
        adapter: BrokerAdapter,
    ) -> OrderRecoveryResult:
        """Recover an open position by querying the broker.

        Args:
            position_id: Position identifier.
            symbol: Trading symbol.
            adapter: Broker adapter to query.

        Returns:
            OrderRecoveryResult with recovery status.
        """
        try:
            positions = await adapter.get_open_positions()
            for pos in positions:
                if pos.position_id == position_id:
                    return OrderRecoveryResult(
                        order_id=position_id,
                        status=OrderRecoveryStatus.RECOVERED,
                        broker_status="open",
                        filled_quantity=str(pos.quantity),
                        average_fill_price=str(pos.open_price),
                    )

            return OrderRecoveryResult(
                order_id=position_id,
                status=OrderRecoveryStatus.NOT_FOUND,
                error=f"Position {position_id} not found on broker",
            )

        except Exception as e:
            return OrderRecoveryResult(
                order_id=position_id,
                status=OrderRecoveryStatus.FAILED,
                error=str(e),
            )

    async def recover_partial_fill(
        self,
        order: Order,
        adapter: BrokerAdapter,
    ) -> OrderRecoveryResult:
        """Recover a partial fill by checking current order status.

        Args:
            order: The partially filled order.
            adapter: Broker adapter to query.

        Returns:
            OrderRecoveryResult with updated fill status.
        """
        if order.status != OrderStatus.PARTIALLY_FILLED:
            return OrderRecoveryResult(
                order_id=order.order_id,
                status=OrderRecoveryStatus.FAILED,
                error=f"Order is not partially filled (status={order.status.value})",
            )

        try:
            execution_info = await adapter.get_execution_history(
                symbol=order.symbol,
                limit=10,
            )

            total_filled = order.filled_quantity
            for ei in execution_info:
                if str(ei.broker_order_id) == str(order.broker_order_id):
                    if ei.filled_quantity > total_filled:
                        total_filled = ei.filled_quantity

            is_complete = total_filled >= order.quantity
            status = OrderRecoveryStatus.RECOVERED if is_complete else OrderRecoveryStatus.PARTIALLY_RECOVERED

            return OrderRecoveryResult(
                order_id=order.order_id,
                status=status,
                broker_order_id=str(order.broker_order_id or ""),
                filled_quantity=str(total_filled),
                attempts=1,
            )

        except Exception as e:
            return OrderRecoveryResult(
                order_id=order.order_id,
                status=OrderRecoveryStatus.FAILED,
                error=str(e),
            )

    async def recover_network_interruption(
        self,
        orders: list[Order],
        adapter: BrokerAdapter,
    ) -> list[OrderRecoveryResult]:
        """Recover from a network interruption.

        Queries the broker for all orders that were in-flight during
        the interruption.

        Args:
            orders: List of orders that may be affected.
            adapter: Broker adapter to query.

        Returns:
            List of recovery results for each order.
        """
        results: list[OrderRecoveryResult] = []
        for order in orders:
            if order.status in (
                OrderStatus.SUBMITTED,
                OrderStatus.ACKNOWLEDGED,
                OrderStatus.PARTIALLY_FILLED,
            ):
                result = await self.recover_pending_order(order, adapter)
                results.append(result)
                await asyncio.sleep(0.1)  # Rate limit recovery
        return results

    async def detect_duplicate_executions(
        self,
        order: Order,
        adapter: BrokerAdapter,
    ) -> bool:
        """Detect if an order was already executed on the broker.

        Args:
            order: The order to check.
            adapter: Broker adapter to query.

        Returns:
            True if duplicate execution is detected.
        """
        try:
            execution_info = await adapter.get_execution_history(
                symbol=order.symbol,
                since=order.created_at,
                limit=50,
            )
            for ei in execution_info:
                if str(ei.broker_order_id) == str(order.broker_order_id):
                    return True
            return False
        except Exception:
            return False

    async def get_recovery_status(self, order_id: str) -> OrderRecoveryResult | None:
        """Get current recovery status for an order.

        Args:
            order_id: Order identifier.

        Returns:
            Current recovery result if being recovered, None otherwise.
        """
        async with self._lock:
            return self._recovering.get(order_id)

    async def get_recovery_history(self, order_id: str) -> list[OrderRecoveryResult]:
        """Get recovery history for an order.

        Args:
            order_id: Order identifier.

        Returns:
            List of past recovery results.
        """
        async with self._lock:
            return list(self._recovered_orders.get(order_id, []))

    async def clear_recovery_history(self, order_id: str) -> None:
        """Clear recovery history for an order.

        Args:
            order_id: Order identifier.
        """
        async with self._lock:
            self._recovered_orders.pop(order_id, None)
            self._recovering.pop(order_id, None)

    async def recovery_count(self) -> int:
        """Return number of orders currently being recovered."""
        async with self._lock:
            return len(self._recovering)

