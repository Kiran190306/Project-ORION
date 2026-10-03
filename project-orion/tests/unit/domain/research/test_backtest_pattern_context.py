"""Unit tests for Candlestick Pattern Backtest Context Infrastructure.

Validates:
1. Pattern context disabled: pattern_engine=None
2. Pattern context enabled: correct patterns injected
3. Pattern timestamp matches current candle
4. No future patterns appear in context
5. No cross-symbol contamination
6. No cross-timeframe contamination
7. Multiple patterns on same candle are preserved
8. Pattern tuples are immutable
9. Empty pattern result works (returns empty tuple)
10. Deterministic repeated backtest
11. Existing strategy behavior unchanged when disabled
12. LeakageGuard remains enforced
13. Pattern precomputation happens once rather than once per replay bar
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from libraries.domain.backtesting.historical_data import MarketDataServiceHistoricalProvider
from libraries.domain.backtesting.leakage_guard import DataLeakageDetectedError, LeakageGuard
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.patterns.engine import CandlestickPatternEngine
from libraries.domain.patterns.models import CandlestickPattern, PatternDirection, PatternStrength
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import Signal, StrategyContext, StrategyMetadata
from libraries.domain.strategy.registry import StrategyRegistry


class ContextCapturingStrategy(BaseStrategy):
    """Captures StrategyContext during evaluation for test assertions."""

    def __init__(self, metadata: StrategyMetadata, **kwargs: object) -> None:
        super().__init__(metadata, kwargs)
        self.captured_contexts: list[StrategyContext] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        self.captured_contexts.append(context)
        return None


def _make_strategy(symbol: str = "EUR/USD") -> ContextCapturingStrategy:
    metadata = StrategyMetadata(
        strategy_id="test_capturing_strategy",
        name="Test Capturing Strategy",
        version="1.0.0",
        tags=[symbol],
    )
    strat = ContextCapturingStrategy(metadata)
    strat.initialize()
    return strat


def _make_synthetic_candles(
    count: int = 10,
    base_time: datetime | None = None,
    symbol: str = "EUR/USD",
    timeframe: str = "H1",
) -> list[dict[str, Any]]:
    """Build a deterministic series of candles with controlled patterns."""
    t0 = base_time or datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles: list[dict[str, Any]] = []

    for i in range(count):
        t = t0 + timedelta(hours=i)
        if i == 3:
            # Doji: open == close, tiny body
            candles.append({
                "timestamp": t,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": Decimal("1.08500"),
                "high": Decimal("1.08700"),
                "low": Decimal("1.08300"),
                "close": Decimal("1.08500"),
                "volume": Decimal("1000"),
            })
        elif i == 4:
            # Bearish preceding bar for hammer reversal setup
            candles.append({
                "timestamp": t,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": Decimal("1.08600"),
                "high": Decimal("1.08700"),
                "low": Decimal("1.08150"),
                "close": Decimal("1.08200"),
                "volume": Decimal("1000"),
            })
        elif i == 5:
            # Hammer: small body near top, long lower shadow (>= 2x body)
            candles.append({
                "timestamp": t,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": Decimal("1.08500"),
                "high": Decimal("1.08520"),
                "low": Decimal("1.08100"),
                "close": Decimal("1.08510"),
                "volume": Decimal("1000"),
            })
        else:
            # Standard bullish/neutral bar
            candles.append({
                "timestamp": t,
                "symbol": symbol,
                "timeframe": timeframe,
                "open": Decimal("1.08000") + Decimal(str(i * 0.0005)),
                "high": Decimal("1.08200") + Decimal(str(i * 0.0005)),
                "low": Decimal("1.07900") + Decimal(str(i * 0.0005)),
                "close": Decimal("1.08150") + Decimal(str(i * 0.0005)),
                "volume": Decimal("1000"),
            })

    return candles


# ─── 1. Pattern Context Disabled (pattern_engine=None) ─────────────────────────


@pytest.mark.asyncio
async def test_pattern_context_disabled_by_default() -> None:
    """When pattern_engine is None, no patterns are computed and context metadata omits 'patterns'."""
    strat = _make_strategy()
    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=None,
    )
    candles = _make_synthetic_candles(count=5)

    assert adapter.pattern_engine is None
    assert adapter.pattern_map == {}

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

    assert len(strat.captured_contexts) == 5
    for ctx in strat.captured_contexts:
        assert "patterns" not in ctx.metadata


# ─── 2. Pattern Context Enabled (Patterns Injected) ───────────────────────────


@pytest.mark.asyncio
async def test_pattern_context_enabled_injects_correct_patterns() -> None:
    """When pattern_engine is provided, recognized patterns are injected into context.metadata['patterns']."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()
    candles = _make_synthetic_candles(count=10)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
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

    assert len(strat.captured_contexts) == 10

    # Candle 3 was designed as a Doji
    doji_ctx = strat.captured_contexts[3]
    assert "patterns" in doji_ctx.metadata
    doji_patterns = doji_ctx.metadata["patterns"]
    assert len(doji_patterns) > 0
    pattern_ids = [p.pattern_id for p in doji_patterns]
    assert "doji" in pattern_ids

    # Candle 5 was designed as a Hammer
    hammer_ctx = strat.captured_contexts[5]
    assert "patterns" in hammer_ctx.metadata
    hammer_patterns = hammer_ctx.metadata["patterns"]
    assert len(hammer_patterns) > 0
    assert any(p.pattern_id == "hammer" for p in hammer_patterns)


