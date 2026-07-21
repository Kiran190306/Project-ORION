"""Tests for all 24 risk policy implementations."""
from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.risk.context import RiskContext
from libraries.domain.risk.models import DrawdownMetrics, PolicyCategory, PolicySeverity
from libraries.domain.risk.policy import (
    BrokerHealthProtectionPolicy,
    CooldownTimerPolicy,
    EmergencyStopPolicy,
    HardStopPolicy,
    HolidayProtectionPolicy,
    LiquidityProtectionPolicy,
    MarginProtectionPolicy,
    MarketDataQualityProtectionPolicy,
    MaximumConsecutiveLossesPolicy,
    MaximumCurrencyExposurePolicy,
    MaximumDailyLossPolicy,
    MaximumDrawdownPolicy,
    MaximumExposurePolicy,
    MaximumLeveragePolicy,
    MaximumMonthlyLossPolicy,
    MaximumOpenPositionsPolicy,
    MaximumPositionSizePolicy,
    MaximumSymbolExposurePolicy,
    MaximumWeeklyLossPolicy,
    NewsProtectionPolicy,
    RecoveryModePolicy,
    SlippageProtectionPolicy,
    SoftStopPolicy,
    SpreadProtectionPolicy,
    TradingHoursProtectionPolicy,
    TradingLockPolicy,
    VolatilityProtectionPolicy,
    WeekendProtectionPolicy,
    create_default_policies,
)
from libraries.domain.risk.profile import RiskProfileConfig


# ─── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def default_config() -> RiskProfileConfig:
    return RiskProfileConfig()


@pytest.fixture
def safe_context() -> RiskContext:
    return RiskContext(
        symbol="EURUSD",
        direction="buy",
        account_balance=Decimal("100000"),
        account_equity=Decimal("100000"),
        margin_used=Decimal("0"),
        margin_free=Decimal("100000"),
        leverage=1.0,
        daily_pnl=-100.0,
        weekly_pnl=-200.0,
        monthly_pnl=-500.0,
        consecutive_losses=1,
        open_positions_count=2,
        spread_pips=1.5,
        volatility=0.3,
        liquidity_score=0.8,
        slippage_estimate=0.5,
        market_open=True,
        is_news_hour=False,
        is_weekend=False,
        is_holiday=False,
        broker_connected=True,
        broker_latency_ms=50.0,
        broker_uptime_pct=99.9,
        data_feed_active=True,
        consensus_quality=0.9,
        provider_health=0.95,
        drawdown=DrawdownMetrics(current_drawdown=5.0, max_drawdown=15.0),
    )


@pytest.fixture
def risky_context() -> RiskContext:
    return RiskContext(
        symbol="EURUSD",
        direction="buy",
        account_balance=Decimal("10000"),
        account_equity=Decimal("8000"),
        margin_used=Decimal("5000"),
        margin_free=Decimal("3000"),
        leverage=50.0,
        daily_pnl=-1500.0,
        weekly_pnl=-3000.0,
        monthly_pnl=-8000.0,
        consecutive_losses=6,
        open_positions_count=15,
        notional_value=Decimal("500000"),
        position_size=Decimal("500000"),
        spread_pips=15.0,
        volatility=1.5,
        liquidity_score=0.1,
        slippage_estimate=8.0,
        market_open=False,
        is_news_hour=True,
        is_weekend=True,
        is_holiday=True,
        broker_connected=False,
        broker_latency_ms=5000.0,
        broker_uptime_pct=85.0,
        data_feed_active=False,
        consensus_quality=0.2,
        provider_health=0.3,
        drawdown=DrawdownMetrics(
            current_drawdown=35.0,
            max_drawdown=40.0,
            is_recovery_mode=True,
        ),
    )


# ─── Tests: Base Policy ───────────────────────────────────────────────────


