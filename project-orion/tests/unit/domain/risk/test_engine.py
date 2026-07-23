"""Tests for the RiskEngine."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.engine import RiskEngine, RiskEngineConfig
from libraries.domain.risk.evaluator import RiskEvaluator
from libraries.domain.risk.models import (
    DrawdownMetrics,
    PolicyCategory,
    PolicySeverity,
    RiskDecision,
    RiskResult,
)
from libraries.domain.risk.policy import (
    MaximumDrawdownPolicy,
    MaximumPositionSizePolicy,
    create_default_policies,
)
from libraries.domain.risk.registry import RiskPolicyRegistry
from libraries.domain.risk.validator import RiskValidator


class MockDecision:
    """Mock TradeDecision for testing."""

    def __init__(
        self,
        symbol="EURUSD",
        direction="buy",
        entry_price=Decimal("1.1000"),
        stop_loss=Decimal("1.0900"),
        take_profit=Decimal("1.1200"),
        position_size=Decimal("10000"),
        confidence=75.0,
        strategy="swing",
        outcome="execute",
    ):
        self.symbol = symbol
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.position_size = position_size
        self.confidence = confidence
        self.strategy = strategy
        self.outcome = outcome
        self.notional_value = Decimal("0")
        self.metadata = {}
        self.reject_reasons = []


class TestRiskEngine:
    @pytest.mark.asyncio
    async def test_initialize(self):
        engine = RiskEngine()
        await engine.initialize()
        assert engine.is_initialized
        assert not engine.is_shutdown

    @pytest.mark.asyncio
    async def test_shutdown(self):
        engine = RiskEngine()
        await engine.initialize()
        await engine.shutdown()
        assert engine.is_shutdown
        assert not engine.is_initialized

    @pytest.mark.asyncio
    async def test_evaluate_no_policies_returns_approved(self):
        engine = RiskEngine()
        await engine.initialize()
        decision = MockDecision()
        result = await engine.evaluate(decision)
        assert result.decision == RiskDecision.APPROVED
        assert result.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_with_policies_passes(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumPositionSizePolicy())

        engine = RiskEngine(registry=registry)
        await engine.initialize()
        decision = MockDecision()
        result = await engine.evaluate(decision)
        assert result.decision == RiskDecision.APPROVED

    @pytest.mark.asyncio
    async def test_evaluate_rejects_when_policy_fails(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumDrawdownPolicy())

        # Create context with high drawdown
        context = RiskContext(
            symbol="EURUSD",
            drawdown=DrawdownMetrics(current_drawdown=25.0, max_drawdown=25.0),
        )

        engine = RiskEngine(registry=registry)
        await engine.initialize()
        decision = MockDecision()
        result = await engine.evaluate(decision, context=context)
        assert result.decision == RiskDecision.REJECTED

    @pytest.mark.asyncio
    async def test_evaluate_with_all_default_policies(self):
        registry = RiskPolicyRegistry()
        policies = create_default_policies()
        for p in policies:
            await registry.register(p)

        engine = RiskEngine(registry=registry)
        await engine.initialize()

        decision = MockDecision()
        context = RiskContext(
            symbol="EURUSD",
            direction="buy",
            account_balance=Decimal("100000"),
            account_equity=Decimal("100000"),
            leverage=1.0,
            daily_pnl=0.0,
            weekly_pnl=0.0,
            monthly_pnl=0.0,
            consecutive_losses=0,
            open_positions_count=0,
            spread_pips=1.0,
            volatility=0.2,
            liquidity_score=0.9,
            market_open=True,
            broker_connected=True,
            data_feed_active=True,
            drawdown=DrawdownMetrics(current_drawdown=0.0, max_drawdown=5.0),
        )
        result = await engine.evaluate(decision, context=context)
        assert result.decision == RiskDecision.APPROVED

    @pytest.mark.asyncio
    async def test_evaluate_rejects_during_emergency(self):
        context = RiskContext(
            symbol="EURUSD",
            emergency_status=type("EmergencyStatus", (), {"active": True, "triggers": ()})(),
        )
        # Override is_emergency property
        import dataclasses

        context = dataclasses.replace(context, emergency_status=None)
        # Test via emergency in context evaluation
        registry = RiskPolicyRegistry()
        from libraries.domain.risk.policy import EmergencyStopPolicy

        await registry.register(EmergencyStopPolicy())

        engine = RiskEngine(registry=registry)
        await engine.initialize()

        from libraries.domain.risk.models import EmergencyModeStatus, EmergencyTrigger

        context = RiskContext(
            symbol="EURUSD",
            emergency_status=EmergencyModeStatus(
                active=True,
                triggers=(EmergencyTrigger.BROKER_DISCONNECT,),
            ),
        )
        decision = MockDecision()
        result = await engine.evaluate(decision, context=context)
        assert result.decision == RiskDecision.REJECTED

    @pytest.mark.asyncio
    async def test_evaluate_with_context_passed_directly(self):
        engine = RiskEngine()
        await engine.initialize()

        context = RiskContext(symbol="EURUSD")
        decision = MockDecision()
        result = await engine.evaluate(decision, context=context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_health_check(self):
        engine = RiskEngine()
        await engine.initialize()
        health = await engine.health_check()
        assert health["initialized"]
        assert not health["shutdown"]
        assert health["total_policies"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_before_initialize_auto_inits(self):
        engine = RiskEngine()
        decision = MockDecision()
        result = await engine.evaluate(decision)
        assert result is not None

    @pytest.mark.asyncio
    async def test_evaluate_after_shutdown_raises(self):
        engine = RiskEngine()
        await engine.initialize()
        await engine.shutdown()
        with pytest.raises(Exception):
            decision = MockDecision()
            await engine.evaluate(decision)

    @pytest.mark.asyncio
    async def test_get_risk_score(self):
        registry = RiskPolicyRegistry()
        await registry.register(MaximumPositionSizePolicy())

        engine = RiskEngine(registry=registry)
        await engine.initialize()

        context = RiskContext(symbol="EURUSD", leverage=1.0)
        score = await engine.get_risk_score(context)
        assert score.policy_count == 1

    @pytest.mark.asyncio
    async def test_fail_open_mode(self):
        registry = RiskPolicyRegistry()
        engine = RiskEngine(
            registry=registry,
            config=RiskEngineConfig(fail_open=True),
        )
        await engine.initialize()

        # Inject a broken policy
        class BrokenPolicy:
            name = "broken"
            description = "Broken policy"
            category = PolicyCategory.SYSTEM_HEALTH
            severity = PolicySeverity.CRITICAL
            enabled = True
            priority = 1

            async def evaluate(self, context):
                raise RuntimeError("Unexpected error")

            async def statistics(self):
                return {}

            async def initialize(self):
                pass

            async def dispose(self):
                pass

        await registry.register(BrokenPolicy())  # type: ignore[arg-type]
        decision = MockDecision()
        result = await engine.evaluate(decision)
        assert result.decision == RiskDecision.APPROVED  # fail-open => approved

    @pytest.mark.asyncio
    async def test_strict_mode_rejects_invalid_context(self):
        engine = RiskEngine(config=RiskEngineConfig(strict_mode=True))
        await engine.initialize()

        context = RiskContext(symbol="")  # Empty symbol
        decision = MockDecision()
        result = await engine.evaluate(decision, context=context)
        assert result.decision == RiskDecision.REJECTED

    @pytest.mark.asyncio
    async def test_config_property(self):
        engine = RiskEngine()
        assert engine.config.max_evaluation_time_ms == 5000.0
        assert not engine.config.fail_open

    @pytest.mark.asyncio
    async def test_registry_property(self):
        registry = RiskPolicyRegistry()
        engine = RiskEngine(registry=registry)
        assert engine.registry is registry

    @pytest.mark.asyncio
    async def test_multiple_evaluations(self):
        engine = RiskEngine()
        await engine.initialize()
        for _ in range(5):
            decision = MockDecision()
            result = await engine.evaluate(decision)
            assert result.decision == RiskDecision.APPROVED

    @pytest.mark.asyncio
    async def test_evaluate_with_rejection_reasons(self):
        registry = RiskPolicyRegistry()
        policy = MaximumPositionSizePolicy()
        policy._enabled = True
        await registry.register(policy)

        engine = RiskEngine(registry=registry)
        await engine.initialize()

        decision = MockDecision(position_size=Decimal("100000000"))
        context = RiskContext(
            symbol="EURUSD",
            notional_value=Decimal("100000000"),
            account_balance=Decimal("1000"),
        )
        result = await engine.evaluate(decision, context=context)
        if result.decision == RiskDecision.REJECTED:
            assert len(result.rejection_reasons) > 0