# ─── 3. Pattern Timestamp Matches Current Candle ───────────────────────────────


@pytest.mark.asyncio
async def test_pattern_timestamp_matches_current_candle() -> None:
    """All patterns in context.metadata['patterns'] must strictly match the current candle timestamp."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()
    candles = _make_synthetic_candles(count=8)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
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

    for ctx in strat.captured_contexts:
        patterns = ctx.metadata.get("patterns", ())
        for p in patterns:
            # Pattern timestamp must match current simulation time exactly
            assert p.timestamp == ctx.timestamp


# ─── 4. No Future Patterns Appear in Context ───────────────────────────────────


@pytest.mark.asyncio
async def test_no_future_patterns_in_context() -> None:
    """At bar N, no pattern from bar N+1 or later must appear in context."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()
    candles = _make_synthetic_candles(count=10)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
        candles=candles,
    )

    for i, c in enumerate(candles):
        await adapter.on_candle(
            symbol="EUR/USD",
            timestamp=c["timestamp"],
            open_price=c["open"],
            high_price=c["high"],
            low_price=c["low"],
            close_price=c["close"],
            volume=c["volume"],
        )

        current_ctx = strat.captured_contexts[-1]
        patterns = current_ctx.metadata.get("patterns", ())

        # Ensure no pattern has index > i
        for p in patterns:
            assert p.candle_index <= i
            assert p.timestamp <= c["timestamp"]


# ─── 5. No Cross-Symbol Contamination ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_cross_symbol_contamination() -> None:
    """An adapter configured for EUR/USD must ignore GBP/USD candles and isolate state."""
    strat = _make_strategy("EUR/USD")
    engine = CandlestickPatternEngine()

    eur_candles = _make_synthetic_candles(count=5, symbol="EUR/USD")
    gbp_candles = _make_synthetic_candles(count=5, symbol="GBP/USD")
    mixed_candles = eur_candles + gbp_candles

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
        candles=mixed_candles,  # Passed mixed candles
    )

    # All precomputed patterns must belong strictly to EUR/USD
    for ts, plist in adapter.pattern_map.items():
        for p in plist:
            assert p.metadata.get("symbol") == "EUR/USD"


# ─── 6. No Cross-Timeframe Contamination ──────────────────────────────────────