class TestBasePolicyProperties:
    def test_policy_names_unique(self):
        policies = create_default_policies()
        names = [p.name for p in policies]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"

    def test_all_policies_have_description(self):
        for p in create_default_policies():
            assert p.description, f"Policy '{p.name}' missing description"

    def test_all_policies_have_category(self):
        for p in create_default_policies():
            assert isinstance(p.category, PolicyCategory), f"Policy '{p.name}' invalid category"

    def test_all_policies_have_severity(self):
        for p in create_default_policies():
            assert isinstance(p.severity, PolicySeverity), f"Policy '{p.name}' invalid severity"

    def test_all_policies_enabled_by_default(self):
        for p in create_default_policies():
            assert p.enabled, f"Policy '{p.name}' not enabled by default"

    def test_all_policies_have_positive_priority(self):
        for p in create_default_policies():
            assert p.priority >= 0, f"Policy '{p.name}' has negative priority"

    def test_statistics_structure(self):
        policies = create_default_policies()
        for p in policies[:3]:
            stats = p.statistics()
            assert "policy_name" in stats
            assert "evaluation_count" in stats
            assert "pass_count" in stats


# ─── Tests: Position Sizing ───────────────────────────────────────────────


class TestMaximumPositionSizePolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_position(self, safe_context, default_config):
        policy = MaximumPositionSizePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_large_position(self, risky_context, default_config):
        policy = MaximumPositionSizePolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed
        assert "exceeds" in result.message.lower()

    @pytest.mark.asyncio
    async def test_skipped_when_no_limit(self):
        cfg = RiskProfileConfig(max_position_size_pct=0)
        policy = MaximumPositionSizePolicy(cfg)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed

    @pytest.mark.asyncio
    async def test_properties(self, default_config):
        policy = MaximumPositionSizePolicy(default_config)
        assert policy.name == "maximum_position_size"
        assert policy.category == PolicyCategory.POSITION_SIZING


# ─── Tests: Loss Limits ───────────────────────────────────────────────────


class TestMaximumDailyLossPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_loss(self, safe_context, default_config):
        policy = MaximumDailyLossPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_excessive_loss(self, risky_context, default_config):
        policy = MaximumDailyLossPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_disabled(self):
        cfg = RiskProfileConfig(max_daily_loss_pct=0)
        policy = MaximumDailyLossPolicy(cfg)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


class TestMaximumWeeklyLossPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_loss(self, safe_context, default_config):
        policy = MaximumWeeklyLossPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_excessive_loss(self, risky_context, default_config):
        policy = MaximumWeeklyLossPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestMaximumMonthlyLossPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_loss(self, safe_context, default_config):
        policy = MaximumMonthlyLossPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_excessive_loss(self, risky_context, default_config):
        policy = MaximumMonthlyLossPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_critical_severity(self, default_config):
        policy = MaximumMonthlyLossPolicy(default_config)
        assert policy.severity == PolicySeverity.CRITICAL


class TestMaximumDrawdownPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_dd(self, safe_context, default_config):
        policy = MaximumDrawdownPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_excessive_dd(self, risky_context, default_config):
        policy = MaximumDrawdownPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed

    @pytest.mark.asyncio
    async def test_no_drawdown_data(self, default_config):
        policy = MaximumDrawdownPolicy(default_config)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed  # passes when no data


class TestMaximumConsecutiveLossesPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_few_losses(self, safe_context, default_config):
        policy = MaximumConsecutiveLossesPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_many_losses(self, risky_context, default_config):
        policy = MaximumConsecutiveLossesPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


# ─── Tests: Exposure ──────────────────────────────────────────────────────


class TestMaximumExposurePolicy:
    @pytest.mark.asyncio
    async def test_passes_with_low_exposure(self, safe_context, default_config):
        policy = MaximumExposurePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_no_exposure_data(self, default_config):
        policy = MaximumExposurePolicy(default_config)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


class TestMaximumSymbolExposurePolicy:
    @pytest.mark.asyncio
    async def test_passes(self, safe_context, default_config):
        policy = MaximumSymbolExposurePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_no_data(self, default_config):
        policy = MaximumSymbolExposurePolicy(default_config)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


