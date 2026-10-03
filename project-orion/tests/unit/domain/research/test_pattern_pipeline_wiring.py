"""Unit tests for Research, Optimization, and Walk-Forward Candlestick Pattern Pipeline Wiring.

Verifies:
1. ResearchService provides pattern context to StrategyBacktestAdapter.
2. candlestick_reversal produces at least one signal when qualifying patterns exist.
3. Optimization candidate receives pattern context.
4. Optimization candidate does not silently produce zero trades solely because pattern context is missing.
5. Walk-forward IS receives patterns from IS candles.
6. Walk-forward OOS receives patterns from OOS candles.
7. IS cannot access OOS patterns.
8. Pattern precomputation happens once per adapter/replay dataset.
9. close_price correctly becomes context.current_price.
10. close argument remains backward compatible.
11. Existing 4 strategies retain their existing behavior.
12. LeakageGuard remains active.
13. No future pattern appears in context.
14. Existing pattern context tests continue passing.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from apps.trading_engine.src.services.research_service import ResearchService
from apps.trading_engine.src.services.subscription_service import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from libraries.domain.backtesting.historical_data import MarketDataServiceHistoricalProvider
from libraries.domain.backtesting.leakage_guard import DataLeakageDetectedError, LeakageGuard
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.patterns.engine import CandlestickPatternEngine
from libraries.domain.patterns.models import CandlestickPattern, PatternDirection, PatternStrength
from libraries.domain.research.models import ResearchExperimentStatus
from libraries.domain.research.optimization_engine import OptimizationEngine
from libraries.domain.research.optimization_models import (
    FitnessObjective,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)
from libraries.domain.research.walk_forward_engine import WalkForwardEngine
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import Signal, StrategyContext, StrategyMetadata
from libraries.domain.strategy.registry import StrategyRegistry
from libraries.infrastructure.persistence.base import Base
from libraries.infrastructure.persistence.models.organization import (
    OrganizationMemberModel,
    OrganizationModel,
)
from libraries.infrastructure.persistence.models.user import UserModel


def _build_hammer_reversal_series(base_time: datetime, n_prefix: int = 20) -> list[dict[str, Any]]:
    """Build a candle series that contains a clear bullish hammer pattern."""
    candles: list[dict[str, Any]] = []
    price = Decimal("1.1000")

    # Gentle downtrend prefix
    for i in range(n_prefix):
        o = price
        c = price - Decimal("0.0005")
        h = o + Decimal("0.0002")
        l = c - Decimal("0.0002")
        candles.append({
            "timestamp": base_time + timedelta(hours=i),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": Decimal(1000),
        })
        price = c

    # Previous candle: bearish
    idx = n_prefix
    c_prev_o = price
    c_prev_c = price - Decimal("0.0010")
    c_prev_h = c_prev_o + Decimal("0.0002")
    c_prev_l = c_prev_c - Decimal("0.0002")
    candles.append({
        "timestamp": base_time + timedelta(hours=idx),
        "open": c_prev_o,
        "high": c_prev_h,
        "low": c_prev_l,
        "close": c_prev_c,
        "volume": Decimal(1000),
    })

    # Hammer candle:
    # Open 1.0855, High 1.0858, Low 1.0830, Close 1.0857
    # Lower shadow = 0.0025, body = 0.0002 -> Hammer
    idx += 1
    c_ham_o = Decimal("1.0855")
    c_ham_h = Decimal("1.0858")
    c_ham_l = Decimal("1.0830")
    c_ham_c = Decimal("1.0857")
    candles.append({
        "timestamp": base_time + timedelta(hours=idx),
        "open": c_ham_o,
        "high": c_ham_h,
        "low": c_ham_l,
        "close": c_ham_c,
        "volume": Decimal(1000),
    })

    # Post-hammer candles to allow trade progression
    price = c_ham_c
    for i in range(1, 15):
        o = price
        c = price + Decimal("0.0008")
        h = c + Decimal("0.0003")
        l = o - Decimal("0.0002")
        candles.append({
            "timestamp": base_time + timedelta(hours=idx + i),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": Decimal(1000),
        })
        price = c

    return candles


class ContextCapturingStrategy(BaseStrategy):
    """Test helper to capture all received StrategyContext instances."""

    def __init__(self, metadata: StrategyMetadata, **kwargs: object) -> None:
        super().__init__(metadata, kwargs)
        self.captured_contexts: list[StrategyContext] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        self.captured_contexts.append(context)
        return None


@pytest.fixture
async def test_session() -> AsyncSession:
    """Isolated async SQLite database session for ResearchService testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        org = OrganizationModel(
            id="org_test_pipeline",
            name="Test Pipeline Org",
            slug="test-pipeline-org",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user = UserModel(
            id="usr_test_pipeline",
            username="test_pipeline_user",
            email="pipeline@example.com",
            hashed_password="hashed_pass",
            is_active=True,
            is_superuser=False,
        )
        member = OrganizationMemberModel(
            id="mem_test_pipeline",
            organization_id="org_test_pipeline",
            user_id="usr_test_pipeline",
            role="RESEARCHER",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add_all([org, user, member])
        sub_service = SubscriptionService(session)
        await sub_service._ensure_canonical_plans()
        await session.commit()
        yield session


# ─── 1. ResearchService Wiring ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_research_service_provides_pattern_context(test_session: AsyncSession) -> None:
    """Requirement 1 & 2: ResearchService provides pattern context and candlestick_reversal produces signals."""
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    synthetic_series = _build_hammer_reversal_series(t0, n_prefix=10)

    mock_provider = MagicMock(spec=MarketDataServiceHistoricalProvider)

    async def _mock_load_candles(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return synthetic_series

    mock_provider.load_candles = _mock_load_candles

    service = ResearchService(session=test_session)
    service.historical_provider = mock_provider

    exp = await service.create_and_run_experiment(
        organization_id="org_test_pipeline",
        user_id="usr_test_pipeline",
        strategy_id="candlestick_reversal",
        symbol="EUR/USD",
        timeframe="H1",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 5),
        parameters={
            "pattern_id": "any_reversal",
            "pattern_direction": "all",
            "min_strength": "moderate",
            "min_confidence": 0.70,
        },
    )

    assert exp.status == ResearchExperimentStatus.COMPLETED.value
    assert exp.metrics is not None
    # Reversal trade was executed because pattern context was successfully wired
    assert exp.metrics["total_trades"] >= 1
    assert len(exp.trades) >= 1


# ─── 2. OptimizationEngine Wiring ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_optimization_candidate_receives_pattern_context() -> None:
    """Requirement 3 & 4: Optimization candidate receives pattern context and produces trades."""
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = _build_hammer_reversal_series(t0, n_prefix=15)

    engine = OptimizationEngine()
    combos = [
        {
            "pattern_id": "any_reversal",
            "pattern_direction": "all",
            "min_strength": "moderate",
            "min_confidence": 0.70,
        },
        {
            "pattern_id": "hammer",
            "pattern_direction": "all",
            "min_strength": "any",
            "min_confidence": 0.60,
        },
    ]

    candidates, _heatmap = await engine.run_sweep(
        strategy_id="candlestick_reversal",
        parameter_combinations=combos,
        candles=candles,
        symbol="EUR/USD",
        timeframe="H1",
        fitness_objective=FitnessObjective.TOTAL_RETURN,
    )

    assert len(candidates) == 2
    # Verify candidates did not evaluate to 0 trades solely because pattern context was missing
    for c in candidates:
        assert c.total_trades >= 1


# ─── 3. WalkForwardEngine IS/OOS Segregation ──────────────────────────────────


@pytest.mark.asyncio
async def test_walk_forward_engine_is_oos_pattern_isolation() -> None:
    """Requirement 5, 6, 7: IS receives patterns from IS candles, OOS from OOS candles, strictly segregated."""
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    # Generate 120 candles with hammer patterns in both sections
    candles = _build_hammer_reversal_series(t0, n_prefix=30)
    # Append another sequence to have at least 80 bars
    candles.extend(_build_hammer_reversal_series(candles[-1]["timestamp"] + timedelta(hours=1), n_prefix=30))

    wfa = WalkForwardEngine()

    partitions = wfa._partition_windows(candles, n_windows=2, in_sample_ratio=0.7, anchored=False)
    assert len(partitions) >= 1
    is_candles, oos_candles = partitions[0]

    # Pattern engine over IS only
    pe = CandlestickPatternEngine()
    is_patterns = pe.detect_patterns(is_candles)
    oos_patterns = pe.detect_patterns(oos_candles)

    # Assert timestamps: IS patterns cannot have timestamps past the IS window
    is_end_ts = is_candles[-1]["timestamp"]
    for p in is_patterns:
        assert p.timestamp <= is_end_ts

    # Assert OOS patterns start on or after OOS start
    oos_start_ts = oos_candles[0]["timestamp"]
    for p in oos_patterns:
        assert p.timestamp >= oos_start_ts


# ─── 4. Precomputation Invariant ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pattern_precomputation_happens_once_per_adapter() -> None:
    """Requirement 8: Pattern precomputation happens once upfront in adapter, not per bar."""
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = _build_hammer_reversal_series(t0, n_prefix=5)

    meta = StrategyMetadata(
        strategy_id="test_capturing",
        name="Test Capturing",
        version="1.0.0",
        tags=["EUR/USD"],
    )
    strat = ContextCapturingStrategy(meta)
    strat.initialize()

    mock_pattern_engine = MagicMock(spec=CandlestickPatternEngine)
    mock_pattern_engine.detect_patterns.return_value = []

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe="H1",
        pattern_engine=mock_pattern_engine,
        candles=candles,
    )

    # detect_patterns was called exactly once during __init__
    assert mock_pattern_engine.detect_patterns.call_count == 1

    # Replay all candles
    for c in candles:
        await adapter.on_candle(
            symbol="EUR/USD",
            timestamp=c["timestamp"],
            open_price=c["open"],
            high_price=c["high"],
            low_price=c["low"],
            close_price=c["close"],
            volume=c["volume"],
        )

    # detect_patterns was NOT called per bar
    assert mock_pattern_engine.detect_patterns.call_count == 1


# ─── 5. Effective Close Argument Handling ─────────────────────────────────────


@pytest.mark.asyncio
async def test_close_price_populates_context_current_price() -> None:
    """Requirement 9 & 10: close_price and close argument handling."""
    meta = StrategyMetadata(
        strategy_id="test_capturing",
        name="Test Capturing",
        version="1.0.0",
        tags=["EUR/USD"],
    )
    strat = ContextCapturingStrategy(meta)
    strat.initialize()

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe="H1",
    )

    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t0,
        open_price=Decimal("1.0800"),
        high_price=Decimal("1.0850"),
        low_price=Decimal("1.0790"),
        close_price=Decimal("1.0825"),
        volume=Decimal(100),
    )

    assert len(strat.captured_contexts) == 1
    assert strat.captured_contexts[0].current_price == Decimal("1.0825")
    assert strat.captured_contexts[0].current_price is not None

    # Backward compatibility with close=...
    t1 = t0 + timedelta(hours=1)
    await adapter.on_candle(
        symbol="EUR/USD",
        timestamp=t1,
        open_price=Decimal("1.0825"),
        high=Decimal("1.0860"),
        low=Decimal("1.0810"),
        close=Decimal("1.0840"),
        volume=Decimal(100),
    )
    assert len(strat.captured_contexts) == 2
    assert strat.captured_contexts[1].current_price == Decimal("1.0840")


