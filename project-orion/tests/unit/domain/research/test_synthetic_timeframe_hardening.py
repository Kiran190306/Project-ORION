"""Tests for Synthetic Historical Data Timeframe Hardening (PROJECT ORION Phase 4.3).

Validates:
1. Exact timestamp spacing for all 8 standard canonical timeframes:
   M1 (1m), M5 (5m), M15 (15m), M30 (30m), H1 (1h), H4 (4h), D1 (1d), W1 (1w).
2. Calendar-aware progression for MN1 (monthly).
3. Invalid timeframe rejection (fail-closed, no silent fallback).
4. Determinism (same inputs produce identical hashes, prices, and timestamps).
5. Monotonic timestamps without duplicate timestamps.
6. Provenance timeframe consistency across all timeframes.
7. OHLC integrity invariants (high >= max(open,close), low <= min(open,close)).
8. Support for string aliases (15m, 1h, 4h, 1d, 1w, 1mo, weekly, monthly).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.historical_data import (
    MarketDataServiceHistoricalProvider,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.market_data.exceptions import UnsupportedBarTypeError
from libraries.domain.market_data.models import BarType


# ─── 1. Exact Timestamp Spacing for M1 through W1 ────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("timeframe", "expected_delta"),
    [
        (Timeframe.M1, timedelta(minutes=1)),
        (Timeframe.M5, timedelta(minutes=5)),
        (Timeframe.M15, timedelta(minutes=15)),
        (Timeframe.M30, timedelta(minutes=30)),
        (Timeframe.H1, timedelta(hours=1)),
        (Timeframe.H4, timedelta(hours=4)),
        (Timeframe.D1, timedelta(days=1)),
        (Timeframe.WEEKLY, timedelta(weeks=1)),
    ],
)
async def test_synthetic_candles_exact_spacing(
    timeframe: Timeframe,
    expected_delta: timedelta,
) -> None:
    """Verify that consecutive synthetic candles within a trading session have exact timestamp spacing."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    # Pick a date range starting on a Monday to ensure continuous trading
    start = date(2025, 1, 6)   # Monday
    end = date(2025, 1, 9) if timeframe != Timeframe.WEEKLY else date(2025, 3, 31)

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=timeframe,
        start_date=start,
        end_date=end,
    )

    assert len(candles) >= 3, f"Expected at least 3 candles for {timeframe.name}, got {len(candles)}"

    # Check spacing between consecutive candles within the same day / session
    for i in range(min(10, len(candles) - 1)):
        delta = candles[i + 1]["timestamp"] - candles[i]["timestamp"]
        # If consecutive bars are within the same active trading window
        if candles[i + 1]["timestamp"].weekday() < 5 and candles[i]["timestamp"].weekday() < 5:
            # For intraday bars on the same day:
            if candles[i + 1]["timestamp"].date() == candles[i]["timestamp"].date():
                assert delta == expected_delta, f"Mismatch for {timeframe.name}: {delta} != {expected_delta}"
            elif timeframe in (Timeframe.D1, Timeframe.WEEKLY):
                assert delta == expected_delta, f"Mismatch for {timeframe.name}: {delta} != {expected_delta}"


# ─── 2. MN1 Calendar-Aware Monthly Progression ────────────────────────────────


@pytest.mark.asyncio
async def test_synthetic_candles_mn1_calendar_progression() -> None:
    """Verify that MN1 produces calendar-aware monthly candles (month-by-month increment)."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    start = date(2025, 1, 1)
    end = date(2025, 6, 30)

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=Timeframe.MONTHLY,
        start_date=start,
        end_date=end,
    )

    # 6 calendar months: Jan, Feb, Mar, Apr, May, Jun
    assert len(candles) == 6, f"Expected 6 monthly candles, got {len(candles)}"

    for i in range(len(candles) - 1):
        c_curr = candles[i]["timestamp"]
        c_next = candles[i + 1]["timestamp"]

        # Month should advance by exactly 1
        expected_month = (c_curr.month % 12) + 1
        assert c_next.month == expected_month, f"Expected month {expected_month}, got {c_next.month}"

        # Year should advance if rolled past December
        expected_year = c_curr.year + (1 if c_curr.month == 12 else 0)
        assert c_next.year == expected_year, f"Expected year {expected_year}, got {c_next.year}"

        # Day should remain 1st of the month
        assert c_next.day == c_curr.day == 1

        # Strict monotonicity
        assert c_next > c_curr


# ─── 3. String Aliases Spacing ────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("alias", "expected_delta"),
    [
        ("1m", timedelta(minutes=1)),
        ("5m", timedelta(minutes=5)),
        ("15m", timedelta(minutes=15)),
        ("30m", timedelta(minutes=30)),
        ("1h", timedelta(hours=1)),
        ("4h", timedelta(hours=4)),
        ("1d", timedelta(days=1)),
        ("1w", timedelta(weeks=1)),
        ("weekly", timedelta(weeks=1)),
    ],
)
async def test_synthetic_candles_string_aliases_spacing(
    alias: str,
    expected_delta: timedelta,
) -> None:
    """Verify string aliases (e.g. '15m', '1h', 'weekly') produce expected spacing."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    start = date(2025, 1, 6)
    end = date(2025, 1, 8) if "w" not in alias else date(2025, 3, 31)

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=alias,  # string alias
        start_date=start,
        end_date=end,
    )

    assert len(candles) >= 2
    # Verify first step
    if candles[0]["timestamp"].date() == candles[1]["timestamp"].date() or "w" in alias or alias == "1d":
        assert candles[1]["timestamp"] - candles[0]["timestamp"] == expected_delta


