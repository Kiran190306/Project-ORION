"""Unit tests for Strategy Registry Canonical Instrument & Timeframe Alignment (Phase 4.4).

Verifies that all registered strategy catalogue entries expose verified canonical
instruments (8 pairs) and timeframes (9 intervals), reject phantom EUR/GBP,
normalize through canonical market-data primitives, preserve parameters and versions,
and maintain 100% execution compatibility.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src import dependencies
from apps.trading_engine.src.main import create_app
from fastapi.testclient import TestClient

from libraries.domain.market_data.models import BarType
from libraries.domain.market_data.normalization import (
    bar_type_to_timeframe,
    canonical_instruments,
    normalize_symbol,
    normalize_timeframe,
)
from libraries.domain.patterns.models import (
    CandlestickPattern,
    PatternDirection,
    PatternStrength,
)
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    SignalDirection,
    StrategyContext,
    StrategyMetadata,
)
from libraries.domain.strategy.registry import (
    ParameterDefinition,
    StrategyCatalogueEntry,
    StrategyRegistry,
    UnknownStrategyError,
)
from libraries.domain.subscription.models import PlanLimits

# The 8 canonical forex instruments
CANONICAL_SYMBOLS = (
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "XAU/USD",
)

# The 9 canonical timeframe names
CANONICAL_TIMEFRAMES = (
    "M1",
    "M5",
    "M15",
    "M30",
    "H1",
    "H4",
    "D1",
    "W1",
    "MN1",
)

EXPECTED_STRATEGIES = (
    "trend_following",
    "mean_reversion",
    "breakout",
    "momentum",
    "candlestick_reversal",
)


# ─── 1. Registry Content & Integrity ──────────────────────────────────────────


def test_registry_contains_all_executable_strategies() -> None:
    """StrategyRegistry must contain exactly all 5 canonical executable strategies."""
    entries = StrategyRegistry.list_strategies()
    strategy_ids = {e.strategy_id for e in entries}
    for expected_id in EXPECTED_STRATEGIES:
        assert expected_id in strategy_ids
    assert len(strategy_ids) == len(EXPECTED_STRATEGIES)


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_strategy_metadata_invariants(strat_id: str) -> None:
    """Each strategy must maintain its identifier, version 1.0.0, and deterministic flag."""
    entry = StrategyRegistry.get(strat_id)
    assert entry.strategy_id == strat_id
    assert entry.version == "1.0.0"
    assert entry.is_deterministic is True
    assert issubclass(entry.strategy_class, BaseStrategy)
    assert len(entry.parameters) > 0


# ─── 2. Instrument Alignment & Phantom Rejection ─────────────────────────────


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_no_registered_strategy_advertises_eur_gbp(strat_id: str) -> None:
    """No registered strategy may advertise unsupported EUR/GBP."""
    entry = StrategyRegistry.get(strat_id)
    assert "EUR/GBP" not in entry.supported_instruments


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_all_advertised_instruments_are_canonical(strat_id: str) -> None:
    """Every advertised instrument in the catalogue must normalize through normalize_symbol."""
    entry = StrategyRegistry.get(strat_id)
    canonical_dict = canonical_instruments()

    for symbol in entry.supported_instruments:
        # Must normalize without error
        normalized = normalize_symbol(symbol)
        assert normalized == symbol
        # Must be an active member of canonical_instruments
        assert symbol in canonical_dict
        assert canonical_dict[symbol].is_active is True


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_all_eight_canonical_instruments_present(strat_id: str) -> None:
    """All 8 canonical instruments must be present in every reference strategy's catalogue entry."""
    entry = StrategyRegistry.get(strat_id)
    for expected_symbol in CANONICAL_SYMBOLS:
        assert expected_symbol in entry.supported_instruments
    assert len(entry.supported_instruments) == len(CANONICAL_SYMBOLS)


