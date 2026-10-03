"""Comprehensive unit tests for the Candlestick Pattern Recognition Engine.

Tests every pattern, zero-range safety, decimal precision, immutability,
chronological ordering, registry cataloging, and strict look-ahead prevention.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.indicators.models import Bar
from libraries.domain.market_data.models import OHLCV, BarType
from libraries.domain.patterns import (
    CandlestickPatternEngine,
    PatternDefinition,
    PatternDirection,
    PatternStrength,
    detect_patterns,
    detect_patterns_at,
    get_default_pattern_registry,
)


def _dt(minute: int) -> datetime:
    return datetime(2026, 9, 26, 12, minute, tzinfo=timezone.utc)


def _ohlcv(
    open_: str, high: str, low: str, close: str, minute: int = 0, volume: str = "1000"
) -> OHLCV:
    return OHLCV(
        symbol="EUR/USD",
        timestamp=_dt(minute),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
        bar_type=BarType.M15,
    )


# ─── 1. REGISTRY & CATALOG TESTS ─────────────────────────────────────────────


def test_pattern_registry_catalog() -> None:
    registry = get_default_pattern_registry()
    assert len(registry) == 14

    pattern_ids = registry.list_pattern_ids()
    expected_ids = {
        "doji",
        "hammer",
        "inverted_hammer",
        "shooting_star",
        "hanging_man",
        "bullish_engulfing",
        "bearish_engulfing",
        "bullish_harami",
        "bearish_harami",
        "inside_bar",
        "morning_star",
        "evening_star",
        "three_white_soldiers",
        "three_black_crows",
    }
    assert set(pattern_ids) == expected_ids

    bullish_patterns = registry.filter_by_direction(PatternDirection.BULLISH)
    assert len(bullish_patterns) == 6  # hammer, inv_hammer, bull_engulf, bull_harami, morning_star, 3_soldiers

    bearish_patterns = registry.filter_by_direction(PatternDirection.BEARISH)
    assert len(bearish_patterns) == 6  # shooting_star, hanging_man, bear_engulf, bear_harami, evening_star, 3_crows

    neutral_patterns = registry.filter_by_direction(PatternDirection.NEUTRAL)
    assert len(neutral_patterns) == 2  # doji, inside_bar

    # Verify metadata fields
    for p in registry.list_definitions():
        assert p.required_candles in (1, 2, 3)
        assert len(p.name) > 0
        assert len(p.description) > 0


# ─── 2. ROBUSTNESS & EDGE CASE TESTS ─────────────────────────────────────────


def test_zero_range_candle_safety() -> None:
    """Zero-range candle (H == L) must not cause ZeroDivisionError."""
    flat_candle = _ohlcv("1.0850", "1.0850", "1.0850", "1.0850", minute=0)
    engine = CandlestickPatternEngine()

    patterns = engine.detect_patterns([flat_candle])
    assert patterns == []

    # Sequence of flat candles
    patterns = engine.detect_patterns([flat_candle, flat_candle, flat_candle])
    assert patterns == []


def test_insufficient_history() -> None:
    """Empty or short candle sequences must return empty list without exceptions."""
    engine = CandlestickPatternEngine()
    assert engine.detect_patterns([]) == []
    assert engine.detect_patterns_at([], 0) == []
    assert engine.detect_patterns_at([_ohlcv("1.0850", "1.0860", "1.0840", "1.0855")], -1) == []
    assert engine.detect_patterns_at([_ohlcv("1.0850", "1.0860", "1.0840", "1.0855")], 5) == []


def test_input_immutability() -> None:
    """Original input candle objects must never be modified by the engine."""
    c1 = _ohlcv("1.0850", "1.0870", "1.0840", "1.0865", minute=0)
    c2 = _ohlcv("1.0865", "1.0890", "1.0860", "1.0880", minute=1)
    candles = [c1, c2]

    c1_open_before = c1.open
    c2_close_before = c2.close

    detect_patterns(candles)

    assert c1.open == c1_open_before
    assert c2.close == c2_close_before


def test_heterogeneous_candle_types() -> None:
    """Engine must accept OHLCV, Bar, and raw dict instances seamlessly."""
    # Dict
    d = {
        "timestamp": "2026-09-26T12:00:00Z",
        "open": "1.0850",
        "high": "1.0860",
        "low": "1.0840",
        "close": "1.08505",  # Doji
        "volume": "100",
    }
    # Bar (float)
    b = Bar(
        timestamp=_dt(1),
        open=1.0850,
        high=1.0860,
        low=1.0840,
        close=1.08505,
        volume=100.0,
    )
    # OHLCV (Decimal)
    o = _ohlcv("1.0850", "1.0860", "1.0840", "1.08505", minute=2)

    for item in [d, b, o]:
        res = detect_patterns([item], pattern_ids=["doji"])
        assert len(res) == 1
        assert res[0].pattern_id == "doji"


# ─── 3. SINGLE-CANDLE PATTERN TESTS ──────────────────────────────────────────


def test_doji_detection() -> None:
    # Range = 0.0020, Body = 0.0001 (5% of range), Upper = 0.0009, Lower = 0.0010
    valid_doji = _ohlcv("1.0850", "1.0860", "1.0840", "1.0851", minute=0)
    res = detect_patterns([valid_doji], pattern_ids=["doji"])
    assert len(res) == 1
    assert res[0].pattern_id == "doji"
    assert res[0].direction == PatternDirection.NEUTRAL

    # Large body: not a doji (body = 0.0015 / range = 0.0020 = 75%)
    large_body = _ohlcv("1.0845", "1.0860", "1.0840", "1.0860", minute=0)
    assert detect_patterns([large_body], pattern_ids=["doji"]) == []


def test_hammer_detection() -> None:
    # Downtrend context: C0 is bear
    c_prev = _ohlcv("1.0870", "1.0875", "1.0850", "1.0852", minute=0)
    # Hammer: Open 1.0855, High 1.0858, Low 1.0830, Close 1.0857
    # Range = 0.0028, Body = 0.0002, Lower Shadow = 0.0025 (12.5x body!), Upper Shadow = 0.0001 (3.5% range)
    c_hammer = _ohlcv("1.0855", "1.0858", "1.0830", "1.0857", minute=1)

    res = detect_patterns([c_prev, c_hammer], pattern_ids=["hammer"])
    assert len(res) == 1
    assert res[0].pattern_id == "hammer"
    assert res[0].direction == PatternDirection.BULLISH

    # Negative case: upper shadow too long (0.0010 vs range 0.0028 = 35% > 15%)
    c_invalid = _ohlcv("1.0855", "1.0867", "1.0830", "1.0857", minute=1)
    assert detect_patterns([c_prev, c_invalid], pattern_ids=["hammer"]) == []


def test_inverted_hammer_detection() -> None:
    c_prev = _ohlcv("1.0880", "1.0885", "1.0860", "1.0862", minute=0)
    # Inverted Hammer: Open 1.0850, Close 1.0852 (body 0.0002), High 1.0875 (upper shadow 0.0023 = 11.5x body), Low 1.0849 (lower shadow 0.0001)
    c_inv = _ohlcv("1.0850", "1.0875", "1.0849", "1.0852", minute=1)

    res = detect_patterns([c_prev, c_inv], pattern_ids=["inverted_hammer"])
    assert len(res) == 1
    assert res[0].pattern_id == "inverted_hammer"
    assert res[0].direction == PatternDirection.BULLISH


def test_shooting_star_detection() -> None:
    # Uptrend context: C_prev is bull
    c_prev = _ohlcv("1.0840", "1.0865", "1.0835", "1.0862", minute=0)
    # Shooting Star: Open 1.0865, High 1.0890, Low 1.0863, Close 1.0866 (body 0.0001, upper shadow 0.0024 = 24x body)
    c_star = _ohlcv("1.0865", "1.0890", "1.0863", "1.0866", minute=1)

    res = detect_patterns([c_prev, c_star], pattern_ids=["shooting_star"])
    assert len(res) == 1
    assert res[0].pattern_id == "shooting_star"
    assert res[0].direction == PatternDirection.BEARISH

    # Negative case: occurred after bearish candle (not a shooting star)
    c_bear_prev = _ohlcv("1.0880", "1.0885", "1.0850", "1.0852", minute=0)
    assert detect_patterns([c_bear_prev, c_star], pattern_ids=["shooting_star"]) == []


def test_hanging_man_detection() -> None:
    # Uptrend context: C_prev is bull
    c_prev = _ohlcv("1.0830", "1.0860", "1.0825", "1.0858", minute=0)
    # Hanging man at top: small body near top, long lower shadow
    c_man = _ohlcv("1.0860", "1.0862", "1.0835", "1.0858", minute=1)

    res = detect_patterns([c_prev, c_man], pattern_ids=["hanging_man"])
    assert len(res) == 1
    assert res[0].pattern_id == "hanging_man"
    assert res[0].direction == PatternDirection.BEARISH


# ─── 4. TWO-CANDLE PATTERN TESTS ─────────────────────────────────────────────


def test_bullish_engulfing_detection() -> None:
    c_bear = _ohlcv("1.0860", "1.0865", "1.0845", "1.0850", minute=0)  # Body = 0.0010
    c_bull = _ohlcv("1.0848", "1.0875", "1.0845", "1.0870", minute=1)  # Body = 0.0022 (engulfs 1.0850-1.0860)

    res = detect_patterns([c_bear, c_bull], pattern_ids=["bullish_engulfing"])
    assert len(res) == 1
    assert res[0].pattern_id == "bullish_engulfing"
    assert res[0].direction == PatternDirection.BULLISH

    # Negative: Bull doesn't engulf bear body
    c_small_bull = _ohlcv("1.0848", "1.0858", "1.0845", "1.0855", minute=1)
    assert detect_patterns([c_bear, c_small_bull], pattern_ids=["bullish_engulfing"]) == []


def test_bearish_engulfing_detection() -> None:
    c_bull = _ohlcv("1.0840", "1.0855", "1.0835", "1.0850", minute=0)  # Body = 0.0010
    c_bear = _ohlcv("1.0852", "1.0855", "1.0825", "1.0830", minute=1)  # Body = 0.0022 (engulfs 1.0840-1.0850)

    res = detect_patterns([c_bull, c_bear], pattern_ids=["bearish_engulfing"])
    assert len(res) == 1
    assert res[0].pattern_id == "bearish_engulfing"
    assert res[0].direction == PatternDirection.BEARISH


def test_bullish_harami_detection() -> None:
    c_bear = _ohlcv("1.0870", "1.0875", "1.0840", "1.0845", minute=0)  # Body 1.0845 to 1.0870
    c_bull = _ohlcv("1.0850", "1.0865", "1.0848", "1.0860", minute=1)  # Body 1.0850 to 1.0860 (strictly inside)

    res = detect_patterns([c_bear, c_bull], pattern_ids=["bullish_harami"])
    assert len(res) == 1
    assert res[0].pattern_id == "bullish_harami"
    assert res[0].direction == PatternDirection.BULLISH


def test_bearish_harami_detection() -> None:
    c_bull = _ohlcv("1.0840", "1.0875", "1.0835", "1.0870", minute=0)  # Body 1.0840 to 1.0870
    c_bear = _ohlcv("1.0865", "1.0868", "1.0848", "1.0850", minute=1)  # Body 1.0850 to 1.0865 (strictly inside)

    res = detect_patterns([c_bull, c_bear], pattern_ids=["bearish_harami"])
    assert len(res) == 1
    assert res[0].pattern_id == "bearish_harami"
    assert res[0].direction == PatternDirection.BEARISH


def test_inside_bar_detection() -> None:
    # Mother bar: High 1.0880, Low 1.0840 (range 0.0040)
    c_mother = _ohlcv("1.0850", "1.0880", "1.0840", "1.0870", minute=0)
    # Inside bar: High 1.0870, Low 1.0850 (range 0.0020, completely inside mother bar range)
    c_inside = _ohlcv("1.0860", "1.0870", "1.0850", "1.0855", minute=1)

    res = detect_patterns([c_mother, c_inside], pattern_ids=["inside_bar"])
    assert len(res) == 1
    assert res[0].pattern_id == "inside_bar"
    assert res[0].direction == PatternDirection.NEUTRAL

    # Negative case: breaks mother bar high
    c_break = _ohlcv("1.0860", "1.0885", "1.0850", "1.0855", minute=1)
    assert detect_patterns([c_mother, c_break], pattern_ids=["inside_bar"]) == []


# ─── 5. THREE-CANDLE PATTERN TESTS ───────────────────────────────────────────


def test_morning_star_detection() -> None:
    # Candle 1: Strong bearish bar (Open 1.0880, Close 1.0840, midpoint = 1.0860)
    c1 = _ohlcv("1.0880", "1.0885", "1.0838", "1.0840", minute=0)
    # Candle 2: Small star bar (Open 1.0835, Close 1.0838, body 0.0003 <= 0.35 * 0.0040)
    c2 = _ohlcv("1.0835", "1.0840", "1.0830", "1.0838", minute=1)
    # Candle 3: Strong bullish bar (Open 1.0838, Close 1.0865 >= midpoint 1.0860)
    c3 = _ohlcv("1.0838", "1.0870", "1.0835", "1.0865", minute=2)

    res = detect_patterns([c1, c2, c3], pattern_ids=["morning_star"])
    assert len(res) == 1
    assert res[0].pattern_id == "morning_star"
    assert res[0].direction == PatternDirection.BULLISH

    # Negative: Candle 3 closes below midpoint (e.g. 1.0850 < 1.0860)
    c3_weak = _ohlcv("1.0838", "1.0852", "1.0835", "1.0850", minute=2)
    assert detect_patterns([c1, c2, c3_weak], pattern_ids=["morning_star"]) == []


def test_evening_star_detection() -> None:
    # Candle 1: Strong bullish bar (Open 1.0840, Close 1.0880, midpoint = 1.0860)
    c1 = _ohlcv("1.0840", "1.0882", "1.0838", "1.0880", minute=0)
    # Candle 2: Small star bar (Open 1.0885, Close 1.0883, body 0.0002)
    c2 = _ohlcv("1.0885", "1.0890", "1.0880", "1.0883", minute=1)
    # Candle 3: Strong bearish bar (Open 1.0880, Close 1.0855 <= midpoint 1.0860)
    c3 = _ohlcv("1.0880", "1.0882", "1.0850", "1.0855", minute=2)

    res = detect_patterns([c1, c2, c3], pattern_ids=["evening_star"])
    assert len(res) == 1
    assert res[0].pattern_id == "evening_star"
    assert res[0].direction == PatternDirection.BEARISH


def test_three_white_soldiers_detection() -> None:
    c1 = _ohlcv("1.0820", "1.0842", "1.0818", "1.0840", minute=0)  # Range 24, Body 20, Upper 2 (8%)
    c2 = _ohlcv("1.0835", "1.0862", "1.0832", "1.0860", minute=1)  # Range 30, Body 25, Upper 2 (6%)
    c3 = _ohlcv("1.0855", "1.0882", "1.0850", "1.0880", minute=2)  # Range 32, Body 25, Upper 2 (6%)

    res = detect_patterns([c1, c2, c3], pattern_ids=["three_white_soldiers"])
    assert len(res) == 1
    assert res[0].pattern_id == "three_white_soldiers"
    assert res[0].direction == PatternDirection.BULLISH

    # Negative case: Middle bar is bearish
    c2_bear = _ohlcv("1.0860", "1.0862", "1.0832", "1.0835", minute=1)
    assert detect_patterns([c1, c2_bear, c3], pattern_ids=["three_white_soldiers"]) == []


def test_three_black_crows_detection() -> None:
    c1 = _ohlcv("1.0880", "1.0882", "1.0858", "1.0860", minute=0)  # Range 24, Body 20, Lower 2
    c2 = _ohlcv("1.0865", "1.0868", "1.0838", "1.0840", minute=1)  # Range 30, Body 25, Lower 2
    c3 = _ohlcv("1.0845", "1.0850", "1.0818", "1.0820", minute=2)  # Range 32, Body 25, Lower 2

    res = detect_patterns([c1, c2, c3], pattern_ids=["three_black_crows"])
    assert len(res) == 1
    assert res[0].pattern_id == "three_black_crows"
    assert res[0].direction == PatternDirection.BEARISH


# ─── 6. CAUSALITY, DETERMINISM & ZERO-LOOKAHEAD VERIFICATION ─────────────────


def test_chronological_ordering() -> None:
    """Detection results across a sequence must be strictly ordered by candle_index."""
    candles = [
        _ohlcv("1.0850", "1.0860", "1.0840", "1.0851", minute=0),  # Doji at 0
        _ohlcv("1.0850", "1.0880", "1.0840", "1.0870", minute=1),  # Mother bar
        _ohlcv("1.0860", "1.0870", "1.0850", "1.0855", minute=2),  # Inside bar at 2
        _ohlcv("1.0850", "1.0860", "1.0840", "1.0851", minute=3),  # Doji at 3
    ]
    patterns = detect_patterns(candles)
    assert len(patterns) >= 3
    indices = [p.candle_index for p in patterns]
    assert indices == sorted(indices)


def test_zero_lookahead_bias() -> None:
    """A pattern detected at index N must never change whether future candles exist or not."""
    history = [
        _ohlcv("1.0870", "1.0875", "1.0840", "1.0845", minute=0),
        _ohlcv("1.0850", "1.0865", "1.0848", "1.0860", minute=1),  # Bullish Harami at index 1
    ]
    future = [
        _ohlcv("1.0860", "1.0890", "1.0855", "1.0885", minute=2),
        _ohlcv("1.0885", "1.0910", "1.0880", "1.0905", minute=3),
    ]

    # Evaluation on history alone
    history_patterns = detect_patterns(history)
    harami_history = [p for p in history_patterns if p.pattern_id == "bullish_harami"]
    assert len(harami_history) == 1

    # Evaluation on extended history (history + future)
    full_patterns = detect_patterns(history + future)
    harami_full = [p for p in full_patterns if p.pattern_id == "bullish_harami" and p.candle_index == 1]
    assert len(harami_full) == 1

    # Pattern properties must be 100% identical
    assert harami_history[0] == harami_full[0]

    # detect_patterns_at on index 1 must match
    at_history = detect_patterns_at(history, index=1)
    at_full = detect_patterns_at(history + future, index=1)
    assert at_history == at_full


def test_repeated_execution_determinism() -> None:
    """Repeated runs on the same input must produce bit-for-bit identical results."""
    c1 = _ohlcv("1.0860", "1.0865", "1.0845", "1.0850", minute=0)
    c2 = _ohlcv("1.0848", "1.0875", "1.0845", "1.0870", minute=1)
    candles = [c1, c2]

    first_run = detect_patterns(candles)
    for _ in range(50):
        next_run = detect_patterns(candles)
        assert first_run == next_run