@pytest.mark.asyncio
async def test_no_cross_timeframe_contamination() -> None:
    """An adapter configured for H1 must ignore M15 candles and maintain separate state."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()

    h1_candles = _make_synthetic_candles(count=5, timeframe="H1")
    m15_candles = _make_synthetic_candles(count=5, timeframe="M15")
    mixed_candles = h1_candles + m15_candles

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        timeframe="H1",
        pattern_engine=engine,
        candles=mixed_candles,
    )

    for ts, plist in adapter.pattern_map.items():
        for p in plist:
            assert p.metadata.get("timeframe") == "H1"


# ─── 7. Multiple Patterns on Same Candle Preserved ────────────────────────────


@pytest.mark.asyncio
async def test_multiple_patterns_on_same_candle_preserved() -> None:
    """When a candle matches multiple patterns, all patterns are preserved in the tuple."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()

    # Construct candles where a bar triggers inside_bar and doji simultaneously
    # Bar 0: Wide bar
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=1)
    candles = [
        {
            "timestamp": t0,
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "open": Decimal("1.08000"),
            "high": Decimal("1.09000"),
            "low": Decimal("1.07000"),
            "close": Decimal("1.08500"),
            "volume": Decimal("1000"),
        },
        {
            "timestamp": t1,
            "symbol": "EUR/USD",
            "timeframe": "H1",
            "open": Decimal("1.08200"),
            "high": Decimal("1.08400"),  # high < 1.09000 (inside)
            "low": Decimal("1.08000"),   # low > 1.07000 (inside)
            "close": Decimal("1.08200"), # open == close (doji)
            "volume": Decimal("1000"),
        },
    ]

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
        candles=candles,
    )

    for c in candles:
        await adapter.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])

    second_ctx = strat.captured_contexts[1]
    patterns = second_ctx.metadata.get("patterns", ())
    # Should detect both Inside Bar and Doji
    pattern_ids = {p.pattern_id for p in patterns}
    assert "doji" in pattern_ids
    assert "inside_bar" in pattern_ids
    assert len(patterns) >= 2