# ─── 3. Timeframe Alignment & Bridge Mapping ─────────────────────────────────


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_all_nine_canonical_timeframes_present(strat_id: str) -> None:
    """All 9 canonical timeframes (including M30, W1, MN1) must be in catalogue entries."""
    entry = StrategyRegistry.get(strat_id)
    for expected_tf in CANONICAL_TIMEFRAMES:
        assert expected_tf in entry.supported_timeframes
    assert len(entry.supported_timeframes) == len(CANONICAL_TIMEFRAMES)


@pytest.mark.parametrize("strat_id", EXPECTED_STRATEGIES)
def test_all_advertised_timeframes_map_through_bridge(strat_id: str) -> None:
    """Every advertised timeframe must resolve to BarType and convert to domain Timeframe."""
    entry = StrategyRegistry.get(strat_id)
    for tf_str in entry.supported_timeframes:
        bar_type = normalize_timeframe(tf_str)
        assert isinstance(bar_type, BarType)
        # Roundtrip to backtesting Timeframe enum
        domain_tf = bar_type_to_timeframe(bar_type)
        assert domain_tf is not None


# ─── 4. Parameter Definitions Stability ──────────────────────────────────────


def test_strategy_parameter_definitions_unchanged() -> None:
    """Parameter schema definitions must retain their original bounds, defaults, and types."""
    tf_entry = StrategyRegistry.get("trend_following")
    tf_params = {p.name: p for p in tf_entry.parameters}
    assert tf_params["fast_period"].default == 10
    assert tf_params["fast_period"].min_value == 2
    assert tf_params["fast_period"].max_value == 100
    assert tf_params["slow_period"].default == 30

    mr_entry = StrategyRegistry.get("mean_reversion")
    mr_params = {p.name: p for p in mr_entry.parameters}
    assert mr_params["lookback_period"].default == 20
    assert mr_params["entry_threshold"].default == 2.0

    bo_entry = StrategyRegistry.get("breakout")
    bo_params = {p.name: p for p in bo_entry.parameters}
    assert bo_params["channel_period"].default == 20
    assert bo_params["breakout_multiplier"].default == 1.0

    mom_entry = StrategyRegistry.get("momentum")
    mom_params = {p.name: p for p in mom_entry.parameters}
    assert mom_params["momentum_period"].default == 14
    assert mom_params["momentum_threshold"].default == 0.02

    cr_entry = StrategyRegistry.get("candlestick_reversal")
    cr_params = {p.name: p for p in cr_entry.parameters}
    assert cr_params["pattern_id"].default == "any_reversal"
    assert cr_params["pattern_direction"].default == "all"
    assert cr_params["min_strength"].default == "moderate"
    assert cr_params["min_confidence"].default == 0.70


# ─── 5. Strategy Factory & Execution Behavior ────────────────────────────────


def test_factory_instantiation_uses_canonical_tags_when_symbols_omitted() -> None:
    """create_strategy() defaults metadata.tags to canonical instruments when symbols is None."""
    instance = StrategyRegistry.create_strategy("trend_following")
    assert instance.metadata.tags == list(CANONICAL_SYMBOLS)


def test_factory_instantiation_honors_explicit_symbols() -> None:
    """create_strategy() sets metadata.tags to provided symbols."""
    instance = StrategyRegistry.create_strategy("trend_following", symbols=["USD/JPY", "XAU/USD"])
    assert instance.metadata.tags == ["USD/JPY", "XAU/USD"]


@pytest.mark.asyncio
async def test_trend_following_execution_unchanged() -> None:
    """TrendFollowingStrategy generates signals across price series unchanged."""
    strategy = StrategyRegistry.create_strategy("trend_following", {"fast_period": 2, "slow_period": 5})
    now = datetime.now(timezone.utc)

    # Feed increasing prices: 10.0, 11.0, 12.0, 13.0, 14.0
    for p in [10.0, 11.0, 12.0, 13.0, 14.0]:
        ctx = StrategyContext(
            strategy_id="trend_following",
            symbol="EUR/USD",
            current_price=Decimal(str(p)),
            timestamp=now,
        )
        sig = await strategy.generate_signal(ctx)

    assert sig is not None
    assert sig.direction == SignalDirection.BUY
    assert sig.symbol == "EUR/USD"


