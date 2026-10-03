"""Unit test suite for CandlestickReversalStrategy.

Covers all 32 minimum required scenarios:
1. strategy_id
2. default parameters
3. bullish hammer -> BUY
4. bearish shooting star -> SELL
5. bullish engulfing -> BUY
6. bearish engulfing -> SELL
7. exact pattern_id filtering
8. any_reversal filtering
9. bullish_only filtering
10. bearish_only filtering
11. neutral pattern produces no signal
12. minimum strength "any"
13. minimum strength "moderate"
14. minimum strength "strong"
15. confidence threshold pass
16. confidence threshold fail
17. empty pattern context
18. missing pattern context
19. invalid stop direction LONG
20. invalid stop direction SHORT
21. stop distance below 5 pips
22. valid LONG stop-loss
23. valid SHORT stop-loss
24. multiple bullish patterns deterministic selection
25. bullish/bearish conflict returns None
26. required_candles tie-break
27. pattern_id alphabetical final tie-break
28. existing BaseStrategy lifecycle compatibility
29. strategy registry registration
30. parameter validation
31. optimization space registration
32. deterministic repeated evaluation
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from libraries.domain.market_data.models import OHLCV
from libraries.domain.patterns.models import (
    CandlestickPattern,
    PatternDirection,
    PatternStrength,
)
from libraries.domain.research.optimization_models import ParameterType
from libraries.domain.research.parameter_space_engine import ParameterSpaceEngine
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    ExecutionAction,
    PositionSide,
    SignalDirection,
    SignalStrength,
    StrategyContext,
    StrategyMetadata,
    StrategyStatus,
)
from libraries.domain.strategy.registry import (
    InvalidStrategyParameterError,
    StrategyRegistry,
)
from libraries.domain.strategy.strategies.candlestick_reversal import (
    CandlestickReversalStrategy,
    get_pip_size,
)

_NOW = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)


def _make_strategy(
    strategy_id: str = "candlestick_reversal",
    pattern_id: str = "any_reversal",
    pattern_direction: str = "all",
    min_strength: str = "moderate",
    min_confidence: float = 0.70,
    symbol: str = "EUR/USD",
) -> CandlestickReversalStrategy:
    metadata = StrategyMetadata(
        strategy_id=strategy_id,
        name="Candlestick Reversal",
        version="1.0.0",
        tags=[symbol],
    )
    strat = CandlestickReversalStrategy(
        metadata=metadata,
        pattern_id=pattern_id,
        pattern_direction=pattern_direction,
        min_strength=min_strength,
        min_confidence=min_confidence,
    )
    strat.initialize()
    return strat


def _make_pattern(
    pattern_id: str = "hammer",
    direction: PatternDirection = PatternDirection.BULLISH,
    strength: PatternStrength = PatternStrength.STRONG,
    confidence: Decimal | float | str = "0.80",
    timestamp: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> CandlestickPattern:
    return CandlestickPattern(
        pattern_id=pattern_id,
        name=pattern_id.replace("_", " ").title(),
        direction=direction,
        strength=strength,
        candle_index=1,
        timestamp=timestamp or _NOW,
        description=f"Test pattern {pattern_id}",
        confidence=Decimal(str(confidence)),
        metadata=metadata or {},
    )


def _make_context(
    patterns: tuple[CandlestickPattern, ...] | None = None,
    current_price: Decimal = Decimal("1.0850"),
    candle_high: Decimal = Decimal("1.0880"),
    candle_low: Decimal = Decimal("1.0820"),
    symbol: str = "EUR/USD",
    include_patterns_key: bool = True,
) -> StrategyContext:
    candle = OHLCV(
        symbol=symbol,
        timestamp=_NOW,
        open=Decimal("1.0830"),
        high=candle_high,
        low=candle_low,
        close=current_price,
        volume=Decimal("1000"),
    )
    metadata: dict[str, Any] = {
        "current_candle": candle,
        "historical_candles": [candle],
    }
    if include_patterns_key:
        metadata["patterns"] = patterns if patterns is not None else ()

    return StrategyContext(
        strategy_id="candlestick_reversal",
        symbol=symbol,
        current_price=current_price,
        timestamp=_NOW,
        metadata=metadata,
    )


# ─── 1. STRATEGY ID ─────────────────────────────────────────────────────────


def test_1_strategy_id():
    strat = _make_strategy()
    assert strat.strategy_id == "candlestick_reversal"


# ─── 2. DEFAULT PARAMETERS ──────────────────────────────────────────────────


def test_2_default_parameters():
    strat = _make_strategy()
    assert strat.pattern_id == "any_reversal"
    assert strat.pattern_direction == "all"
    assert strat.min_strength == "moderate"
    assert strat.min_confidence == 0.70
    assert strat.parameters["pattern_id"] == "any_reversal"
    assert strat.parameters["pattern_direction"] == "all"
    assert strat.parameters["min_strength"] == "moderate"
    assert strat.parameters["min_confidence"] == 0.70


# ─── 3. BULLISH HAMMER -> BUY ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_3_bullish_hammer_generates_buy():
    strat = _make_strategy(pattern_id="hammer")
    pat = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.85",
    )
    ctx = _make_context(patterns=(pat,), current_price=Decimal("1.0850"), candle_low=Decimal("1.0820"))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.direction == SignalDirection.BUY
    assert result.signal.price == Decimal("1.0850")
    assert result.signal.confidence == 0.85
    assert result.signal.strength == SignalStrength.STRONG
    assert result.signal.metadata["pattern_id"] == "hammer"
    assert result.signal.metadata["stop_loss"] == "1.0819"  # 1.0820 - 0.0001
    assert result.order_intent is not None
    assert result.order_intent.action == ExecutionAction.ENTER_LONG
    assert result.order_intent.stop_price == Decimal("1.0819")


# ─── 4. BEARISH SHOOTING STAR -> SELL ────────────────────────────────────────


@pytest.mark.asyncio
async def test_4_bearish_shooting_star_generates_sell():
    strat = _make_strategy(pattern_id="shooting_star")
    pat = _make_pattern(
        pattern_id="shooting_star",
        direction=PatternDirection.BEARISH,
        strength=PatternStrength.STRONG,
        confidence="0.85",
    )
    ctx = _make_context(patterns=(pat,), current_price=Decimal("1.0850"), candle_high=Decimal("1.0880"))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.direction == SignalDirection.SELL
    assert result.signal.price == Decimal("1.0850")
    assert result.signal.confidence == 0.85
    assert result.signal.metadata["pattern_id"] == "shooting_star"
    assert result.signal.metadata["stop_loss"] == "1.0881"  # 1.0880 + 0.0001
    assert result.order_intent is not None
    assert result.order_intent.action == ExecutionAction.ENTER_SHORT
    assert result.order_intent.stop_price == Decimal("1.0881")


# ─── 5. BULLISH ENGULFING -> BUY ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_5_bullish_engulfing_generates_buy():
    strat = _make_strategy(pattern_id="bullish_engulfing")
    pat = _make_pattern(
        pattern_id="bullish_engulfing",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.90",
    )
    ctx = _make_context(patterns=(pat,), current_price=Decimal("1.0850"), candle_low=Decimal("1.0820"))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.direction == SignalDirection.BUY
    assert result.signal.metadata["pattern_id"] == "bullish_engulfing"


# ─── 6. BEARISH ENGULFING -> SELL ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_6_bearish_engulfing_generates_sell():
    strat = _make_strategy(pattern_id="bearish_engulfing")
    pat = _make_pattern(
        pattern_id="bearish_engulfing",
        direction=PatternDirection.BEARISH,
        strength=PatternStrength.STRONG,
        confidence="0.90",
    )
    ctx = _make_context(patterns=(pat,), current_price=Decimal("1.0850"), candle_high=Decimal("1.0880"))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.direction == SignalDirection.SELL
    assert result.signal.metadata["pattern_id"] == "bearish_engulfing"


# ─── 7. EXACT PATTERN_ID FILTERING ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_7_exact_pattern_id_filtering():
    strat = _make_strategy(pattern_id="hammer")
    # Provide a bullish engulfing pattern instead of hammer
    pat = _make_pattern(pattern_id="bullish_engulfing", direction=PatternDirection.BULLISH)
    ctx = _make_context(patterns=(pat,))
    result = await strat.evaluate(ctx)

    assert result.signal is None


# ─── 8. ANY_REVERSAL FILTERING ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_8_any_reversal_filtering():
    strat = _make_strategy(pattern_id="any_reversal")
    # Morning star is tagged reversal -> must pass
    pat = _make_pattern(
        pattern_id="morning_star",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    ctx = _make_context(patterns=(pat,))
    result = await strat.evaluate(ctx)
    assert result.signal is not None
    assert result.signal.direction == SignalDirection.BUY

    # Three white soldiers is continuation -> must NOT pass
    pat_cont = _make_pattern(
        pattern_id="three_white_soldiers",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    ctx_cont = _make_context(patterns=(pat_cont,))
    result_cont = await strat.evaluate(ctx_cont)
    assert result_cont.signal is None


# ─── 9. BULLISH_ONLY FILTERING ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_9_bullish_only_filtering():
    strat = _make_strategy(pattern_direction="bullish_only")
    pat_bearish = _make_pattern(pattern_id="shooting_star", direction=PatternDirection.BEARISH)
    ctx = _make_context(patterns=(pat_bearish,))
    result = await strat.evaluate(ctx)
    assert result.signal is None

    pat_bullish = _make_pattern(pattern_id="hammer", direction=PatternDirection.BULLISH)
    ctx_bullish = _make_context(patterns=(pat_bullish,))
    result_bullish = await strat.evaluate(ctx_bullish)
    assert result_bullish.signal is not None
    assert result_bullish.signal.direction == SignalDirection.BUY


# ─── 10. BEARISH_ONLY FILTERING ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_10_bearish_only_filtering():
    strat = _make_strategy(pattern_direction="bearish_only")
    pat_bullish = _make_pattern(pattern_id="hammer", direction=PatternDirection.BULLISH)
    ctx = _make_context(patterns=(pat_bullish,))
    result = await strat.evaluate(ctx)
    assert result.signal is None

    pat_bearish = _make_pattern(pattern_id="shooting_star", direction=PatternDirection.BEARISH)
    ctx_bearish = _make_context(patterns=(pat_bearish,))
    result_bearish = await strat.evaluate(ctx_bearish)
    assert result_bearish.signal is not None
    assert result_bearish.signal.direction == SignalDirection.SELL


# ─── 11. NEUTRAL PATTERN PRODUCES NO SIGNAL ──────────────────────────────────


@pytest.mark.asyncio
async def test_11_neutral_pattern_produces_no_signal():
    strat = _make_strategy(pattern_id="any_reversal")
    # Doji has reversal tag but NEUTRAL direction -> must NEVER generate signal
    pat_doji = _make_pattern(
        pattern_id="doji",
        direction=PatternDirection.NEUTRAL,
        strength=PatternStrength.MODERATE,
        confidence="0.95",
    )
    ctx_doji = _make_context(patterns=(pat_doji,))
    result_doji = await strat.evaluate(ctx_doji)
    assert result_doji.signal is None

    # Inside bar is NEUTRAL consolidation -> must never generate signal
    pat_ib = _make_pattern(
        pattern_id="inside_bar",
        direction=PatternDirection.NEUTRAL,
        strength=PatternStrength.MODERATE,
        confidence="0.95",
    )
    ctx_ib = _make_context(patterns=(pat_ib,))
    result_ib = await strat.evaluate(ctx_ib)
    assert result_ib.signal is None


# ─── 12. MINIMUM STRENGTH "ANY" ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_12_minimum_strength_any():
    strat = _make_strategy(min_strength="any")
    pat_weak = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.WEAK,
        confidence="0.75",
    )
    ctx = _make_context(patterns=(pat_weak,))
    result = await strat.evaluate(ctx)
    assert result.signal is not None


# ─── 13. MINIMUM STRENGTH "MODERATE" ────────────────────────────────────────


@pytest.mark.asyncio
async def test_13_minimum_strength_moderate():
    strat = _make_strategy(min_strength="moderate")
    pat_weak = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.WEAK,
        confidence="0.75",
    )
    ctx_weak = _make_context(patterns=(pat_weak,))
    result_weak = await strat.evaluate(ctx_weak)
    assert result_weak.signal is None

    pat_mod = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.MODERATE,
        confidence="0.75",
    )
    ctx_mod = _make_context(patterns=(pat_mod,))
    result_mod = await strat.evaluate(ctx_mod)
    assert result_mod.signal is not None


# ─── 14. MINIMUM STRENGTH "STRONG" ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_14_minimum_strength_strong():
    strat = _make_strategy(min_strength="strong")
    pat_mod = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.MODERATE,
        confidence="0.75",
    )
    ctx_mod = _make_context(patterns=(pat_mod,))
    result_mod = await strat.evaluate(ctx_mod)
    assert result_mod.signal is None

    pat_strong = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.75",
    )
    ctx_strong = _make_context(patterns=(pat_strong,))
    result_strong = await strat.evaluate(ctx_strong)
    assert result_strong.signal is not None


# ─── 15. CONFIDENCE THRESHOLD PASS ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_15_confidence_threshold_pass():
    strat = _make_strategy(min_confidence=0.70)
    pat = _make_pattern(confidence="0.70")
    ctx = _make_context(patterns=(pat,))
    result = await strat.evaluate(ctx)
    assert result.signal is not None
    assert result.signal.confidence == 0.70


# ─── 16. CONFIDENCE THRESHOLD FAIL ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_16_confidence_threshold_fail():
    strat = _make_strategy(min_confidence=0.75)
    pat = _make_pattern(confidence="0.74")
    ctx = _make_context(patterns=(pat,))
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 17. EMPTY PATTERN CONTEXT ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_17_empty_pattern_context():
    strat = _make_strategy()
    ctx = _make_context(patterns=())
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 18. MISSING PATTERN CONTEXT ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_18_missing_pattern_context():
    strat = _make_strategy()
    ctx = _make_context(include_patterns_key=False)
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 19. INVALID STOP DIRECTION LONG ────────────────────────────────────────


@pytest.mark.asyncio
async def test_19_invalid_stop_direction_long():
    strat = _make_strategy()
    pat = _make_pattern(direction=PatternDirection.BULLISH)
    # For LONG: SL = low - 1 pip. If low is higher than current_price, SL >= current_price -> reject!
    ctx = _make_context(
        patterns=(pat,),
        current_price=Decimal("1.0800"),
        candle_low=Decimal("1.0820"),  # SL = 1.0819 >= 1.0800
    )
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 20. INVALID STOP DIRECTION SHORT ───────────────────────────────────────


@pytest.mark.asyncio
async def test_20_invalid_stop_direction_short():
    strat = _make_strategy()
    pat = _make_pattern(pattern_id="shooting_star", direction=PatternDirection.BEARISH)
    # For SHORT: SL = high + 1 pip. If high is lower than current_price, SL <= current_price -> reject!
    ctx = _make_context(
        patterns=(pat,),
        current_price=Decimal("1.0900"),
        candle_high=Decimal("1.0880"),  # SL = 1.0881 <= 1.0900
    )
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 21. STOP DISTANCE BELOW 5 PIPS ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_21_stop_distance_below_5_pips():
    strat = _make_strategy()
    pat = _make_pattern(direction=PatternDirection.BULLISH)
    # pip_size = 0.0001. 5 pips = 0.0005.
    # If current_price = 1.0850, candle_low = 1.0848:
    # SL = 1.0848 - 0.0001 = 1.0847.
    # stop_distance = 1.0850 - 1.0847 = 0.0003 (3 pips < 5 pips) -> reject!
    ctx = _make_context(
        patterns=(pat,),
        current_price=Decimal("1.0850"),
        candle_low=Decimal("1.0848"),
    )
    result = await strat.evaluate(ctx)
    assert result.signal is None


# ─── 22. VALID LONG STOP-LOSS ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_22_valid_long_stop_loss():
    strat = _make_strategy()
    pat = _make_pattern(direction=PatternDirection.BULLISH)
    # current_price = 1.0850, candle_low = 1.0820.
    # SL = 1.0820 - 0.0001 = 1.0819.
    # stop_distance = 0.0031 (31 pips >= 5 pips)
    ctx = _make_context(
        patterns=(pat,),
        current_price=Decimal("1.0850"),
        candle_low=Decimal("1.0820"),
    )
    result = await strat.evaluate(ctx)
    assert result.signal is not None
    assert result.signal.metadata["stop_loss"] == "1.0819"
    assert result.position_intent is not None
    assert result.position_intent.side == PositionSide.LONG
    assert result.position_intent.stop_loss == Decimal("1.0819")


# ─── 23. VALID SHORT STOP-LOSS ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_23_valid_short_stop_loss():
    strat = _make_strategy()
    pat = _make_pattern(pattern_id="shooting_star", direction=PatternDirection.BEARISH)
    # current_price = 1.0850, candle_high = 1.0880.
    # SL = 1.0880 + 0.0001 = 1.0881.
    # stop_distance = 0.0031 (31 pips >= 5 pips)
    ctx = _make_context(
        patterns=(pat,),
        current_price=Decimal("1.0850"),
        candle_high=Decimal("1.0880"),
    )
    result = await strat.evaluate(ctx)
    assert result.signal is not None
    assert result.signal.metadata["stop_loss"] == "1.0881"
    assert result.position_intent is not None
    assert result.position_intent.side == PositionSide.SHORT
    assert result.position_intent.stop_loss == Decimal("1.0881")


# ─── 24. MULTIPLE BULLISH PATTERNS DETERMINISTIC SELECTION ──────────────────


@pytest.mark.asyncio
async def test_24_multiple_bullish_patterns_deterministic_selection():
    strat = _make_strategy(pattern_id="any_reversal")
    # Two bullish patterns: hammer (conf=0.75), bullish_engulfing (conf=0.90)
    pat1 = _make_pattern(pattern_id="hammer", direction=PatternDirection.BULLISH, confidence="0.75")
    pat2 = _make_pattern(pattern_id="bullish_engulfing", direction=PatternDirection.BULLISH, confidence="0.90")
    ctx = _make_context(patterns=(pat1, pat2))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    # Higher confidence wins
    assert result.signal.metadata["pattern_id"] == "bullish_engulfing"


# ─── 25. BULLISH/BEARISH CONFLICT RETURNS NONE ──────────────────────────────


@pytest.mark.asyncio
async def test_25_bullish_bearish_conflict_returns_none():
    strat = _make_strategy(pattern_id="any_reversal")
    # Qualifying bullish hammer + qualifying bearish shooting star on same candle
    pat_bull = _make_pattern(pattern_id="hammer", direction=PatternDirection.BULLISH, confidence="0.85")
    pat_bear = _make_pattern(pattern_id="shooting_star", direction=PatternDirection.BEARISH, confidence="0.85")
    ctx = _make_context(patterns=(pat_bull, pat_bear))
    result = await strat.evaluate(ctx)

    assert result.signal is None


# ─── 26. REQUIRED_CANDLES TIE-BREAK ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_26_required_candles_tie_break():
    strat = _make_strategy(pattern_id="any_reversal")
    # Both same confidence (0.80) and strength (STRONG).
    # hammer has required_candles = 2.
    # morning_star has required_candles = 3.
    pat_hammer = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    pat_mstar = _make_pattern(
        pattern_id="morning_star",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    ctx = _make_context(patterns=(pat_hammer, pat_mstar))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.metadata["pattern_id"] == "morning_star"


# ─── 27. PATTERN_ID ALPHABETICAL FINAL TIE-BREAK ─────────────────────────────


@pytest.mark.asyncio
async def test_27_pattern_id_alphabetical_final_tie_break():
    strat = _make_strategy(pattern_id="any_reversal")
    # Both confidence=0.80, strength=STRONG, required_candles=2.
    # bullish_engulfing vs hammer.
    # Deterministic max by tuple puts "hammer" > "bullish_engulfing".
    pat_engulf = _make_pattern(
        pattern_id="bullish_engulfing",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    pat_hammer = _make_pattern(
        pattern_id="hammer",
        direction=PatternDirection.BULLISH,
        strength=PatternStrength.STRONG,
        confidence="0.80",
    )
    ctx = _make_context(patterns=(pat_engulf, pat_hammer))
    result = await strat.evaluate(ctx)

    assert result.signal is not None
    assert result.signal.metadata["pattern_id"] == "hammer"


# ─── 28. BASESTRATEGY LIFECYCLE COMPATIBILITY ───────────────────────────────


@pytest.mark.asyncio
async def test_28_base_strategy_lifecycle_compatibility():
    metadata = StrategyMetadata(
        strategy_id="candlestick_reversal",
        name="Candlestick Reversal",
        tags=["EUR/USD"],
    )
    strat = CandlestickReversalStrategy(metadata)
    assert strat.status == StrategyStatus.DRAFT

    strat.initialize()
    assert strat.status == StrategyStatus.ACTIVE

    strat.pause()
    assert strat.status == StrategyStatus.PAUSED
    ctx = _make_context(patterns=(_make_pattern(),))
    res_paused = await strat.evaluate(ctx)
    assert res_paused.signal is None
    assert "Strategy is paused" in res_paused.errors[0]

    strat.resume()
    assert strat.status == StrategyStatus.ACTIVE

    strat.stop()
    assert strat.status == StrategyStatus.STOPPED


# ─── 29. STRATEGY REGISTRY REGISTRATION ──────────────────────────────────────


def test_29_strategy_registry_registration():
    entry = StrategyRegistry.get("candlestick_reversal")
    assert entry.strategy_id == "candlestick_reversal"
    assert entry.name == "Candlestick Reversal"
    assert entry.category == "price_action"
    assert entry.version == "1.0.0"
    assert entry.is_deterministic is True

    param_names = {p.name for p in entry.parameters}
    assert param_names == {"pattern_id", "pattern_direction", "min_strength", "min_confidence"}

    instance = StrategyRegistry.create_strategy("candlestick_reversal")
    assert isinstance(instance, CandlestickReversalStrategy)
    assert instance.status == StrategyStatus.ACTIVE


# ─── 30. PARAMETER VALIDATION ───────────────────────────────────────────────


def test_30_parameter_validation():
    # Valid parameters pass
    validated = StrategyRegistry.validate_parameters(
        "candlestick_reversal",
        {
            "pattern_id": "hammer",
            "pattern_direction": "bullish_only",
            "min_strength": "strong",
            "min_confidence": 0.85,
        },
    )
    assert validated["pattern_id"] == "hammer"
    assert validated["pattern_direction"] == "bullish_only"
    assert validated["min_strength"] == "strong"
    assert validated["min_confidence"] == 0.85

    # Invalid pattern_id fails
    with pytest.raises(InvalidStrategyParameterError):
        StrategyRegistry.validate_parameters(
            "candlestick_reversal",
            {"pattern_id": "nonexistent_pattern"},
        )

    # Invalid direction fails
    with pytest.raises(InvalidStrategyParameterError):
        StrategyRegistry.validate_parameters(
            "candlestick_reversal",
            {"pattern_direction": "invalid_direction"},
        )

    # Invalid strength fails
    with pytest.raises(InvalidStrategyParameterError):
        StrategyRegistry.validate_parameters(
            "candlestick_reversal",
            {"min_strength": "ultra_strong"},
        )

    # Confidence out of bounds fails
    with pytest.raises(InvalidStrategyParameterError):
        StrategyRegistry.validate_parameters(
            "candlestick_reversal",
            {"min_confidence": 0.30},
        )
    with pytest.raises(InvalidStrategyParameterError):
        StrategyRegistry.validate_parameters(
            "candlestick_reversal",
            {"min_confidence": 1.20},
        )


# ─── 31. OPTIMIZATION SPACE REGISTRATION ────────────────────────────────────


def test_31_optimization_space_registration():
    space = ParameterSpaceEngine.get_default_space("candlestick_reversal")
    assert space.strategy_id == "candlestick_reversal"
    assert len(space.ranges) == 3

    range_map = {r.name: r for r in space.ranges}
    assert "pattern_id" in range_map
    assert range_map["pattern_id"].param_type == ParameterType.CHOICE
    assert len(range_map["pattern_id"].choices) == 7

    assert "min_confidence" in range_map
    assert range_map["min_confidence"].param_type == ParameterType.FLOAT

    assert "min_strength" in range_map
    assert range_map["min_strength"].param_type == ParameterType.CHOICE

    ParameterSpaceEngine.validate_space(space)
    combos = ParameterSpaceEngine.count_combinations(space)
    assert combos > 0


# ─── 32. DETERMINISTIC REPEATED EVALUATION ──────────────────────────────────


@pytest.mark.asyncio
async def test_32_deterministic_repeated_evaluation():
    strat = _make_strategy()
    pat = _make_pattern(pattern_id="hammer", direction=PatternDirection.BULLISH, confidence="0.82")
    ctx = _make_context(patterns=(pat,))

    result1 = await strat.evaluate(ctx)
    result2 = await strat.evaluate(ctx)

    assert result1.signal is not None
    assert result2.signal is not None
    assert result1.signal.direction == result2.signal.direction
    assert result1.signal.price == result2.signal.price
    assert result1.signal.confidence == result2.signal.confidence
    assert result1.signal.metadata == result2.signal.metadata
    assert result1.order_intent.action == result2.order_intent.action
    assert result1.order_intent.stop_price == result2.order_intent.stop_price
    assert result1.position_intent.stop_loss == result2.position_intent.stop_loss
