"""Tests for order lifecycle tracker."""

from __future__ import annotations

import pytest

from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import Order, OrderSide, OrderStatus, OrderType
from libraries.domain.execution.state_machine import Trigger
from decimal import Decimal


@pytest.fixture
def order() -> Order:
    return Order(
        order_id="ORD-001",
        decision_id="DEC-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1000"),
    )


@pytest.fixture
def tracker(order: Order) -> OrderLifecycleTracker:
    return OrderLifecycleTracker(order)


class TestOrderLifecycleTracker:
    def test_initial_state(self, tracker: OrderLifecycleTracker) -> None:
        assert tracker.order_id == "ORD-001"
        assert tracker.current_status == OrderStatus.NEW
        assert tracker.order is not None

    def test_transition(self, tracker: OrderLifecycleTracker) -> None:
        t = tracker.transition(Trigger.VALIDATE)
        assert t.from_status == OrderStatus.NEW
        assert t.to_status == OrderStatus.VALIDATED

    def test_transition_with_details(self, tracker: OrderLifecycleTracker) -> None:
        t = tracker.transition(Trigger.VALIDATE, "Validating", {"key": "val"})
        assert t.details == "Validating"
        assert t.metadata["key"] == "val"

    def test_can_transition(self, tracker: OrderLifecycleTracker) -> None:
        assert tracker.can_transition(Trigger.VALIDATE)
        assert not tracker.can_transition(Trigger.FULL_FILL)

    def test_is_terminal(self, tracker: OrderLifecycleTracker) -> None:
        assert not tracker.is_terminal()
        tracker.transition(Trigger.CANCEL)
        assert tracker.is_terminal()

    def test_is_active(self, tracker: OrderLifecycleTracker) -> None:
        assert tracker.is_active()
        tracker.transition(Trigger.CANCEL)
        assert not tracker.is_active()

    def test_allowed_triggers(self, tracker: OrderLifecycleTracker) -> None:
        triggers = tracker.allowed_triggers()
        assert Trigger.VALIDATE in triggers
        assert Trigger.REJECT in triggers

    def test_snapshot(self, tracker: OrderLifecycleTracker) -> None:
        tracker.transition(Trigger.VALIDATE)
        snap = tracker.snapshot()
        assert snap.order_id == "ORD-001"
        assert snap.current_status == OrderStatus.VALIDATED
        assert snap.transition_count == 1
        assert not snap.is_terminal

    def test_mark_start_end(self, tracker: OrderLifecycleTracker) -> None:
        tracker.mark_start(Trigger.VALIDATE)
        elapsed = tracker.mark_end(Trigger.VALIDATE)
        assert elapsed >= 0.0

    def test_reset(self, tracker: OrderLifecycleTracker) -> None:
        tracker.transition(Trigger.VALIDATE)
        assert tracker.current_status == OrderStatus.VALIDATED
        tracker.reset()
        assert tracker.current_status == OrderStatus.NEW

    def test_full_lifecycle_tracking(self, tracker: OrderLifecycleTracker) -> None:
        tracker.transition(Trigger.VALIDATE)
        tracker.transition(Trigger.BUILD)
        tracker.transition(Trigger.ROUTE)
        tracker.transition(Trigger.SUBMIT)
        tracker.transition(Trigger.ACKNOWLEDGE)
        tracker.transition(Trigger.FULL_FILL)
        snap = tracker.snapshot()
        assert snap.transition_count == 6
        assert snap.current_status == OrderStatus.FILLED
