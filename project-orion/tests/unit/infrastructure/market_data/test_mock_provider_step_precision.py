"""Unit tests for MockMarketDataProvider timeframe step precision (Phase 4.5).

Verifies that every canonical ORION timeframe produces candles with exact
timestamp spacing, calendar-aware monthly progression, deterministic output,
strict monotonic ordering, and OHLC invariants with zero silent fallback.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import Timeframe
from libraries.domain.market_data.exceptions import (
    SymbolNotFoundError,
    UnsupportedBarTypeError,
)
from libraries.domain.market_data.models import BarType
from libraries.infrastructure.market_data.mock_provider import MockMarketDataProvider

CANONICAL_TIMEFRAMES_WITH_DELTAS = [
    (BarType.M1, timedelta(minutes=1)),
    (BarType.M5, timedelta(minutes=5)),
    (BarType.M15, timedelta(minutes=15)),
    (BarType.M30, timedelta(minutes=30)),
    (BarType.H1, timedelta(hours=1)),
    (BarType.H4, timedelta(hours=4)),
    (BarType.D1, timedelta(days=1)),
    (BarType.W1, timedelta(weeks=1)),
]

ALL_CANONICAL_BAR_TYPES = [
    BarType.M1,
    BarType.M5,
    BarType.M15,
    BarType.M30,
    BarType.H1,
    BarType.H4,
    BarType.D1,
    BarType.W1,
    BarType.MN1,
]


# ─── 1. Fixed Step Spacing Verification ──────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(("bar_type", "expected_delta"), CANONICAL_TIMEFRAMES_WITH_DELTAS)
async def test_fixed_step_timeframe_spacing(bar_type: BarType, expected_delta: timedelta) -> None:
    """Every fixed-step canonical timeframe must produce candles separated by exact delta."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", bar_type, end=anchor, limit=10)

    assert len(candles) == 10
    for i in range(len(candles) - 1):
        diff = candles[i + 1].timestamp - candles[i].timestamp
        assert diff == expected_delta, (
            f"Timeframe {bar_type.value} produced delta {diff}, expected {expected_delta}"
        )


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
        ("M1", timedelta(minutes=1)),
        ("M5", timedelta(minutes=5)),
        ("M15", timedelta(minutes=15)),
        ("M30", timedelta(minutes=30)),
        ("H1", timedelta(hours=1)),
        ("H4", timedelta(hours=4)),
        ("D1", timedelta(days=1)),
        ("W1", timedelta(weeks=1)),
    ],
)
async def test_string_alias_timeframe_spacing(alias: str, expected_delta: timedelta) -> None:
    """String aliases (e.g. '15m', 'H4') must normalize and produce exact delta."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", alias, end=anchor, limit=6)

    assert len(candles) == 6
    for i in range(len(candles) - 1):
        diff = candles[i + 1].timestamp - candles[i].timestamp
        assert diff == expected_delta


# ─── 2. Calendar-Aware Monthly (MN1) Progression ─────────────────────────────


@pytest.mark.asyncio
async def test_mn1_calendar_month_progression_end_of_month() -> None:
    """MN1 with end-of-month anchor preserves end-of-month semantics across varied month lengths."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 4, 30, 0, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", BarType.MN1, end=anchor, limit=5)

    assert len(candles) == 5
    dates = [c.timestamp.date() for c in candles]
    expected_dates = [
        date(2025, 11, 30),
        date(2025, 12, 31),
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]
    assert dates == expected_dates

    # Confirm non-fixed delta: Jan->Feb is 28 days, Feb->Mar is 31 days
    delta_feb = candles[3].timestamp - candles[2].timestamp
    delta_mar = candles[4].timestamp - candles[3].timestamp
    assert delta_feb == timedelta(days=28)
    assert delta_mar == timedelta(days=31)
    assert delta_feb != delta_mar