# ─── 8. Pattern Tuples are Immutable ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_pattern_tuples_are_immutable() -> None:
    """Pattern list in context.metadata['patterns'] must be an immutable tuple."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()
    candles = _make_synthetic_candles(count=4)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
        candles=candles,
    )

    for c in candles:
        await adapter.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])

    for ctx in strat.captured_contexts:
        patterns = ctx.metadata["patterns"]
        assert isinstance(patterns, tuple)
        # Attempting modification raises AttributeError
        with pytest.raises(AttributeError):
            patterns.append(None)  # type: ignore[attr-defined]


# ─── 9. Empty Pattern Result Works ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_pattern_result_returns_empty_tuple() -> None:
    """When a candle has no pattern detected, context.metadata['patterns'] is empty tuple ()."""
    strat = _make_strategy()
    engine = CandlestickPatternEngine()
    # Candle 0 is a standard bar with no prior history -> 0 patterns
    candles = _make_synthetic_candles(count=2)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=engine,
        candles=candles,
    )

    for c in candles:
        await adapter.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])

    ctx0 = strat.captured_contexts[0]
    assert "patterns" in ctx0.metadata
    assert ctx0.metadata["patterns"] == ()


# ─── 10. Deterministic Repeated Backtest ──────────────────────────────────────


@pytest.mark.asyncio
async def test_deterministic_repeated_backtest() -> None:
    """Running identical backtests twice produces 100% identical pattern maps and contexts."""
    engine = CandlestickPatternEngine()
    candles = _make_synthetic_candles(count=6)

    # Run 1
    strat1 = _make_strategy()
    adapter1 = StrategyBacktestAdapter(strategy=strat1, symbol="EUR/USD", pattern_engine=engine, candles=candles)
    for c in candles:
        await adapter1.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])

    # Run 2
    strat2 = _make_strategy()
    adapter2 = StrategyBacktestAdapter(strategy=strat2, symbol="EUR/USD", pattern_engine=engine, candles=candles)
    for c in candles:
        await adapter2.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])

    assert adapter1.pattern_map.keys() == adapter2.pattern_map.keys()
    for ts in adapter1.pattern_map:
        p1 = adapter1.pattern_map[ts]
        p2 = adapter2.pattern_map[ts]
        assert len(p1) == len(p2)
        for pat1, pat2 in zip(p1, p2):
            assert pat1.pattern_id == pat2.pattern_id
            assert pat1.confidence == pat2.confidence


# ─── 11. Existing Strategy Behavior Unchanged When Disabled ───────────────────


@pytest.mark.asyncio
async def test_existing_strategy_behavior_unchanged_when_disabled() -> None:
    """A registered strategy (trend_following) produces identical trades and metrics with pattern_engine=None."""
    provider = MarketDataServiceHistoricalProvider()
    candles = await provider.load_candles("EUR/USD", Timeframe.H1, date(2025, 1, 1), date(2025, 1, 10))

    # Baseline run
    strat_base = StrategyRegistry.create_strategy("trend_following", {"fast_period": 5, "slow_period": 15}, ["EUR/USD"])
    adapter_base = StrategyBacktestAdapter(strategy=strat_base, symbol="EUR/USD")
    for c in candles:
        await adapter_base.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])
    await adapter_base.finalize(candles[-1]["timestamp"], candles[-1]["close"])
    m_base = adapter_base.calculate_performance_metrics()

    # Explicit pattern_engine=None run
    strat_none = StrategyRegistry.create_strategy("trend_following", {"fast_period": 5, "slow_period": 15}, ["EUR/USD"])
    adapter_none = StrategyBacktestAdapter(strategy=strat_none, symbol="EUR/USD", pattern_engine=None)
    for c in candles:
        await adapter_none.on_candle("EUR/USD", c["timestamp"], c["open"], c["high"], c["low"], c["close"], c["volume"])
    await adapter_none.finalize(candles[-1]["timestamp"], candles[-1]["close"])
    m_none = adapter_none.calculate_performance_metrics()

    assert m_base.final_balance == m_none.final_balance
    assert m_base.net_profit == m_none.net_profit
    assert m_base.total_trades == m_none.total_trades
    assert m_base.sharpe_ratio == m_none.sharpe_ratio
    assert m_base.max_drawdown_pct == m_none.max_drawdown_pct


# ─── 12. LeakageGuard Remains Enforced ────────────────────────────────────────


@pytest.mark.asyncio
async def test_leakage_guard_rejects_future_patterns() -> None:
    """LeakageGuard raises DataLeakageDetectedError if a pattern timestamp exceeds current simulation time."""
    now = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    future = now + timedelta(hours=1)

    future_pattern = CandlestickPattern(
        pattern_id="hammer",
        name="Hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        candle_index=5,
        timestamp=future,  # In the future!
        description="Leaked future pattern",
    )

    leaked_context = StrategyContext(
        strategy_id="test_strat",
        symbol="EUR/USD",
        current_price=Decimal("1.08500"),
        timestamp=now,
        metadata={"patterns": (future_pattern,)},
    )

    with pytest.raises(DataLeakageDetectedError) as exc_info:
        LeakageGuard.validate_strategy_context(leaked_context, now)

    assert "Look-ahead bias detected" in str(exc_info.value)
    assert "hammer" in str(exc_info.value)


# ─── 13. Pattern Precomputation Happens Once (Not Per Bar) ────────────────────


@pytest.mark.asyncio
async def test_pattern_precomputation_happens_once_not_per_bar() -> None:
    """Precomputation is called exactly once per backtest, NOT once per replay bar."""
    strat = _make_strategy()
    real_engine = CandlestickPatternEngine()
    mock_engine = MagicMock(wraps=real_engine)

    candles = _make_synthetic_candles(count=20)

    adapter = StrategyBacktestAdapter(
        strategy=strat,
        symbol="EUR/USD",
        pattern_engine=mock_engine,
        candles=candles,
    )

    # Replay 20 bars
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

    # detect_patterns must have been called EXACTLY ONCE
    assert mock_engine.detect_patterns.call_count == 1
