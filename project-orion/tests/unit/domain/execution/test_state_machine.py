"""Tests for the order state machine."""

from __future__ import annotations

import pytest

from libraries.domain.execution.exceptions import InvalidTransitionError
from libraries.domain.execution.models import OrderStatus
from libraries.domain.execution.state_machine import (
    OrderStateMachine,
    StateTransition,
    Trigger,
)


class TestOrderStateMachine:
    def test_valid_transition(self) -> None:
        sm = OrderStateMachine()
        t = sm.transition(OrderStatus.NEW, Trigger.VALIDATE, "Validating order")
        assert t.from_status == OrderStatus.NEW
        assert t.to_status == OrderStatus.VALIDATED
        assert t.trigger == Trigger.VALIDATE
        assert t.details == "Validating order"

    def test_invalid_transition_raises_error(self) -> None:
        sm = OrderStateMachine()
        with pytest.raises(InvalidTransitionError) as exc:
            sm.transition(OrderStatus.NEW, Trigger.FULL_FILL)
        assert "Cannot transition" in str(exc.value)

    def test_full_lifecycle(self) -> None:
        sm = OrderStateMachine()
        # NEW -> VALIDATED -> BUILT -> ROUTED -> SUBMITTED -> ACKNOWLEDGED -> FILLED -> SETTLED -> COMPLETED
        sm.transition(OrderStatus.NEW, Trigger.VALIDATE)
        sm.transition(OrderStatus.VALIDATED, Trigger.BUILD)
        sm.transition(OrderStatus.BUILT, Trigger.ROUTE)
        sm.transition(OrderStatus.ROUTED, Trigger.SUBMIT)
        sm.transition(OrderStatus.SUBMITTED, Trigger.ACKNOWLEDGE)
        sm.transition(OrderStatus.ACKNOWLEDGED, Trigger.FULL_FILL)
        sm.transition(OrderStatus.FILLED, Trigger.SETTLE)
        t = sm.transition(OrderStatus.SETTLED, Trigger.COMPLETE)
        assert t.to_status == OrderStatus.COMPLETED

    def test_partial_fill_self_loop(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderStatus.NEW, Trigger.VALIDATE)
        sm.transition(OrderStatus.VALIDATED, Trigger.BUILD)
        sm.transition(OrderStatus.BUILT, Trigger.ROUTE)
        sm.transition(OrderStatus.ROUTED, Trigger.SUBMIT)
        sm.transition(OrderStatus.SUBMITTED, Trigger.ACKNOWLEDGE)
        # First partial fill
        sm.transition(OrderStatus.ACKNOWLEDGED, Trigger.PARTIAL_FILL)
        # Second partial fill (self-loop)
        t = sm.transition(OrderStatus.PARTIALLY_FILLED, Trigger.PARTIAL_FILL)
        assert t.to_status == OrderStatus.PARTIALLY_FILLED

    def test_rejected_then_retry(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderStatus.NEW, Trigger.REJECT)
        t = sm.transition(OrderStatus.REJECTED, Trigger.RETRY)
        assert t.to_status == OrderStatus.NEW

    def test_terminal_states(self) -> None:
        assert OrderStateMachine.is_terminal(OrderStatus.CANCELLED)
        assert OrderStateMachine.is_terminal(OrderStatus.EXPIRED)
        assert OrderStateMachine.is_terminal(OrderStatus.COMPLETED)
        assert not OrderStateMachine.is_terminal(OrderStatus.NEW)
        assert not OrderStateMachine.is_terminal(OrderStatus.FILLED)

    def test_is_active(self) -> None:
        assert not OrderStateMachine.is_active(OrderStatus.CANCELLED)
        assert not OrderStateMachine.is_active(OrderStatus.COMPLETED)
        assert OrderStateMachine.is_active(OrderStatus.NEW)
        assert OrderStateMachine.is_active(OrderStatus.SUBMITTED)

    def test_can_transition(self) -> None:
        assert OrderStateMachine.can_transition(OrderStatus.NEW, Trigger.VALIDATE)
        assert not OrderStateMachine.can_transition(OrderStatus.NEW, Trigger.FULL_FILL)
        assert OrderStateMachine.can_transition(OrderStatus.FILLED, Trigger.SETTLE)

    def test_next_status(self) -> None:
        assert OrderStateMachine.next_status(OrderStatus.NEW, Trigger.VALIDATE) == OrderStatus.VALIDATED
        assert OrderStateMachine.next_status(OrderStatus.NEW, Trigger.FULL_FILL) is None

    def test_allowed_triggers(self) -> None:
        triggers = OrderStateMachine.allowed_triggers(OrderStatus.NEW)
        assert Trigger.VALIDATE in triggers
        assert Trigger.REJECT in triggers
        assert Trigger.CANCEL in triggers
        assert Trigger.FULL_FILL not in triggers

    def test_allowed_next_statuses(self) -> None:
        statuses = OrderStateMachine.allowed_next_statuses(OrderStatus.NEW)
        assert OrderStatus.VALIDATED in statuses
        assert OrderStatus.REJECTED in statuses
        assert OrderStatus.CANCELLED in statuses

    def test_is_retryable(self) -> None:
        assert OrderStateMachine.is_retryable(OrderStatus.REJECTED)
        assert OrderStateMachine.is_retryable(OrderStatus.EXPIRED)
        assert not OrderStateMachine.is_retryable(OrderStatus.FILLED)

    def test_can_settle(self) -> None:
        assert OrderStateMachine.can_settle(OrderStatus.FILLED)
        assert not OrderStateMachine.can_settle(OrderStatus.NEW)

    def test_can_complete(self) -> None:
        assert OrderStateMachine.can_complete(OrderStatus.SETTLED)
        assert not OrderStateMachine.can_complete(OrderStatus.NEW)

    def test_transition_records_history(self) -> None:
        sm = OrderStateMachine()
        sm.transition(OrderStatus.NEW, Trigger.VALIDATE)
        sm.transition(OrderStatus.VALIDATED, Trigger.BUILD)
        assert sm.transition_count == 2
        assert len(sm.transitions) == 2

    def test_state_transition_creation(self) -> None:
        t = StateTransition(
            from_status=OrderStatus.NEW,
            to_status=OrderStatus.VALIDATED,
            trigger=Trigger.VALIDATE,
            details="test",
            metadata={"key": "value"},
        )
        assert t.from_status == OrderStatus.NEW
        assert t.to_status == OrderStatus.VALIDATED
        assert t.metadata["key"] == "value"
        assert t.transition_time_ms > 0