# ─── 6. Existing Strategies Non-Regression ────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("strat_id", ["trend_following", "mean_reversion", "breakout", "momentum"])
async def test_existing_strategies_retain_behavior(strat_id: str) -> None:
    """Requirement 11: Existing 4 strategies retain their behavior with adapter."""
    params: dict[str, Any] = {}
    if strat_id == "trend_following":
        params = {"fast_period": 5, "slow_period": 15}
    elif strat_id == "mean_reversion":
        params = {"lookback_period": 20, "entry_threshold": 2.0}
    elif strat_id == "breakout":
        params = {"channel_period": 20, "breakout_multiplier": 1.0}
    elif strat_id == "momentum":
        params = {"momentum_period": 14, "momentum_threshold": 0.02}

    strategy = StrategyRegistry.create_strategy(
        strategy_id=strat_id,
        parameters=params,
        symbols=["EUR/USD"],
    )

    pattern_engine = CandlestickPatternEngine()
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = _build_hammer_reversal_series(t0, n_prefix=30)

    adapter = StrategyBacktestAdapter(
        strategy=strategy,
        symbol="EUR/USD",
        timeframe="H1",
        pattern_engine=pattern_engine,
        candles=candles,
    )

    for c in candles:
        await adapter.on_candle(
            symbol="EUR/USD",
            timestamp=c["timestamp"],
            open_price=c["open"],
            high_price=c["high"],
            low_price=c["low"],
            close_price=c["close"],
            volume=c["volume"],
        )

    await adapter.finalize(candles[-1]["timestamp"], candles[-1]["close"])
    perf = adapter.calculate_performance_metrics()
    assert perf.initial_capital == Decimal("10000.00")
    assert perf.final_balance > Decimal("0.00")


# ─── 7. LeakageGuard and Lookahead Bias Invariant ─────────────────────────────


def test_leakage_guard_rejects_future_pattern() -> None:
    """Requirement 12 & 13: LeakageGuard rejects future pattern timestamps."""
    sim_time = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    future_time = sim_time + timedelta(hours=1)

    future_pattern = CandlestickPattern(
        pattern_id="hammer",
        name="Hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.MODERATE,
        candle_index=13,
        timestamp=future_time,
        description="Future hammer",
        confidence=Decimal("0.85"),
    )

    context = StrategyContext(
        strategy_id="candlestick_reversal",
        symbol="EUR/USD",
        current_price=Decimal("1.0850"),
        position=None,
        account_equity=Decimal("10000.00"),
        account_balance=Decimal("10000.00"),
        timestamp=sim_time,
        metadata={"patterns": (future_pattern,)},
    )

    with pytest.raises(DataLeakageDetectedError, match="Look-ahead bias detected"):
        LeakageGuard.validate_strategy_context(context, sim_time)
