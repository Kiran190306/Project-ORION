"""Order recovery handler.

Handles recovery of orders that were submitted but not confirmed
(broker acknowledged, but no fill received). Supports timeout-based
detection, query-by-broker, and reconnect recovery.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Awaitable

from libraries.domain.execution.exceptions import RecoveryError
from libraries.domain.execution.models import Order, OrderStatus


@dataclass(frozen=True, slots=True)
class RecoveryConfig:
    """Configuration for order recovery."""

    recovery_timeout_seconds: float = 30.0  # Time before marking as recovery-needed
    max_recovery_attempts: int = 3
    recovery_interval_seconds: float = 5.0
    query_broker_on_recovery: bool = True
    auto_cancel_after_failed_recovery: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    """Record of a recovery attempt."""

    attempt_number: int
    order_id: str
    broker_queried: bool = False
    broker_found: bool = False
    broker_status: str = ""
    recovered: bool = False
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class RecoveryState:
    """Current recovery state for an order."""

    order_id: str
    is_recovering: bool
    attempts: int
    max_attempts: int
    last_attempt: RecoveryAttempt | None = None
    recovery_started_at: datetime | None = None


class OrderRecoveryHandler:
    """Handles order recovery for unconfirmed submissions.

    For orders that were submitted but not confirmed (e.g., broker
    disconnect, timeout), this handler attempts to recover by
    querying the broker for the order status.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        config: RecoveryConfig | None = None,
    ) -> None:
        self._config = config or RecoveryConfig()
        self._recovering: dict[str, RecoveryState] = {}
        self._attempts: dict[str, list[RecoveryAttempt]] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> RecoveryConfig:
        return self._config

    async def mark_for_recovery(self, order: Order) -> RecoveryState:
        """Mark an order for recovery.

        Args:
            order: The order needing recovery.

        Returns:
            Current recovery state.
        """
        async with self._lock:
            state = RecoveryState(
                order_id=order.order_id,
                is_recovering=True,
                attempts=0,
                max_attempts=self._config.max_recovery_attempts,
                recovery_started_at=datetime.now(timezone.utc),
            )
            self._recovering[order.order_id] = state
            self._attempts[order.order_id] = []
            return state

    async def attempt_recovery(
        self,
        order: Order,
        query_broker: Callable[[str, str], Awaitable[tuple[bool, str, str]]] | None = None,
    ) -> RecoveryAttempt:
        """Attempt to recover an order.

        Args:
            order: The order to recover.
            query_broker: Async callable (order_id, symbol) -> (found, status, error).

        Returns:
            RecoveryAttempt with results.

        Raises:
            RecoveryError: If recovery fails after max attempts.
        """
        async with self._lock:
            state = self._recovering.get(order.order_id)
            if state is None:
                raise RecoveryError(f"Order {order.order_id} is not marked for recovery")

            if state.attempts >= state.max_attempts:
                raise RecoveryError(
                    f"Recovery exhausted for order {order.order_id} "
                    f"after {state.max_attempts} attempts"
                )

            attempt_number = state.attempts + 1

        # Attempt recovery (outside lock to avoid blocking)
        broker_found = False
        broker_status = ""
        error = ""

        if query_broker is not None and self._config.query_broker_on_recovery:
            try:
                broker_found, broker_status, error = await query_broker(
                    order.order_id, order.symbol
                )
            except Exception as e:
                error = str(e)

        async with self._lock:
            recovered = broker_found and broker_status.lower() in (
                "filled", "partial_fill", "acknowledged", "working"
            )

            attempt = RecoveryAttempt(
                attempt_number=attempt_number,
                order_id=order.order_id,
                broker_queried=query_broker is not None,
                broker_found=broker_found,
                broker_status=broker_status,
                recovered=recovered,
                error=error,
            )

            self._attempts[order.order_id].append(attempt)

            # Update state
            new_state = RecoveryState(
                order_id=order.order_id,
                is_recovering=not recovered and attempt_number < state.max_attempts,
                attempts=attempt_number,
                max_attempts=state.max_attempts,
                last_attempt=attempt,
                recovery_started_at=state.recovery_started_at,
            )

            if recovered:
                self._recovering.pop(order.order_id, None)
            else:
                self._recovering[order.order_id] = new_state

            return attempt

    async def needs_recovery(self, order: Order) -> bool:
        """Check if an order needs recovery.

        An order needs recovery if it was submitted but not confirmed
        within the recovery timeout window.

        Args:
            order: The order to check.

        Returns:
            True if recovery is needed.
        """
        async with self._lock:
            # Already being recovered
            if order.order_id in self._recovering:
                return True

            # Check if order is in a state that needs recovery
            if order.status in (
                OrderStatus.SUBMITTED,
                OrderStatus.ACKNOWLEDGED,
            ):
                # Check if stale
                if order.created_at is not None:
                    elapsed = (datetime.now(timezone.utc) - order.created_at).total_seconds()
                    return elapsed > self._config.recovery_timeout_seconds

            return False

    async def is_recovering(self, order_id: str) -> bool:
        """Check if an order is currently being recovered."""
        async with self._lock:
            return order_id in self._recovering

    async def get_attempts(self, order_id: str) -> list[RecoveryAttempt]:
        """Get recovery attempts for an order."""
        async with self._lock:
            return list(self._attempts.get(order_id, []))

    async def cancel_recovery(self, order_id: str) -> None:
        """Cancel recovery for an order.

        Args:
            order_id: Order identifier.
        """
        async with self._lock:
            self._recovering.pop(order_id, None)
            self._attempts.pop(order_id, None)

    async def recovery_count(self) -> int:
        """Return number of orders currently being recovered."""
        async with self._lock:
            return len(self._recovering)