class TestMaximumCurrencyExposurePolicy:
    @pytest.mark.asyncio
    async def test_passes_without_data(self, safe_context, default_config):
        policy = MaximumCurrencyExposurePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_passes_within_limits(self, default_config):
        from libraries.domain.risk.models import PortfolioRisk
        policy = MaximumCurrencyExposurePolicy(default_config)
        ctx = RiskContext(
            symbol="EURUSD",
            portfolio_risk=PortfolioRisk(
                currency_exposure={"USD": Decimal("5000")},
            ),
            account_balance=Decimal("100000"),
        )
        result = await policy.evaluate(ctx)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_excessive_currency(self, default_config):
        from libraries.domain.risk.models import PortfolioRisk
        policy = MaximumCurrencyExposurePolicy(default_config)
        ctx = RiskContext(
            symbol="EURUSD",
            portfolio_risk=PortfolioRisk(
                currency_exposure={"USD": Decimal("50000"), "EUR": Decimal("40000")},
            ),
            account_balance=Decimal("100000"),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed


# ─── Tests: Leverage ──────────────────────────────────────────────────────


class TestMaximumLeveragePolicy:
    @pytest.mark.asyncio
    async def test_passes_with_low_leverage(self, safe_context, default_config):
        policy = MaximumLeveragePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_high_leverage(self, risky_context, default_config):
        policy = MaximumLeveragePolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestMaximumOpenPositionsPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_few_positions(self, safe_context, default_config):
        policy = MaximumOpenPositionsPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_many_positions(self, risky_context, default_config):
        policy = MaximumOpenPositionsPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


# ─── Tests: Market Conditions ─────────────────────────────────────────────


class TestMarginProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_safe_margin(self, safe_context, default_config):
        policy = MarginProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_low_margin(self, risky_context, default_config):
        policy = MarginProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestSpreadProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_tight_spread(self, safe_context, default_config):
        policy = SpreadProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_wide_spread(self, risky_context, default_config):
        policy = SpreadProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestVolatilityProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_low_volatility(self, safe_context, default_config):
        policy = VolatilityProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_high_volatility(self, risky_context, default_config):
        policy = VolatilityProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestLiquidityProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_good_liquidity(self, safe_context, default_config):
        policy = LiquidityProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_poor_liquidity(self, risky_context, default_config):
        policy = LiquidityProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestSlippageProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_low_slippage(self, safe_context, default_config):
        policy = SlippageProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_high_slippage(self, risky_context, default_config):
        policy = SlippageProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


# ─── Tests: Trading Hours ─────────────────────────────────────────────────


class TestNewsProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_when_no_news(self, safe_context, default_config):
        policy = NewsProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_during_news(self, risky_context, default_config):
        policy = NewsProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestTradingHoursProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_during_market_hours(self, safe_context, default_config):
        policy = TradingHoursProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_when_market_closed(self, risky_context, default_config):
        policy = TradingHoursProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestWeekendProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_on_weekday(self, safe_context, default_config):
        policy = WeekendProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_on_weekend(self, risky_context, default_config):
        policy = WeekendProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestHolidayProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_on_normal_day(self, safe_context, default_config):
        policy = HolidayProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_on_holiday(self, risky_context, default_config):
        policy = HolidayProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


# ─── Tests: Account Protection ────────────────────────────────────────────


class TestSoftStopPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_loss(self, safe_context, default_config):
        policy = SoftStopPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_large_loss(self, risky_context, default_config):
        policy = SoftStopPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed


class TestHardStopPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_small_loss(self, safe_context, default_config):
        policy = HardStopPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_large_loss(self, risky_context, default_config):
        policy = HardStopPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed
        assert "HARD STOP" in result.message

    @pytest.mark.asyncio
    async def test_critical_severity(self, default_config):
        policy = HardStopPolicy(default_config)
        assert policy.severity == PolicySeverity.CRITICAL


class TestTradingLockPolicy:
    @pytest.mark.asyncio
    async def test_passes_when_unlocked(self, safe_context, default_config):
        policy = TradingLockPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_when_locked(self, default_config):
        from libraries.domain.risk.models import AccountProtectionStatus, AccountProtectionLevel
        policy = TradingLockPolicy(default_config)
        ctx = RiskContext(
            symbol="EURUSD",
            protection_status=AccountProtectionStatus(
                level=AccountProtectionLevel.TRADING_LOCK,
                trading_locked=True,
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed


class TestCooldownTimerPolicy:
    @pytest.mark.asyncio
    async def test_passes_when_no_cooldown(self, safe_context, default_config):
        policy = CooldownTimerPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_disabled_when_zero(self, default_config):
        cfg = RiskProfileConfig(cooldown_after_loss_minutes=0)
        policy = CooldownTimerPolicy(cfg)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


class TestRecoveryModePolicy:
    @pytest.mark.asyncio
    async def test_passes_in_normal_mode(self, safe_context, default_config):
        policy = RecoveryModePolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_handles_no_drawdown_data(self, default_config):
        policy = RecoveryModePolicy(default_config)
        ctx = RiskContext(symbol="EURUSD")
        result = await policy.evaluate(ctx)
        assert result.passed


# ─── Tests: System Health ─────────────────────────────────────────────────


class TestBrokerHealthProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_healthy_broker(self, safe_context, default_config):
        policy = BrokerHealthProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_when_disconnected(self, risky_context, default_config):
        policy = BrokerHealthProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed
        assert "disconnected" in result.message


class TestMarketDataQualityProtectionPolicy:
    @pytest.mark.asyncio
    async def test_passes_with_good_quality(self, safe_context, default_config):
        policy = MarketDataQualityProtectionPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_with_poor_quality(self, risky_context, default_config):
        policy = MarketDataQualityProtectionPolicy(default_config)
        result = await policy.evaluate(risky_context)
        assert not result.passed
        assert "data feed" in result.message.lower() or "quality" in result.message.lower()


# ─── Tests: Emergency ─────────────────────────────────────────────────────


class TestEmergencyStopPolicy:
    @pytest.mark.asyncio
    async def test_passes_when_no_emergency(self, safe_context, default_config):
        policy = EmergencyStopPolicy(default_config)
        result = await policy.evaluate(safe_context)
        assert result.passed

    @pytest.mark.asyncio
    async def test_fails_during_emergency(self, default_config):
        from libraries.domain.risk.models import EmergencyModeStatus, EmergencyTrigger
        policy = EmergencyStopPolicy(default_config)
        ctx = RiskContext(
            symbol="EURUSD",
            emergency_status=EmergencyModeStatus(
                active=True,
                triggers=(EmergencyTrigger.BROKER_DISCONNECT,),
            ),
        )
        result = await policy.evaluate(ctx)
        assert not result.passed
        assert "EMERGENCY STOP" in result.message

    @pytest.mark.asyncio
    async def test_critical_severity(self, default_config):
        policy = EmergencyStopPolicy(default_config)
        assert policy.severity == PolicySeverity.CRITICAL
        assert policy.priority == 5  # Runs early in chain


# ─── Tests: Factory ───────────────────────────────────────────────────────


class TestCreateDefaultPolicies:
    def test_returns_correct_count(self):
        policies = create_default_policies()
        assert len(policies) == 28  # 24 policies

    def test_all_policies_initialized(self):
        policies = create_default_policies()
        for p in policies:
            assert hasattr(p, "initialize")
            assert hasattr(p, "dispose")
            assert hasattr(p, "evaluate")

    def test_accepts_custom_config(self):
        cfg = RiskProfileConfig(max_leverage=10.0)
        policies = create_default_policies(cfg)
        assert len(policies) == 28

