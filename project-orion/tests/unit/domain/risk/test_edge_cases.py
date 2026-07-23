"""Edge case tests for the Risk Management Engine.

Tests:
- Zero balance
- Margin exhaustion
- High leverage
- Drawdown
- News mode
- Trading lock
- Cooldown
- Emergency stop
- Risk profiles
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.risk.models import (
    AccountProtectionLevel,
    AccountProtectionStatus,
    DrawdownMetrics,
    EmergencyModeStatus,
    EmergencyTrigger,
    PolicyCategory,
    PolicySeverity,
    PortfolioRisk,
    RiskDecision,
    RiskProfileType,
)
from libraries.domain.risk.policy import (
    EmergencyStopPolicy,
    HardStopPolicy,
    MarginProtectionPolicy,
    MaximumDrawdownPolicy,
    MaximumLeveragePolicy,
    MaximumPositionSizePolicy,
    NewsProtectionPolicy,
    TradingLockPolicy,
    create_default_policies,
)
from libraries.domain.risk.profile import RiskProfileConfig
from libraries.domain.risk.registry import RiskPolicyRegistry

# ─── Zero Balance ──────────────────────────────────────────────────────────


class TestZeroBalance:
    @pytest.mark.asyncio
    async def test_position_size_with_zero_balance(self):
        policy = MaximumPositionSizePolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            account_balance=Decimal("0"),
            notional_value=Decimal("10000"),
        )
        result = await policy.evaluate(ctx)
        # Should not crash with zero balance
        assert result is not None

    @pytest.mark.asyncio
    async def test_margin_with_zero_equity(self):
        policy = MarginProtectionPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            account_equity=Decimal("0"),
            margin_used=Decimal("0"),
        )
        result = await policy.evaluate(ctx)
        assert result is not None

    @pytest.mark.asyncio
    async def test_engine_with_zero_balance(self):
        registry = RiskPolicyRegistry()
        policies = create_default_policies()
        for p in policies:
            await registry.register(p)
        engine = RiskEngine(registry=registry)
        await engine.initialize()
        ctx = RiskContext(
            symbol="EURUSD",
            account_balance=Decimal("0"),
            account_equity=Decimal("0"),
            leverage=0.0,
        )
        result = await engine.evaluate("test", context=ctx)
        assert result is not None


# ─── Margin Exhaustion ─────────────────────────────────────────────────────


class TestMarginExhaustion:
    @pytest.mark.asyncio
    async def test_margin_call_risk_detected(self):
        policy = MarginProtectionPolicy(RiskProfileConfig(margin_call_threshold_pct=100.0))
        ctx = RiskContext(
            symbol="EURUSD",
            account_equity=Decimal("1000"),
            margin_used=Decimal("950"),
            margin_free=Decimal("50"),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed  # Margin level should be critical

    @pytest.mark.asyncio
    async def test_full_margin_used(self):
        policy = MarginProtectionPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            account_equity=Decimal("10000"),
            margin_used=Decimal("10000"),
            margin_free=Decimal("0"),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_no_margin_used(self):
        policy = MarginProtectionPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            account_equity=Decimal("10000"),
            margin_used=Decimal("0"),
            margin_free=Decimal("10000"),
        )
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── High Leverage ─────────────────────────────────────────────────────────


class TestHighLeverage:
    @pytest.mark.asyncio
    async def test_extreme_leverage_rejected(self):
        policy = MaximumLeveragePolicy(RiskProfileConfig(max_leverage=30.0))
        ctx = RiskContext(symbol="EURUSD", leverage=100.0)
        result = await policy.evaluate(ctx)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_leverage_at_limit(self):
        policy = MaximumLeveragePolicy(RiskProfileConfig(max_leverage=50.0))
        ctx = RiskContext(symbol="EURUSD", leverage=50.0)
        result = await policy.evaluate(ctx)
        assert result.passed  # At exactly the limit should pass

    @pytest.mark.asyncio
    async def test_leverage_slightly_above(self):
        policy = MaximumLeveragePolicy(RiskProfileConfig(max_leverage=50.0))
        ctx = RiskContext(symbol="EURUSD", leverage=50.1)
        result = await policy.evaluate(ctx)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_negative_leverage(self):
        policy = MaximumLeveragePolicy()
        ctx = RiskContext(symbol="EURUSD", leverage=-1.0)
        result = await policy.evaluate(ctx)
        assert result.passed  # Negative leverage should pass


# ─── Drawdown ──────────────────────────────────────────────────────────────


class TestDrawdown:
    @pytest.mark.asyncio
    async def test_drawdown_at_maximum(self):
        policy = MaximumDrawdownPolicy(RiskProfileConfig(max_drawdown_pct=20.0))
        ctx = RiskContext(
            symbol="EURUSD",
            drawdown=DrawdownMetrics(current_drawdown=20.0, max_drawdown=20.0),
        )
        result = await policy.evaluate(ctx)
        assert result.passed  # At the limit should pass

    @pytest.mark.asyncio
    async def test_drawdown_exceeds_maximum(self):
        policy = MaximumDrawdownPolicy(RiskProfileConfig(max_drawdown_pct=20.0))
        ctx = RiskContext(
            symbol="EURUSD",
            drawdown=DrawdownMetrics(current_drawdown=25.0, max_drawdown=25.0),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_drawdown_with_no_data(self):
        policy = MaximumDrawdownPolicy()
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed

    @pytest.mark.asyncio
    async def test_negative_drawdown(self):
        policy = MaximumDrawdownPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            drawdown=DrawdownMetrics(current_drawdown=-5.0, max_drawdown=-5.0),
        )
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── News Mode ─────────────────────────────────────────────────────────────


class TestNewsMode:
    @pytest.mark.asyncio
    async def test_news_during_trading(self):
        policy = NewsProtectionPolicy()
        ctx = RiskContext(symbol="EURUSD", is_news_hour=True)
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "news" in result.message.lower()

    @pytest.mark.asyncio
    async def test_news_combined_with_other_checks(self):
        news_policy = NewsProtectionPolicy()
        drawdown_policy = MaximumDrawdownPolicy()

        ctx = RiskContext(
            symbol="EURUSD",
            is_news_hour=True,
            drawdown=DrawdownMetrics(current_drawdown=20.0, max_drawdown=30.0),
        )
        news_result = await news_policy.evaluate(ctx)
        dd_result = await drawdown_policy.evaluate(ctx)

        assert not news_result.passed  # News blocks
        assert dd_result.passed  # Drawdown is fine

    @pytest.mark.asyncio
    async def test_news_not_triggered(self):
        policy = NewsProtectionPolicy()
        ctx = RiskContext(symbol="EURUSD", is_news_hour=False)
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── Trading Lock ──────────────────────────────────────────────────────────


class TestTradingLock:
    @pytest.mark.asyncio
    async def test_trading_lock_blocks(self):
        policy = TradingLockPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            protection_status=AccountProtectionStatus(
                level=AccountProtectionLevel.TRADING_LOCK,
                trading_locked=True,
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "locked" in result.message.lower()

    @pytest.mark.asyncio
    async def test_trading_lock_unlocked(self):
        policy = TradingLockPolicy()
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed

    @pytest.mark.asyncio
    async def test_trading_lock_with_soft_stop(self):
        from libraries.domain.risk.policy import SoftStopPolicy

        soft_stop = SoftStopPolicy()
        trading_lock = TradingLockPolicy()

        ctx = RiskContext(
            symbol="EURUSD",
            drawdown=DrawdownMetrics(current_drawdown=5.0, max_drawdown=10.0),
        )
        soft_result = await soft_stop.evaluate(ctx)
        lock_result = await trading_lock.evaluate(ctx)

        assert soft_result.passed
        assert lock_result.passed


# ─── Cooldown ──────────────────────────────────────────────────────────────


class TestCooldown:
    @pytest.mark.asyncio
    async def test_cooldown_after_consecutive_losses(self):
        from libraries.domain.risk.policy import CooldownTimerPolicy

        policy = CooldownTimerPolicy(
            RiskProfileConfig(
                cooldown_after_loss_minutes=15.0,
                max_consecutive_losses=3,
            )
        )
        await policy.initialize()

        # Simulate consecutive losses
        ctx = RiskContext(symbol="EURUSD", consecutive_losses=5)
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "cooldown" in result.message.lower()

    @pytest.mark.asyncio
    async def test_cooldown_disabled(self):
        from libraries.domain.risk.policy import CooldownTimerPolicy

        policy = CooldownTimerPolicy(RiskProfileConfig(cooldown_after_loss_minutes=0))
        await policy.initialize()
        ctx = RiskContext(symbol="EURUSD", consecutive_losses=10)
        result = await policy.evaluate(ctx)
        assert result.passed

    @pytest.mark.asyncio
    async def test_no_cooldown_without_losses(self):
        from libraries.domain.risk.policy import CooldownTimerPolicy

        policy = CooldownTimerPolicy(RiskProfileConfig(cooldown_after_loss_minutes=15.0))
        await policy.initialize()
        ctx = RiskContext(symbol="EURUSD", consecutive_losses=0)
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── Emergency Stop ────────────────────────────────────────────────────────


class TestEmergencyStop:
    @pytest.mark.asyncio
    async def test_emergency_stop_blocks_all(self):
        policy = EmergencyStopPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            emergency_status=EmergencyModeStatus(
                active=True,
                triggers=(EmergencyTrigger.MANUAL_OVERRIDE,),
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "EMERGENCY STOP" in result.message

    @pytest.mark.asyncio
    async def test_emergency_stop_broker_disconnect(self):
        policy = EmergencyStopPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            emergency_status=EmergencyModeStatus(
                active=True,
                triggers=(EmergencyTrigger.BROKER_DISCONNECT,),
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_emergency_stop_multiple_triggers(self):
        policy = EmergencyStopPolicy()
        ctx = RiskContext(
            symbol="EURUSD",
            emergency_status=EmergencyModeStatus(
                active=True,
                triggers=(
                    EmergencyTrigger.BROKER_DISCONNECT,
                    EmergencyTrigger.MARKET_FEED_FAILURE,
                    EmergencyTrigger.EXTREME_SPREAD,
                ),
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "broker_disconnect" in result.message

    @pytest.mark.asyncio
    async def test_emergency_stop_not_active(self):
        policy = EmergencyStopPolicy()
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── Risk Profiles ─────────────────────────────────────────────────────────


class TestRiskProfiles:
    @pytest.mark.asyncio
    async def test_conservative_allows_less(self):
        conservative = RiskProfileConfig.conservative()
        aggressive = RiskProfileConfig.aggressive()

        assert conservative.max_leverage < aggressive.max_leverage
        assert conservative.max_position_size_pct < aggressive.max_position_size_pct
        assert conservative.max_daily_loss_pct < aggressive.max_daily_loss_pct
        assert conservative.max_open_positions < aggressive.max_open_positions

    @pytest.mark.asyncio
    async def test_balanced_is_middle(self):
        balanced = RiskProfileConfig.balanced()
        conservative = RiskProfileConfig.conservative()
        aggressive = RiskProfileConfig.aggressive()

        assert conservative.max_leverage <= balanced.max_leverage <= aggressive.max_leverage

    @pytest.mark.asyncio
    async def test_aggressive_allows_weekend_trading(self):
        aggressive = RiskProfileConfig.aggressive()
        conservative = RiskProfileConfig.conservative()

        assert aggressive.allow_weekend_trading
        assert not conservative.allow_weekend_trading

    @pytest.mark.asyncio
    async def test_profile_impact_on_policies(self):
        # Conservative profile should reject more than aggressive
        conservative_policies = create_default_policies(RiskProfileConfig.conservative())
        aggressive_policies = create_default_policies(RiskProfileConfig.aggressive())

        ctx = RiskContext(
            symbol="EURUSD",
            leverage=30.0,
            account_balance=Decimal("10000"),
            notional_value=Decimal("300000"),
            daily_pnl=-1800.0,
            open_positions_count=12,
            consecutive_losses=4,
        )

        con_results = [await p.evaluate(ctx) for p in conservative_policies]
        agg_results = [await p.evaluate(ctx) for p in aggressive_policies]

        con_rejected = sum(1 for r in con_results if not r.passed)
        agg_rejected = sum(1 for r in agg_results if not r.passed)

        # Conservative should reject more policies
        assert con_rejected >= agg_rejected


# ─── Combined Edge Cases ───────────────────────────────────────────────────


class TestCombinedScenarios:
    @pytest.mark.asyncio
    async def test_everything_goes_wrong(self):
        """All risk factors are in the danger zone."""
        policies = create_default_policies(RiskProfileConfig.conservative())
        results = []
        for p in policies:
            ctx = RiskContext(
                symbol="EURUSD",
                direction="buy",
                account_balance=Decimal("100"),
                account_equity=Decimal("50"),
                margin_used=Decimal("100"),
                leverage=200.0,
                daily_pnl=-500.0,
                weekly_pnl=-2000.0,
                monthly_pnl=-5000.0,
                consecutive_losses=10,
                open_positions_count=25,
                notional_value=Decimal("1000000"),
                position_size=Decimal("1000000"),
                spread_pips=50.0,
                volatility=3.0,
                liquidity_score=0.05,
                slippage_estimate=20.0,
                market_open=False,
                is_news_hour=True,
                is_weekend=True,
                is_holiday=True,
                broker_connected=False,
                broker_latency_ms=10000.0,
                broker_uptime_pct=50.0,
                data_feed_active=False,
                consensus_quality=0.1,
                provider_health=0.1,
                drawdown=DrawdownMetrics(
                    current_drawdown=50.0,
                    max_drawdown=60.0,
                    is_recovery_mode=True,
                ),
                emergency_status=EmergencyModeStatus(
                    active=True,
                    triggers=(
                        EmergencyTrigger.BROKER_DISCONNECT,
                        EmergencyTrigger.MARKET_FEED_FAILURE,
                    ),
                ),
                protection_status=AccountProtectionStatus(
                    level=AccountProtectionLevel.HARD_STOP,
                    trading_locked=True,
                ),
            )
            result = await p.evaluate(ctx)
            results.append(result)

        # All policies should reject
        assert all(
            not r.passed for r in results
        ), f"Expected all policies to reject, but {sum(1 for r in results if r.passed)} passed"

    @pytest.mark.asyncio
    async def test_everything_perfect(self):
        """All risk factors are ideal."""
        policies = create_default_policies(RiskProfileConfig.aggressive())
        results = []
        for p in policies:
            ctx = RiskContext(
                symbol="EURUSD",
                direction="buy",
                account_balance=Decimal("1000000"),
                account_equity=Decimal("1000000"),
                margin_used=Decimal("0"),
                margin_free=Decimal("1000000"),
                leverage=1.0,
                daily_pnl=500.0,
                weekly_pnl=2000.0,
                monthly_pnl=10000.0,
                consecutive_losses=0,
                open_positions_count=1,
                notional_value=Decimal("10000"),
                spread_pips=0.5,
                volatility=0.1,
                liquidity_score=0.99,
                slippage_estimate=0.1,
                market_open=True,
                is_news_hour=False,
                is_weekend=False,
                is_holiday=False,
                broker_connected=True,
                broker_latency_ms=10.0,
                broker_uptime_pct=99.99,
                data_feed_active=True,
                consensus_quality=0.99,
                provider_health=0.99,
                drawdown=DrawdownMetrics(current_drawdown=0.0, max_drawdown=0.0),
                protection_status=AccountProtectionStatus(),
            )
            result = await p.evaluate(ctx)
            results.append(result)

        # All policies should pass
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_mixed_conditions(self):
        """Mixed risk factors - some good, some bad."""
        policies = create_default_policies(RiskProfileConfig.balanced())
        ctx = RiskContext(
            symbol="EURUSD",
            account_balance=Decimal("50000"),
            account_equity=Decimal("48000"),
            leverage=10.0,
            daily_pnl=-500.0,
            weekly_pnl=-1000.0,
            monthly_pnl=-2000.0,
            consecutive_losses=2,
            open_positions_count=5,
            notional_value=Decimal("500000"),
            spread_pips=3.0,
            volatility=0.5,
            liquidity_score=0.6,
            slippage_estimate=2.0,
            market_open=True,
            is_news_hour=False,
            is_weekend=False,
            is_holiday=False,
            broker_connected=True,
            broker_latency_ms=100.0,
            broker_uptime_pct=99.0,
            data_feed_active=True,
            consensus_quality=0.8,
            provider_health=0.85,
            drawdown=DrawdownMetrics(current_drawdown=10.0, max_drawdown=15.0),
        )
        results = [await p.evaluate(ctx) for p in policies]
        passed = sum(1 for r in results if r.passed)
        rejected = sum(1 for r in results if not r.passed)

        # Some should pass, some should fail
        assert passed > 0, "Expected some policies to pass"
        assert rejected > 0, "Expected some policies to reject"
