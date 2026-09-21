"""Unit tests for Market Data Quality Engine and extended validation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from libraries.domain.market_data.exceptions import (
    InvalidBarError,
    InvalidQuoteError,
    StaleDataError,
)
from libraries.domain.market_data.models import (
    BarType,
    DataQuality,
    OHLCV,
    Quote,
)
from libraries.domain.market_data.quality_engine import MarketDataQualityEngine
from libraries.domain.market_data.validation import (
    check_staleness,
    validate_ohlc,
    validate_quote,
)


class TestValidateOHLC:
    """Test validate_ohlc invariants."""

    def test_valid_ohlc(self) -> None:
        o, h, l, c, v = validate_ohlc(
            Decimal("1.0850"),
            Decimal("1.0890"),
            Decimal("1.0840"),
            Decimal("1.0875"),
            Decimal("1500"),
        )
        assert o == Decimal("1.0850")
        assert h == Decimal("1.0890")
        assert l == Decimal("1.0840")
        assert c == Decimal("1.0875")
        assert v == Decimal("1500")

    def test_high_less_than_low_raises_error(self) -> None:
        with pytest.raises(InvalidBarError, match="cannot be less than low"):
            validate_ohlc(
                Decimal("1.0850"),
                Decimal("1.0800"),  # high < low
                Decimal("1.0840"),
                Decimal("1.0830"),
            )

    def test_open_above_high_raises_error(self) -> None:
        with pytest.raises(InvalidBarError, match="Open price.*must be within"):
            validate_ohlc(
                Decimal("1.0950"),  # open > high
                Decimal("1.0900"),
                Decimal("1.0800"),
                Decimal("1.0850"),
            )

    def test_close_below_low_raises_error(self) -> None:
        with pytest.raises(InvalidBarError, match="Close price.*must be within"):
            validate_ohlc(
                Decimal("1.0850"),
                Decimal("1.0900"),
                Decimal("1.0800"),
                Decimal("1.0750"),  # close < low
            )

    def test_negative_volume_raises_error(self) -> None:
        with pytest.raises(InvalidBarError, match="volume cannot be negative"):
            validate_ohlc(
                Decimal("1.0850"),
                Decimal("1.0900"),
                Decimal("1.0800"),
                Decimal("1.0850"),
                Decimal("-10"),
            )


class TestValidateQuote:
    """Test validate_quote invariants."""

    def test_valid_quote(self) -> None:
        now = datetime.now(timezone.utc)
        bid, ask, ts = validate_quote(Decimal("1.08500"), Decimal("1.08510"), now)
        assert bid == Decimal("1.08500")
        assert ask == Decimal("1.08510")
        assert ts == now

    def test_crossed_market_raises_error(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(InvalidQuoteError, match="Crossed market"):
            validate_quote(Decimal("1.08550"), Decimal("1.08500"), now)

    def test_max_spread_violation_raises_error(self) -> None:
        now = datetime.now(timezone.utc)
        with pytest.raises(InvalidQuoteError, match="Spread.*exceeds max"):
            validate_quote(
                Decimal("1.08500"),
                Decimal("1.08600"),
                now,
                max_spread=Decimal("0.00050"),
            )

    def test_future_quote_raises_error(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        with pytest.raises(InvalidQuoteError, match="too far in future"):
            validate_quote(Decimal("1.08500"), Decimal("1.08510"), future)


class TestStalenessCheck:
    """Test check_staleness function."""

    def test_fresh_timestamp(self) -> None:
        now = datetime.now(timezone.utc)
        recent = now - timedelta(seconds=5)
        assert check_staleness(recent, max_age_seconds=30.0, current_time=now) is False

    def test_stale_timestamp(self) -> None:
        now = datetime.now(timezone.utc)
        old = now - timedelta(seconds=35)
        assert check_staleness(old, max_age_seconds=30.0, current_time=now) is True

    def test_naive_timestamp_raises_error(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0, 0, tzinfo=None)
        with pytest.raises(StaleDataError, match="timezone-naive"):
            check_staleness(naive)


@pytest.mark.asyncio
class TestMarketDataQualityEngine:
    """Test MarketDataQualityEngine deduplication, ordering, and evaluation."""

    async def test_quote_evaluation_clean(self) -> None:
        engine = MarketDataQualityEngine(stale_threshold_seconds=30.0)
        now = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08510"),
            timestamp=now,
            provider="test_feed",
        )

        assessment = await engine.evaluate_quote(quote)
        assert assessment.is_valid is True
        assert assessment.is_duplicate is False
        assert assessment.is_out_of_order is False
        assert assessment.is_stale is False
        assert assessment.quality in (DataQuality.EXCELLENT, DataQuality.GOOD)

    async def test_quote_deduplication(self) -> None:
        engine = MarketDataQualityEngine()
        now = datetime.now(timezone.utc)
        quote = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08510"),
            timestamp=now,
        )

        first = await engine.evaluate_quote(quote)
        assert first.is_duplicate is False

        second = await engine.evaluate_quote(quote)
        assert second.is_duplicate is True
        assert second.quality == DataQuality.DEGRADED

    async def test_quote_out_of_order(self) -> None:
        engine = MarketDataQualityEngine()
        now = datetime.now(timezone.utc)

        quote1 = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08510"),
            timestamp=now,
        )
        quote2 = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08505"),
            ask=Decimal("1.08515"),
            timestamp=now - timedelta(seconds=10),  # Earlier timestamp!
        )

        await engine.evaluate_quote(quote1)
        assessment2 = await engine.evaluate_quote(quote2)
        assert assessment2.is_out_of_order is True

    async def test_quote_staleness(self) -> None:
        engine = MarketDataQualityEngine(stale_threshold_seconds=10.0)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=20)
        quote = Quote(
            symbol="EUR/USD",
            bid=Decimal("1.08500"),
            ask=Decimal("1.08510"),
            timestamp=old_time,
        )

        assessment = await engine.evaluate_quote(quote)
        assert assessment.is_stale is True
        assert assessment.quality == DataQuality.STALE

    async def test_ohlcv_evaluation_and_deduplication(self) -> None:
        engine = MarketDataQualityEngine()
        now = datetime.now(timezone.utc)
        bar = OHLCV(
            symbol="EUR/USD",
            timestamp=now,
            open=Decimal("1.0850"),
            high=Decimal("1.0890"),
            low=Decimal("1.0840"),
            close=Decimal("1.0870"),
            volume=Decimal("100"),
            bar_type=BarType.M1,
        )

        assessment1 = await engine.evaluate_ohlcv(bar)
        assert assessment1.is_valid is True
        assert assessment1.is_duplicate is False

        assessment2 = await engine.evaluate_ohlcv(bar)
        assert assessment2.is_duplicate is True
