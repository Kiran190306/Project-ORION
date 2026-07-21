"""Immutable order state machine for the Execution Engine.

Defines valid state transitions for the order lifecycle.
Every transition creates a new Order instance (immutable pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.domain.execution.exceptions import InvalidTransitionError
from libraries.domain.execution.models import OrderStatus


class Trigger(StrEnum):
    """Events that trigger state transitions."""

    VALIDATE = "validate"
    BUILD = "build"
    SUBMIT = "submit"
    ACKNOWLEDGE = "acknowledge"
    PARTIAL_FILL = "partial_fill"
    FULL_FILL = "full_fill"
    CANCEL = "cancel"
    REJECT = "reject"
    EXPIRE = "expire"
    ROUTE = "route"
    SETTLE = "settle"
    COMPLETE = "complete"
    RETRY = "retry"
    TIMEOUT = "timeout"
    RECOVER = "recover"


@dataclass(frozen=True, slots=True)
class StateTransition:
    """A record of a state transition."""

    from_status: OrderStatus
    to_status: OrderStatus
    trigger: Trigger
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def transition_time_ms(self) -> float:
        """Return time since epoch for this transition."""
        return self.timestamp.timestamp() * 1000


# ─── Transition Map ─────────────────────────────────────────────────────
# Defines valid transitions: current_status -> {trigger: next_status}

_TRANSITION_MAP: dict[OrderStatus, dict[Trigger, OrderStatus]] = {
    OrderStatus.NEW: {
        Trigger.VALIDATE: OrderStatus.VALIDATED,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
    },
    OrderStatus.VALIDATED: {
        Trigger.BUILD: OrderStatus.BUILT,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
    },
    OrderStatus.BUILT: {
        Trigger.ROUTE: OrderStatus.ROUTED,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
    },
    OrderStatus.ROUTED: {
        Trigger.SUBMIT: OrderStatus.SUBMITTED,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
    },
    OrderStatus.SUBMITTED: {
        Trigger.ACKNOWLEDGE: OrderStatus.ACKNOWLEDGED,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
        Trigger.TIMEOUT: OrderStatus.EXPIRED,
    },
    OrderStatus.ACKNOWLEDGED: {
        Trigger.PARTIAL_FILL: OrderStatus.PARTIALLY_FILLED,
        Trigger.FULL_FILL: OrderStatus.FILLED,
        Trigger.REJECT: OrderStatus.REJECTED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
        Trigger.EXPIRE: OrderStatus.EXPIRED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        Trigger.PARTIAL_FILL: OrderStatus.PARTIALLY_FILLED,  # self-loop
        Trigger.FULL_FILL: OrderStatus.FILLED,
        Trigger.CANCEL: OrderStatus.CANCELLED,
        Trigger.EXPIRE: OrderStatus.EXPIRED,
        Trigger.REJECT: OrderStatus.REJECTED,
    },
    OrderStatus.FILLED: {
        Trigger.SETTLE: OrderStatus.SETTLED,
    },
    OrderStatus.REJECTED: {
        Trigger.RETRY: OrderStatus.NEW,  # retry re-enters pipeline
    },
    OrderStatus.CANCELLED: {},  # terminal
    OrderStatus.EXPIRED: {},  # terminal
    OrderStatus.SETTLED: {
        Trigger.COMPLETE: OrderStatus.COMPLETED,
    },
    OrderStatus.COMPLETED: {},  # terminal
}


class OrderStateMachine:
    """Immutable state machine for order lifecycle.

    Validates transitions against the defined map and records each
    transition as an immutable StateTransition object.
    """

    def __init__(self) -> None:
        self._transitions: list[StateTransition] = []

    @property
    def transitions(self) -> tuple[StateTransition, ...]:
        """Return all recorded transitions."""
        return tuple(self._transitions)

    @property
    def transition_count(self) -> int:
        return len(self._transitions)

    @staticmethod
    def can_transition(from_status: OrderStatus, trigger: Trigger) -> bool:
        """Check if a transition is valid without executing it."""
        allowed = _TRANSITION_MAP.get(from_status, {})
        return trigger in allowed

    @staticmethod
    def next_status(from_status: OrderStatus, trigger: Trigger) -> OrderStatus | None:
        """Return the next status for a trigger, or None if invalid."""
        allowed = _TRANSITION_MAP.get(from_status, {})
        return allowed.get(trigger)

    @staticmethod
    def is_terminal(status: OrderStatus) -> bool:
        """Check if a status is terminal (no outgoing transitions)."""
        return not bool(_TRANSITION_MAP.get(status, {}))

    @staticmethod
    def is_active(status: OrderStatus) -> bool:
        """Check if an order is still active (not in terminal state)."""
        return not OrderStateMachine.is_terminal(status)

    @staticmethod
    def allowed_triggers(from_status: OrderStatus) -> frozenset[Trigger]:
        """Return all valid triggers from a given status."""
        return frozenset(_TRANSITION_MAP.get(from_status, {}).keys())

    @staticmethod
    def allowed_next_statuses(from_status: OrderStatus) -> frozenset[OrderStatus]:
        """Return all valid next statuses from a given status."""
        return frozenset(_TRANSITION_MAP.get(from_status, {}).values())

    def transition(
        self,
        from_status: OrderStatus,
        trigger: Trigger,
        details: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StateTransition:
        """Attempt a state transition.

        Args:
            from_status: Current order status.
            trigger: Event triggering the transition.
            details: Human-readable explanation.
            metadata: Additional transition metadata.

        Returns:
            StateTransition record.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        to_status = self.next_status(from_status, trigger)
        if to_status is None:
            raise InvalidTransitionError(
                f"Cannot transition from {from_status.value} via {trigger.value}"
            )

        transition = StateTransition(
            from_status=from_status,
            to_status=to_status,
            trigger=trigger,
            details=details,
            metadata=metadata or {},
        )
        self._transitions.append(transition)
        return transition

    @staticmethod
    def is_retryable(from_status: OrderStatus) -> bool:
        """Check if an order in this status can be retried."""
        return from_status in (OrderStatus.REJECTED, OrderStatus.EXPIRED)

    @staticmethod
    def can_settle(from_status: OrderStatus) -> bool:
        """Check if an order can be settled."""
        allowed = _TRANSITION_MAP.get(from_status, {})
        return Trigger.SETTLE in allowed

    @staticmethod
    def can_complete(from_status: OrderStatus) -> bool:
        """Check if an order can be completed."""
        allowed = _TRANSITION_MAP.get(from_status, {})
        return Trigger.COMPLETE in allowed
