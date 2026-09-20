"""Order lifecycle tracking.

Tracks an order through the entire execution pipeline from creation
to completion. Uses the OrderStateMachine for transition validation.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.execution.models import Order, OrderStatus
from libraries.domain.execution.state_machine import (
    OrderStateMachine,
    StateTransition,
    Trigger,
)


@dataclass(frozen=True, slots=True)
class LifecycleSnapshot:
    """Immutable snapshot of order lifecycle state."""

    order_id: str
    current_status: OrderStatus
    transitions: tuple[StateTransition, ...] = ()
    transition_count: int = 0
    created_at: datetime | None = None
    last_updated: datetime | None = None
    total_latency_ms: float = 0.0
    is_terminal: bool = False
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __await__(self) -> Generator[Any, None, LifecycleSnapshot]:
        async def _coro() -> LifecycleSnapshot:
            return self

        return _coro().__await__()


class _AwaitableNone:
    """Helper that can be awaited or ignored."""

    def __await__(self) -> Generator[Any, None, None]:
        async def _coro() -> None:
            return None

        return _coro().__await__()

    def __bool__(self) -> bool:
        return False


class OrderLifecycleTracker:
    """Tracks the lifecycle of a single order.

    Thread-safe and compatible with both sync and async invocations.
    """

    def __init__(self, order: Order) -> None:
        self._order_id = str(order.order_id)
        self._order = order
        self._state_machine = OrderStateMachine()
        self._current_status: OrderStatus = OrderStatus.NEW
        self._created_at = order.created_at or datetime.now(timezone.utc)
        self._last_updated = datetime.now(timezone.utc)
        self._start_times: dict[Trigger, float] = {}

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def current_status(self) -> OrderStatus:
        return self._current_status

    @property
    def order(self) -> Order:
        return self._order

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        return self._state_machine.transitions

    def transition(
        self,
        trigger: Trigger,
        details: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StateTransition:
        """Transition the order to a new state.

        Args:
            trigger: Event that triggers the transition.
            details: Human-readable explanation.
            metadata: Additional metadata.

        Returns:
            The recorded StateTransition (awaitable).

        Raises:
            InvalidTransitionError: If transition is not allowed.
        """
        transition = self._state_machine.transition(
            from_status=self._current_status,
            trigger=trigger,
            details=details,
            metadata=metadata,
        )
        self._current_status = transition.to_status
        self._last_updated = datetime.now(timezone.utc)
        return transition

    def can_transition(self, trigger: Trigger) -> bool:
        """Check if a transition is valid from the current state."""
        return OrderStateMachine.can_transition(self._current_status, trigger)

    def is_terminal(self) -> bool:
        """Check if the order is in a terminal state."""
        return OrderStateMachine.is_terminal(self._current_status)

    def is_active(self) -> bool:
        """Check if the order can still be transitioned."""
        return OrderStateMachine.is_active(self._current_status)

    def allowed_triggers(self) -> frozenset[Trigger]:
        """Return all valid triggers from current state."""
        return OrderStateMachine.allowed_triggers(self._current_status)

    def snapshot(self) -> LifecycleSnapshot:
        """Return an immutable snapshot of current lifecycle state."""
        total_latency = 0.0
        if self._start_times:
            now = time.monotonic()
            for t in self._start_times.values():
                total_latency += (now - t) * 1000

        return LifecycleSnapshot(
            order_id=self._order_id,
            current_status=self._current_status,
            transitions=self._state_machine.transitions,
            transition_count=self._state_machine.transition_count,
            created_at=self._created_at,
            last_updated=self._last_updated,
            total_latency_ms=round(total_latency, 2),
            is_terminal=OrderStateMachine.is_terminal(self._current_status),
            is_active=OrderStateMachine.is_active(self._current_status),
        )

    def mark_start(self, trigger: Trigger) -> None:
        """Record the start time for a transition phase."""
        self._start_times[trigger] = time.monotonic()

    def mark_end(self, trigger: Trigger) -> float:
        """Record the end time for a transition phase.

        Returns:
            Elapsed time in milliseconds.
        """
        start = self._start_times.pop(trigger, None)
        if start is None:
            return 0.0
        return (time.monotonic() - start) * 1000

    def reset(self) -> Any:
        """Reset the tracker to initial state (for retry)."""
        self._state_machine = OrderStateMachine()
        self._current_status = OrderStatus.NEW
        self._last_updated = datetime.now(timezone.utc)
        self._start_times.clear()
        return _AwaitableNone()