@pytest.mark.asyncio
async def test_candlestick_reversal_execution_unchanged() -> None:
    """CandlestickReversalStrategy generates signal on bullish pattern unchanged."""
    strategy = StrategyRegistry.create_strategy("candlestick_reversal")
    now = datetime.now(timezone.utc)

    pattern = CandlestickPattern(
        pattern_id="hammer",
        name="Hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        candle_index=0,
        timestamp=now,
        description="Hammer bullish reversal",
        confidence=Decimal("0.85"),
        metadata={"high": "1.08500", "low": "1.08000"},
    )
    ctx = StrategyContext(
        strategy_id="candlestick_reversal",
        symbol="EUR/USD",
        current_price=Decimal("1.08300"),
        timestamp=now,
        metadata={"patterns": [pattern]},
    )
    sig = await strategy.generate_signal(ctx)
    assert sig is not None
    assert sig.direction == SignalDirection.BUY
    assert sig.metadata["stop_loss"] == str(Decimal("1.08000") - Decimal("0.0001"))


# ─── 6. Custom Strategy Registration Override ────────────────────────────────


def test_custom_catalogue_entry_can_override_restrictions() -> None:
    """A specialized strategy can declare restrictive instruments and timeframes."""
    custom_entry = StrategyCatalogueEntry(
        strategy_id="custom_specialized",
        name="Custom Specialized",
        description="Restricted strategy",
        category="custom",
        strategy_class=StrategyRegistry.get("trend_following").strategy_class,
        supported_instruments=("EUR/USD",),
        supported_timeframes=("H1",),
    )
    assert custom_entry.supported_instruments == ("EUR/USD",)
    assert custom_entry.supported_timeframes == ("H1",)


# ─── 7. Subscription Entitlements Isolation ──────────────────────────────────


def test_plan_limits_asset_allowed_is_unaffected() -> None:
    """PlanLimits.is_asset_allowed() remains independent of StrategyCatalogueEntry."""
    free_limits = PlanLimits(
        max_accounts=1,
        max_daily_orders=10,
        max_workers=0,
        allowed_assets=("EUR/USD", "GBP/USD", "USD/JPY"),
        retention_days=30,
    )
    assert free_limits.is_asset_allowed("EUR/USD") is True
    assert free_limits.is_asset_allowed("XAU/USD") is False  # Pro-only asset remains restricted in Free

    pro_limits = PlanLimits(
        max_accounts=5,
        max_daily_orders=100,
        max_workers=2,
        allowed_assets=("*",),
        retention_days=365,
    )
    assert pro_limits.is_asset_allowed("XAU/USD") is True


# ─── 8. API Parity & Compatibility ───────────────────────────────────────────


@pytest.fixture
def test_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[dependencies.get_current_active_user] = lambda: {
        "id": "usr-test",
        "username": "testuser",
        "is_active": True,
        "is_superuser": False,
    }
    app.dependency_overrides[dependencies.get_tenant_context] = lambda: dependencies.TenantContext(
        user_id="usr-test",
        organization_id=None,
        role=None,
        is_superuser=False,
    )
    return TestClient(app)


def test_api_strategies_endpoint_returns_canonical_universe(test_client: TestClient) -> None:
    """GET /api/v1/strategies/ returns 8 canonical symbols and 9 timeframes per strategy."""
    resp = test_client.get("/api/v1/strategies/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5

    for strat in data["strategies"]:
        assert strat["symbols"] == list(CANONICAL_SYMBOLS)
        assert strat["timeframes"] == list(CANONICAL_TIMEFRAMES)
        assert "EUR/GBP" not in strat["symbols"]


def test_api_no_metadata_only_strategies(test_client: TestClient) -> None:
    """Metadata-only non-executable strategies return 404 from API detail endpoint."""
    for phantom in ["reversal", "scalping", "swing", "carry_trade", "news_trading"]:
        resp = test_client.get(f"/api/v1/strategies/{phantom}")
        assert resp.status_code == 404
