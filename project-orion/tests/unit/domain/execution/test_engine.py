"""Tests for execution engine composition root."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.engine import (
    EngineExecutionResult,
    ExecutionEngine,
    ExecutionEngineConfig,
)
from libraries.domain.execution.models import Order, OrderSide, OrderType
from libraries.domain.execution.router import BrokerCapabilities
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection


@pytest.fixture
def engine() -> ExecutionEngine:
    return ExecutionEngine()


@pytest.fixture
def executable_decision() -> TradeDecision:
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
        decision_id="DEC-001",
    )


class TestExecutionEngine:
    async def test_initialize_and_shutdown(self, engine: ExecutionEngine) -> None:
        assert not engine.is_ready
        await engine.initialize()
        assert engine.is_ready
        assert not engine.is_shutdown
        await engine.shutdown()
        assert engine.is_shutdown
        assert not engine.is_ready

    async def test_execute_requires_initialization(
        self, engine: ExecutionEngine, executable_decision: TradeDecision
    ) -> None:
        result = await engine.execute(executable_decision)
        assert not result.success
        assert "not initialized" in result.error.lower()

    async def test_execute_after_shutdown(
        self, engine: ExecutionEngine, executable_decision: TradeDecision
    ) -> None:
        await engine.initialize()
        await engine.shutdown()
        result = await engine.execute(executable_decision)
        assert not result.success
        assert "shut down" in result.error.lower()

    async def test_execute_rejected_decision(self, engine: ExecutionEngine) -> None:
        await engine.initialize()
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.REJECT,
            reason="Risk check failed",
        )
        result = await engine.execute(decision)
        assert not result.success
        assert "not executable" in result.error.lower()

    async def test_execute_with_broker_registration(
        self, engine: ExecutionEngine, executable_decision: TradeDecision
    ) -> None:
        await engine.initialize()
        broker = BrokerCapabilities(
            broker_id="broker-1",
            broker_name="Test Broker",
            supported_symbols=frozenset({"EURUSD"}),
            latency_ms=10.0,
            health_score=0.95,
            is_available=True,
        )
        await engine.register_broker(broker)
        result = await engine.execute(executable_decision)
        # Should succeed (no submit_fn, simulated)
        assert result.success
        assert result.order is not None

    async def test_execute_non_executable_decision(self, engine: ExecutionEngine) -> None:
        await engine.initialize()
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.DEFER,
            reason="Deferred",
        )
        result = await engine.execute(decision)
        assert not result.success

    async def test_engine_execution_result_creation(self) -> None:
        result = EngineExecutionResult(
            success=True,
            error="",
            execution_time_ms=10.0,
            broker_order_id="broker-1",
        )
        assert result.success
        assert result.execution_time_ms == 10.0
        assert result.broker_order_id == "broker-1"

    async def test_health_check(self, engine: ExecutionEngine) -> None:
        await engine.initialize()
        health = await engine.health_check()
        assert health["ready"]
        assert not health["shutdown"]
        assert health["execution_count"] == 0

    async def test_broker_lifecycle(self, engine: ExecutionEngine) -> None:
        broker = BrokerCapabilities(
            broker_id="broker-1",
            broker_name="Test Broker",
            supported_symbols=frozenset({"EURUSD"}),
            is_available=True,
        )
        await engine.register_broker(broker)
        await engine.update_broker_health("broker-1", 0.8)
        await engine.unregister_broker("broker-1")
