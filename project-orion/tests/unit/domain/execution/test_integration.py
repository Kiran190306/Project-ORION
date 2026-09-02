"""Integration tests for the Execution Engine.

Tests the full pipeline: TradeDecision -> Order -> Validate -> Route -> Execute.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.execution.builder import OrderBuilder
from libraries.domain.execution.confirmation import FillConfirmation, FillValidator
from libraries.domain.execution.deduplication import OrderDeduplicator
from libraries.domain.execution.engine import ExecutionEngine, ExecutionEngineConfig
from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import OrderSide, OrderStatus
from tests.unit.domain.execution.conftest import make_order
from libraries.domain.execution.recovery import OrderRecoveryHandler
from libraries.domain.execution.retry import RetryHandler
from libraries.domain.execution.router import BrokerCapabilities, OrderRouter
from libraries.domain.execution.state_machine import Trigger
from libraries.domain.execution.statistics import ExecutionOutcome, ExecutionStatistics
from libraries.domain.execution.tracker import OrderTracker
from libraries.domain.execution.validator import OrderValidator
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection


@pytest.fixture
def decision() -> TradeDecision:
    return TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=85.0,
        entry_price=Decimal("1.10500"),
        stop_loss=Decimal("1.10000"),
        take_profit=Decimal("1.11500"),
        position_size=Decimal("10000"),
        risk_amount=Decimal("50"),
        account_risk_pct=1.0,
        decision_id="DEC-INT-001",
    )


class TestIntegration:
    """Full pipeline integration tests."""

    async def test_full_pipeline_build_validate_route(self, decision: TradeDecision) -> None:
        """Test the full pipeline: Build -> Validate -> Route (no broker)."""
        builder = OrderBuilder()
        validator = OrderValidator()
        router = OrderRouter()
        tracker = OrderTracker()

        # Register a broker
        broker = BrokerCapabilities(
            broker_id="broker-1",
            broker_name="Test Broker",
            supported_symbols=frozenset({"EURUSD"}),
            latency_ms=5.0,
            health_score=0.95,
            is_available=True,
        )
        await router.register_broker(broker)

        # Build
        order = builder.build(decision)
        assert order.symbol == "EURUSD"
        assert order.side == OrderSide.BUY

        # Validate
        validation = await validator.validate(order, market_open=True, broker_available=True)
        assert validation.is_valid

        # Route
        routing = await router.route(order)
        assert routing.selected_broker == "broker-1"

        # Track
        lifecycle = OrderLifecycleTracker(order)
        await tracker.register(order, lifecycle)
        assert await tracker.order_count() == 1

    async def test_full_execution_engine_pipeline(self, decision: TradeDecision) -> None:
        """Test the execution engine with a full pipeline."""
        engine = ExecutionEngine()
        await engine.initialize()

        broker = BrokerCapabilities(
            broker_id="broker-1",
            broker_name="Test Broker",
            supported_symbols=frozenset({"EURUSD"}),
            latency_ms=5.0,
            health_score=0.95,
            is_available=True,
        )
        await engine.register_broker(broker)

        result = await engine.execute(decision)
        assert result.success
        assert result.order is not None
        assert result.order.symbol == "EURUSD"

    async def test_from_decision_to_order_tracking(self, decision: TradeDecision) -> None:
        """Test from decision creation through order tracking."""
        builder = OrderBuilder()
        tracker = OrderTracker()

        order = builder.build(decision)
        lifecycle = OrderLifecycleTracker(order)
        await tracker.register(order, lifecycle)

        # Simulate full lifecycle transitions
        await lifecycle.transition(Trigger.VALIDATE, "Validated")
        await lifecycle.transition(Trigger.BUILD, "Built")
        await lifecycle.transition(Trigger.ROUTE, "Routed")
        await lifecycle.transition(Trigger.SUBMIT, "Submitted")
        await lifecycle.transition(Trigger.ACKNOWLEDGE, "Acknowledged")
        await lifecycle.transition(Trigger.FULL_FILL, "Filled")

        snap = await lifecycle.snapshot()
        assert snap.current_status == OrderStatus.FILLED
        assert snap.transition_count == 6

        # Verify tracker
        tracked = await tracker.get_order(str(order.order_id))
        assert tracked is not None

    async def test_deduplication_in_pipeline(self, decision: TradeDecision) -> None:
        """Test deduplication in the full pipeline."""
        dedup = OrderDeduplicator()
        builder = OrderBuilder()

        order = builder.build(decision)

        # First submission should pass
        await dedup.check_and_register(
            order_id=str(order.order_id),
            decision_id=order.decision_id,
            symbol=order.symbol,
            side=order.side.value,
        )

        # Second submission should fail
        from libraries.domain.execution.exceptions import DuplicateOrderError

        with pytest.raises(DuplicateOrderError):
            await dedup.check_and_register(
                order_id=str(order.order_id),
                decision_id=order.decision_id,
                symbol=order.symbol,
                side=order.side.value,
            )

    async def test_fill_processing_in_pipeline(self, decision: TradeDecision) -> None:
        """Test fill processing in the pipeline."""
        builder = OrderBuilder()
        tracker = OrderTracker()
        fill_validator = FillValidator()

        order = builder.build(decision)
        lifecycle = OrderLifecycleTracker(order)
        await tracker.register(order, lifecycle)

        # Simulate submission
        await lifecycle.transition(Trigger.VALIDATE)
        await lifecycle.transition(Trigger.BUILD)
        await lifecycle.transition(Trigger.ROUTE)
        await lifecycle.transition(Trigger.SUBMIT)
        await lifecycle.transition(Trigger.ACKNOWLEDGE)

        # Create fill confirmation
        fill = FillConfirmation(
            fill_id="FL-INT-001",
            order_id=str(order.order_id),
            symbol=order.symbol,
            side=order.side.value,
            filled_volume=order.quantity or Decimal("0"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("11050.00"),
            broker_fill_id="BROKER-FL-001",
        )

        # Validate fill
        await fill_validator.validate_fill(order, fill)
        assert fill.is_full_fill

        # Transition to filled
        await lifecycle.transition(Trigger.FULL_FILL, "Full fill received")
        snap = await lifecycle.snapshot()
        assert snap.current_status == OrderStatus.FILLED

    async def test_statistics_collection(self, decision: TradeDecision) -> None:
        """Test statistics collection during execution."""
        stats = ExecutionStatistics()

        for i in range(5):
            await stats.record_execution(
                outcome=ExecutionOutcome.FILLED,
                broker_id="broker-1",
                latency_ms=10.0 + i * 5,
                volume=Decimal("1000"),
                commission=Decimal("0.50"),
            )

        snapshot = await stats.get_stats()
        assert snapshot.total_orders == 5
        assert snapshot.filled_orders == 5
        assert snapshot.total_volume == Decimal("5000")
        assert snapshot.total_commission == Decimal("2.50")

    async def test_retry_with_eventual_success(self) -> None:
        """Test retry handler with eventual success."""
        retry = RetryHandler()
        attempt_count = 0

        async def eventually_succeed() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = await retry.execute(eventually_succeed, "test")
        assert result == "success"
        assert attempt_count == 3

    async def test_recovery_after_timeout(self, decision: TradeDecision) -> None:
        """Test recovery after a timeout scenario."""
        from datetime import datetime, timedelta, timezone

        # Create a stale order
        stale_order = make_order(
            order_id="ORD-STALE",
            decision_id="DEC-STALE",
            status=OrderStatus.SUBMITTED,
            created_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )

        recovery = OrderRecoveryHandler()
        assert await recovery.needs_recovery(stale_order)

        await recovery.mark_for_recovery(stale_order)

        async def query_broker(oid: str, symbol: str) -> tuple[bool, str, str]:
            return True, "filled", ""

        attempt = await recovery.attempt_recovery(stale_order, query_broker)
        assert attempt.recovered

    async def test_full_engine_multiple_orders(self) -> None:
        """Test engine with multiple order executions."""
        engine = ExecutionEngine()
        await engine.initialize()

        broker = BrokerCapabilities(
            broker_id="broker-1",
            broker_name="Test Broker",
            supported_symbols=frozenset({"EURUSD", "GBPUSD", "USDJPY"}),
            latency_ms=5.0,
            health_score=0.95,
            is_available=True,
        )
        await engine.register_broker(broker)

        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        decisions = [
            TradeDecision(
                symbol=symbols[i],
                outcome=DecisionOutcome.EXECUTE,
                direction=SignalDirection.BUY,
                position_size=Decimal("1000"),
                decision_id=f"DEC-MULTI-{i}",
            )
            for i in range(3)
        ]

        for decision in decisions:
            result = await engine.execute(decision)
            assert result.success

        health = await engine.health_check()
        assert health["execution_count"] == 3