@pytest.mark.asyncio
async def test_mn1_calendar_month_progression_leap_year() -> None:
    """MN1 correctly respects leap year (February 29 in 2024)."""
    provider = MockMarketDataProvider()
    anchor = datetime(2024, 3, 31, 0, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", BarType.MN1, end=anchor, limit=3)

    assert len(candles) == 3
    dates = [c.timestamp.date() for c in candles]
    expected_dates = [
        date(2023, 12, 31),
        date(2024, 1, 31),
        date(2024, 2, 29),  # Leap day
    ]
    assert dates == expected_dates


@pytest.mark.asyncio
async def test_mn1_mid_month_progression() -> None:
    """MN1 with mid-month anchor preserves the exact day of month across steps."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 5, 15, 10, 30, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", BarType.MN1, end=anchor, limit=4)

    assert len(candles) == 4
    for c in candles:
        assert c.timestamp.day == 15
        assert c.timestamp.hour == 10
        assert c.timestamp.minute == 30

    dates = [c.timestamp.date() for c in candles]
    assert dates == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]


# ─── 3. Determinism & Monotonicity Invariants ─────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("bar_type", ALL_CANONICAL_BAR_TYPES)
async def test_deterministic_reproducibility(bar_type: BarType) -> None:
    """Identical requests must generate identical candles."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    run1 = await provider.get_candles("EUR/USD", bar_type, end=anchor, limit=10)
    run2 = await provider.get_candles("EUR/USD", bar_type, end=anchor, limit=10)

    assert len(run1) == len(run2) == 10
    for c1, c2 in zip(run1, run2, strict=True):
        assert c1.timestamp == c2.timestamp
        assert c1.open == c2.open
        assert c1.high == c2.high
        assert c1.low == c2.low
        assert c1.close == c2.close
        assert c1.volume == c2.volume
        assert c1.bar_type == c2.bar_type


@pytest.mark.asyncio
@pytest.mark.parametrize("bar_type", ALL_CANONICAL_BAR_TYPES)
async def test_strictly_monotonic_no_duplicates(bar_type: BarType) -> None:
    """Candle timestamps must be strictly ascending with zero duplicates."""
    provider = MockMarketDataProvider()
    candles = await provider.get_candles("EUR/USD", bar_type, limit=20)

    assert len(candles) == 20
    seen_timestamps: set[datetime] = set()

    for i in range(len(candles) - 1):
        assert candles[i].timestamp < candles[i + 1].timestamp
        assert candles[i].timestamp not in seen_timestamps
        seen_timestamps.add(candles[i].timestamp)
    seen_timestamps.add(candles[-1].timestamp)
    assert len(seen_timestamps) == len(candles)


# ─── 4. OHLC Invariants & Timezone Awareness ─────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("bar_type", ALL_CANONICAL_BAR_TYPES)
async def test_ohlc_invariants_and_tz_aware(bar_type: BarType) -> None:
    """All generated candles must satisfy OHLC bounds and have timezone-aware UTC timestamps."""
    provider = MockMarketDataProvider()
    candles = await provider.get_candles("USD/JPY", bar_type, limit=15)

    assert len(candles) == 15
    for c in candles:
        # Timezone aware
        assert c.timestamp.tzinfo is not None
        assert c.timestamp.tzinfo == timezone.utc

        # Positive prices
        assert c.open > Decimal(0)
        assert c.high > Decimal(0)
        assert c.low > Decimal(0)
        assert c.close > Decimal(0)
        assert c.volume >= Decimal(0)

        # OHLC bounds
        assert c.high >= max(c.open, c.close, c.low)
        assert c.low <= min(c.open, c.close, c.high)


# ─── 5. Canonical Symbol Normalization ───────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_symbol", "expected_canonical"),
    [
        ("EUR/USD", "EUR/USD"),
        ("EURUSD", "EUR/USD"),
        ("eur_usd", "EUR/USD"),
        ("USD/JPY", "USD/JPY"),
        ("USDJPY", "USD/JPY"),
        ("XAU/USD", "XAU/USD"),
        ("XAUUSD", "XAU/USD"),
        ("usd/chf", "USD/CHF"),
        ("aud/usd", "AUD/USD"),
    ],
)
async def test_canonical_symbol_normalization(input_symbol: str, expected_canonical: str) -> None:
    """Mock provider must normalize input symbols to canonical representation."""
    provider = MockMarketDataProvider()
    candles = await provider.get_candles(input_symbol, BarType.H1, limit=5)
    assert len(candles) == 5
    for c in candles:
        assert c.symbol == expected_canonical


