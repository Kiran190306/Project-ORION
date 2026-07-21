"""Edge case tests for the Execution Engine.

Tests boundary conditions, error states, and stress scenarios.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.deduplication import OrderDeduplicator
from libraries.domain.execution.exceptions import (
    DuplicateOrderError,
    OrderBuildError,
    OrderNotFoundError,
    OrderValidationError,
    RoutingError,
)
from libraries.domain.execution.models import (
    ExecutionReport,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.domain.execution.state_machine import OrderStateMachine, Trigger
from libraries.domain.execution.tracker import OrderTracker
from libraries.domain.execution.validator import OrderValidator
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    async def test_order_with_zero_volume(self) -> None:
        """Zero volume should be rejected by validator."""
        order = Order(
            order_id="ORD-000",
            decision_id="DEC-000",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("0"),
        )
        validator = OrderValidator()
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_order_with_very_large_volume(self) -> None:
        """Very large volume should be rejected."""
        order = Order(
            order_id="ORD-BIG",
            decision_id="DEC-BIG",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("999999999"),
        )
        validator = OrderValidator()
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_build_decision_without_direction(self) -> None:
        """Decision without direction should raise OrderBuildError."""
        from libraries.domain.execution.builder import OrderBuilder

        builder = OrderBuilder()
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.EXECUTE,
            direction=None,
            position_size=Decimal("1000"),
            decision_id="DEC-NO-DIR",
        )
        with pytest.raises(OrderBuildError) as exc:
            builder.build(decision)
        assert "no direction" in str(exc.value).lower()

    async def test_state_machine_terminal_state_no_transitions(self) -> None:
        """Terminal states should have no outgoing transitions."""
        for terminal_status in (OrderStatus.CANCELLED, OrderStatus.COMPLETED, OrderStatus.EXPIRED):
            assert OrderStateMachine.is_terminal(terminal_status)
            for trigger in Trigger:
                assert not OrderStateMachine.can_transition(terminal_status, trigger)

    async def test_tracker_get_nonexistent_order(self) -> None:
        """Getting a non-existent order should raise OrderNotFoundError."""
        tracker = OrderTracker()
        with pytest.raises(OrderNotFoundError):
            await tracker.get_order("DOES-NOT-EXIST")

    async def test_deduplication_multiple_duplicate_checks(self) -> None:
        """Multiple duplicate checks should all raise."""
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-1", "DEC-1", "EURUSD", "buy")

        for _ in range(3):
            with pytest.raises(DuplicateOrderError):
                await dedup.check_and_register("ORD-2", "DEC-1", "EURUSD", "buy")

    async def test_order_with_minimal_fields(self) -> None:
        """Order with only required fields should be creatable."""
        order = Order(
            order_id="ORD-MIN",
            decision_id="DEC-MIN",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
        )
        assert order.price is None
        assert order.stop_loss is None
        assert order.take_profit is None
        assert order.time_in_force is None

    async def test_negative_price_build_error(self) -> None:
        """Building with negative price should raise."""
        from libraries.domain.execution.builder import OrderBuilder

        builder = OrderBuilder()
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY,
            entry_price=Decimal("-1.00"),
            position_size=Decimal("1000"),
            decision_id="DEC-NEG",
        )
        with pytest.raises(OrderBuildError):
            builder.build(decision, order_type=OrderType.LIMIT, price=Decimal("-1.00"))

    async def test_execution_report_minimal(self) -> None:
        """ExecutionReport with minimal fields."""
        report = ExecutionReport(
            report_id="RPT-MIN",
            order_id="ORD-MIN",
            broker_order_id="BROKER-MIN",
            symbol="EURUSD",
            side="buy",
        )
        assert report.filled_volume is None
        assert report.price is None

    async def test_order_status_transition_chain(self) -> None:
        """Verify the complete happy path transition chain."""
        # NEW -> VALIDATED -> BUILT -> ROUTED -> SUBMITTED -> ACKNOWLEDGED -> FILLED -> SETTLED -> COMPLETED
        expected_chain = [
            (OrderStatus.NEW, Trigger.VALIDATE, OrderStatus.VALIDATED),
            (OrderStatus.VALIDATED, Trigger.BUILD, OrderStatus.BUILT),
            (OrderStatus.BUILT, Trigger.ROUTE, OrderStatus.ROUTED),
            (OrderStatus.ROUTED, Trigger.SUBMIT, OrderStatus.SUBMITTED),
            (OrderStatus.SUBMITTED, Trigger.ACKNOWLEDGE, OrderStatus.ACKNOWLEDGED),
            (OrderStatus.ACKNOWLEDGED, Trigger.FULL_FILL, OrderStatus.FILLED),
            (OrderStatus.FILLED, Trigger.SETTLE, OrderStatus.SETTLED),
            (OrderStatus.SETTLED, Trigger.COMPLETE, OrderStatus.COMPLETED),
        ]
        sm = OrderStateMachine()
        current = OrderStatus.NEW
        for from_status, trigger, to_status in expected_chain:
            assert current == from_status, f"Expected {from_status} but got {current}"
            t = sm.transition(current, trigger)
            assert t.to_status == to_status
            current = t.to_status

    async def test_rejection_chain(self) -> None:
        """Verify all paths to REJECTED."""
        reject_triggers = [
            (OrderStatus.NEW, Trigger.REJECT),
            (OrderStatus.VALIDATED, Trigger.REJECT),
            (OrderStatus.BUILT, Trigger.REJECT),
            (OrderStatus.ROUTED, Trigger.REJECT),
            (OrderStatus.SUBMITTED, Trigger.REJECT),
            (OrderStatus.ACKNOWLEDGED, Trigger.REJECT),
            (OrderStatus.PARTIALLY_FILLED, Trigger.REJECT),
        ]
        for from_status, trigger in reject_triggers:
            sm = OrderStateMachine()
            t = sm.transition(from_status, trigger)
            assert t.to_status == OrderStatus.REJECTED, (
                f"Expected REJECTED from {from_status} via {trigger}"
            )

    async def test_cancellation_chain(self) -> None:
        """Verify all paths to CANCELLED."""
        cancel_triggers = [
            OrderStatus.NEW,
            OrderStatus.VALIDATED,
            OrderStatus.BUILT,
            OrderStatus.ROUTED,
            OrderStatus.SUBMITTED,
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED,
        ]
        for from_status in cancel_triggers:
            sm = OrderStateMachine()
            t = sm.transition(from_status, Trigger.CANCEL)
            assert t.to_status == OrderStatus.CANCELLED

    async def test_multiple_partial_fills(self) -> None:
        """Multiple partial fills should be allowed (self-loop)."""
        sm = OrderStateMachine()
        sm.transition(OrderStatus.NEW, Trigger.VALIDATE)
        sm.transition(OrderStatus.VALIDATED, Trigger.BUILD)
        sm.transition(OrderStatus.BUILT, Trigger.ROUTE)
        sm.transition(OrderStatus.ROUTED, Trigger.SUBMIT)
        sm.transition(OrderStatus.SUBMITTED, Trigger.ACKNOWLEDGE)
        sm.transition(OrderStatus.ACKNOWLEDGED, Trigger.PARTIAL_FILL)
        for _ in range(5):
            t = sm.transition(OrderStatus.PARTIALLY_FILLED, Trigger.PARTIAL_FILL)
            assert t.to_status == OrderStatus.PARTIALLY_FILLED