# ─── 4. Invalid Timeframe Rejection ───────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_tf", ["2h", "90m", "foobar", "", "10m", "3d"])
async def test_synthetic_candles_invalid_timeframe_rejection(invalid_tf: str) -> None:
    """Verify invalid timeframe strings fail explicitly with UnsupportedBarTypeError."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    with pytest.raises(UnsupportedBarTypeError):
        await provider.load_candles(
            symbol="EUR/USD",
            timeframe=invalid_tf,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 5),
        )


# ─── 5. Determinism ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("timeframe", [Timeframe.M15, Timeframe.H1, Timeframe.D1, Timeframe.MONTHLY])
async def test_synthetic_candles_determinism(timeframe: Timeframe) -> None:
    """Verify that multiple runs with identical parameters produce identical candles and hash."""
    provider1 = MarketDataServiceHistoricalProvider(source_mode="synthetic")
    provider2 = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    start = date(2025, 1, 1)
    end = date(2025, 1, 10) if timeframe != Timeframe.MONTHLY else date(2025, 6, 30)

    candles1 = await provider1.load_candles(symbol="EUR/USD", timeframe=timeframe, start_date=start, end_date=end)
    candles2 = await provider2.load_candles(symbol="EUR/USD", timeframe=timeframe, start_date=start, end_date=end)

    assert len(candles1) == len(candles2)
    assert provider1.last_provenance.dataset_hash == provider2.last_provenance.dataset_hash

    for c1, c2 in zip(candles1, candles2):
        assert c1["timestamp"] == c2["timestamp"]
        assert c1["open"] == c2["open"]
        assert c1["high"] == c2["high"]
        assert c1["low"] == c2["low"]
        assert c1["close"] == c2["close"]
        assert c1["volume"] == c2["volume"]


# ─── 6. Monotonicity & No Duplicates ──────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("timeframe", list(Timeframe))
async def test_synthetic_candles_monotonic_no_duplicates(timeframe: Timeframe) -> None:
    """Verify timestamps are strictly monotonic with zero duplicate timestamps for all 9 timeframes."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    start = date(2025, 1, 6)
    end = date(2025, 1, 8) if timeframe not in (Timeframe.WEEKLY, Timeframe.MONTHLY) else date(2025, 6, 30)

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=timeframe,
        start_date=start,
        end_date=end,
    )

    assert len(candles) > 0
    timestamps = [c["timestamp"] for c in candles]

    # No duplicates
    assert len(timestamps) == len(set(timestamps)), f"Found duplicate timestamps in {timeframe.name}"

    # Strictly monotonic
    for i in range(len(timestamps) - 1):
        assert timestamps[i + 1] > timestamps[i], f"Timestamp ordering violation in {timeframe.name} at index {i}"


# ─── 7. Provenance Timeframe Consistency ──────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("timeframe", list(Timeframe))
async def test_synthetic_provenance_timeframe_consistency(timeframe: Timeframe) -> None:
    """Verify that provenance records the exact requested timeframe for all 9 timeframes."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    start = date(2025, 1, 6)
    end = date(2025, 1, 8) if timeframe not in (Timeframe.WEEKLY, Timeframe.MONTHLY) else date(2025, 6, 30)

    await provider.load_candles(
        symbol="EUR/USD",
        timeframe=timeframe,
        start_date=start,
        end_date=end,
    )

    prov = provider.last_provenance
    assert prov is not None
    assert prov.timeframe == timeframe.value
    assert prov.synthetic is True
    assert prov.deterministic is True
    assert prov.data_source == "synthetic"
    assert prov.provider == "deterministic_prng"


# ─── 8. OHLC Integrity Invariants ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("timeframe", [Timeframe.M1, Timeframe.M15, Timeframe.H4, Timeframe.D1])
async def test_synthetic_candles_ohlc_invariants(timeframe: Timeframe) -> None:
    """Verify mathematical OHLC invariants (high >= max(open, close), low <= min(open, close))."""
    provider = MarketDataServiceHistoricalProvider(source_mode="synthetic")

    candles = await provider.load_candles(
        symbol="EUR/USD",
        timeframe=timeframe,
        start_date=date(2025, 1, 6),
        end_date=date(2025, 1, 7),
    )

    assert len(candles) > 0
    for c in candles:
        assert isinstance(c["open"], Decimal)
        assert isinstance(c["high"], Decimal)
        assert isinstance(c["low"], Decimal)
        assert isinstance(c["close"], Decimal)
        assert isinstance(c["volume"], Decimal)

        assert c["high"] >= max(c["open"], c["close"])
        assert c["low"] <= min(c["open"], c["close"])
        assert c["volume"] > Decimal(0)