@pytest.mark.asyncio
async def test_unsupported_symbol_rejection() -> None:
    """Unsupported and phantom symbols (such as EUR/GBP) must raise SymbolNotFoundError."""
    provider = MockMarketDataProvider()
    with pytest.raises(SymbolNotFoundError):
        await provider.get_candles("EUR/GBP", BarType.H1, limit=5)

    with pytest.raises(SymbolNotFoundError):
        await provider.get_candles("INVALID/COIN", BarType.H1, limit=5)


# ─── 6. Invalid Timeframe Rejection (No Silent Fallback) ──────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_tf",
    [
        "2h",
        "90m",
        "unknown",
        "FOOBAR",
        "",
        "10m",
        "3d",
    ],
)
async def test_invalid_timeframe_rejection(invalid_tf: str) -> None:
    """Invalid timeframes must raise UnsupportedBarTypeError without falling back to H1 or 5m."""
    provider = MockMarketDataProvider()
    with pytest.raises(UnsupportedBarTypeError):
        await provider.get_candles("EUR/USD", invalid_tf, limit=5)


# ─── 7. H1 & M5 Deterministic Value Backward Compatibility ────────────────────


@pytest.mark.asyncio
async def test_h1_legacy_value_stability() -> None:
    """H1 candles generated with fixed anchor match exact mathematical expectations."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", BarType.H1, end=anchor, limit=3)

    assert len(candles) == 3
    # Step = 1 hour
    assert candles[0].timestamp == anchor - timedelta(hours=3)
    assert candles[1].timestamp == anchor - timedelta(hours=2)
    assert candles[2].timestamp == anchor - timedelta(hours=1)

    # Base price = 1.08500
    # i=0: offset = (0%10 - 5)*0.0002 = -0.0010, open = 1.08400, close = 1.08410
    assert candles[0].open == Decimal("1.08400")
    assert candles[0].close == Decimal("1.08410")
    assert candles[0].high == Decimal("1.08440")
    assert candles[0].low == Decimal("1.08370")


@pytest.mark.asyncio
async def test_m5_legacy_value_stability() -> None:
    """M5 candles generated with fixed anchor match exact mathematical expectations."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    candles = await provider.get_candles("EUR/USD", BarType.M5, end=anchor, limit=3)

    assert len(candles) == 3
    # Step = 5 minutes
    assert candles[0].timestamp == anchor - timedelta(minutes=15)
    assert candles[1].timestamp == anchor - timedelta(minutes=10)
    assert candles[2].timestamp == anchor - timedelta(minutes=5)


# ─── 8. Limits & Range Filtering ─────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("limit_val", [1, 5, 50, 200])
async def test_various_limit_sizes(limit_val: int) -> None:
    """Provider accurately respects requested limit size."""
    provider = MockMarketDataProvider()
    candles = await provider.get_candles("EUR/USD", BarType.M15, limit=limit_val)
    assert len(candles) == limit_val


@pytest.mark.asyncio
async def test_start_date_clipping() -> None:
    """When start is provided, bars strictly before start are excluded."""
    provider = MockMarketDataProvider()
    anchor = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    start_cut = anchor - timedelta(hours=2)

    candles = await provider.get_candles(
        "EUR/USD", BarType.H1, start=start_cut, end=anchor, limit=5
    )
    # limit=5 generates -5h, -4h, -3h, -2h, -1h
    # start_cut is -2h, so only -2h and -1h qualify
    assert len(candles) == 2
    for c in candles:
        assert c.timestamp >= start_cut


# ─── 9. Domain Timeframe Enum Acceptance ─────────────────────────────────────


@pytest.mark.asyncio
async def test_accepts_domain_timeframe_enum() -> None:
    """Provider accepts backtesting Timeframe enum instances via centralized bridge."""
    provider = MockMarketDataProvider()
    candles = await provider.get_candles("EUR/USD", Timeframe.H4, limit=5)
    assert len(candles) == 5
    assert candles[0].bar_type == BarType.H4
    diff = candles[1].timestamp - candles[0].timestamp
    assert diff == timedelta(hours=4)
