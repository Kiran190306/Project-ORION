"""Tests for order lifecycle tracker."""

from __future__ import annotations

import pytest

from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import OrderStatus
from libraries.domain.execution.state_machine import Trigger
from tests.unit.domain.execution.conftest import make_order


@pytest.fixture
def order() -> object:
    return make_order()


@pytest.fixture
def tracker(order: object) -> OrderLifecycleTracker:
    return OrderLifecycleTracker(order)  # type: ignore[arg-type]


class TestOrderLifecycleTracker:
    def test_initial_state(self, tracker: OrderLifecycleTracker) -> None:
        assert tracker.order_id == "ORD-001"
        assert tracker.current_status == OrderStatus.NEW
        assert tracker.order is not None

    async def test_transition(self, tracker: OrderLifecycleTracker) -> None:
        t = await tracker.transition(Trigger.VALIDATE)
        assert t.from_status == OrderStatus.NEW
        assert t.to_status == OrderStatus.VALIDATED

    async def test_transition_with_details(self, tracker: OrderLifecycleTracker) -> None:
        t = await tracker.transition(Trigger.VALIDATE, "Validating", {"key": "val"})
        assert t.details == "Validating"
        assert t.metadata["key"] == "val"

    async def test_can_transition(self, tracker: OrderLifecycleTracker) -> None:
        assert await tracker.can_transition(Trigger.VALIDATE)
        assert not await tracker.can_transition(Trigger.FULL_FILL)

    async def test_is_terminal(self, tracker: OrderLifecycleTracker) -> None:
        assert not await tracker.is_terminal()
        await tracker.transition(Trigger.CANCEL)
        assert await tracker.is_terminal()

    async def test_is_active(self, tracker: OrderLifecycleTracker) -> None:
        assert await tracker.is_active()
        await tracker.transition(Trigger.CANCEL)
        assert not await tracker.is_active()

    async def test_allowed_triggers(self, tracker: OrderLifecycleTracker) -> None:
        triggers = await tracker.allowed_triggers()
        assert Trigger.VALIDATE in triggers
        assert Trigger.REJECT in triggers

    async def test_snapshot(self, tracker: OrderLifecycleTracker) -> None:
        await tracker.transition(Trigger.VALIDATE)
        snap = await tracker.snapshot()
        assert snap.order_id == "ORD-001"
        assert snap.current_status == OrderStatus.VALIDATED
        assert snap.transition_count == 1
        assert not snap.is_terminal

    def test_mark_start_end(self, tracker: OrderLifecycleTracker) -> None:
        tracker.mark_start(Trigger.VALIDATE)
        elapsed = tracker.mark_end(Trigger.VALIDATE)
        assert elapsed >= 0.0

    async def test_reset(self, tracker: OrderLifecycleTracker) -> None:
        await tracker.transition(Trigger.VALIDATE)
        assert tracker.current_status == OrderStatus.VALIDATED
        await tracker.reset()
        assert tracker.current_status == OrderStatus.NEW

    async def test_full_lifecycle_tracking(self, tracker: OrderLifecycleTracker) -> None:
        await tracker.transition(Trigger.VALIDATE)
        await tracker.transition(Trigger.BUILD)
        await tracker.transition(Trigger.ROUTE)
        await tracker.transition(Trigger.SUBMIT)
        await tracker.transition(Trigger.ACKNOWLEDGE)
        await tracker.transition(Trigger.FULL_FILL)
        snap = await tracker.snapshot()
        assert snap.transition_count == 6
        assert snap.current_status == OrderStatus.FILLED
