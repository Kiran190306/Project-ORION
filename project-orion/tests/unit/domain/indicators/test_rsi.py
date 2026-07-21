"""Tests for the RSI indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar
from libraries.domain.indicators.rsi import RSI


@pytest.fixture
def rsi() -> RSI:
    return RSI(period=14)


@pytest.fixture
def uptrend_bars() -> list[Bar]:
    """Generate bars in a consistent uptrend."""
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 100.0
    for i in range(20):
        price += 1.0
        bars.append(
            Bar(
                timestamp=ts,
                open=price - 0.5,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=1000,
            )
        )
    return bars


@pytest.fixture
def downtrend_bars() -> list[Bar]:
    """Generate bars in a consistent downtrend."""
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    bars = []
    price = 120.0
    for i in range(20):
        price -= 1.0
        bars.append(
            Bar(
                timestamp=ts,
                open=price + 0.5,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=1000,
            )
        )
    return bars


class TestRSI:
    """Test suite for RSI indicator."""

    async def test_initialize(self, rsi: RSI) -> None:
        """Test indicator initialization."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        assert rsi.config is not None
        assert rsi.config.period == 14

    async def test_warmup_and_update(self, rsi: RSI, uptrend_bars: list[Bar]) -> None:
        """Test warmup followed by streaming update."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup(uptrend_bars)
        assert rsi.is_warmed_up() is True

        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=121.0,
            high=122.0,
            low=120.0,
            close=121.5,
            volume=1000,
        )
        result = await rsi.update(new_bar)
        assert result.value is not None
        assert 0 <= result.value <= 100

    async def test_rsi_in_uptrend(self, rsi: RSI, uptrend_bars: list[Bar]) -> None:
        """Test RSI is high (>50) in an uptrend."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup(uptrend_bars)
        assert rsi.is_warmed_up() is True
        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=121.0,
            high=122.0,
            low=120.0,
            close=121.5,
            volume=1000,
        )
        result = await rsi.update(new_bar)
        assert result.value is not None and result.value > 50

    async def test_rsi_in_downtrend(self, rsi: RSI, downtrend_bars: list[Bar]) -> None:
        """Test RSI is low (<50) in a downtrend."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup(downtrend_bars)
        assert rsi.is_warmed_up() is True
        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = await rsi.update(new_bar)
        assert result.value is not None and result.value < 50

    async def test_rsi_oversold(self, rsi: RSI) -> None:
        """Test RSI below 30 indicates oversold."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        bars = []
        for i in range(16):
            price -= 2.0
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price + 1,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    volume=1000,
                )
            )
        await rsi.warmup(bars)
        result = await rsi.update(
            Bar(
                timestamp=ts,
                open=price - 1,
                high=price,
                low=price - 2,
                close=price - 1,
                volume=1000,
            )
        )
        assert result.value is not None and result.value < 30

    async def test_rsi_overbought(self, rsi: RSI) -> None:
        """Test RSI above 70 indicates overbought."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        bars = []
        for i in range(16):
            price += 2.0
            bars.append(
                Bar(
                    timestamp=ts,
                    open=price - 1,
                    high=price + 1,
                    low=price - 1,
                    close=price,
                    volume=1000,
                )
            )
        await rsi.warmup(bars)
        result = await rsi.update(
            Bar(
                timestamp=ts,
                open=price + 1,
                high=price + 2,
                low=price,
                close=price + 1,
                volume=1000,
            )
        )
        assert result.value is not None and result.value > 70

    async def test_batch_calculate(self, rsi: RSI, uptrend_bars: list[Bar]) -> None:
        """Test batch calculation."""
        results = await rsi.batch_calculate(uptrend_bars)
        assert len(results) > 0
        for r in results:
            assert r.indicator_name == "rsi"

    async def test_reset(self, rsi: RSI, uptrend_bars: list[Bar]) -> None:
        """Test reset returns to initial state."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup(uptrend_bars)
        assert rsi.is_warmed_up() is True
        await rsi.reset()
        assert rsi.is_warmed_up() is False

    async def test_serialize_deserialize(self, rsi: RSI, uptrend_bars: list[Bar]) -> None:
        """Test serialize/deserialize round-trip."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup(uptrend_bars)
        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=121.0,
            high=122.0,
            low=120.0,
            close=121.5,
            volume=1000,
        )
        await rsi.update(new_bar)
        data = await rsi.serialize()
        assert data["metadata"]["name"] == "rsi"
        assert data["state"]["avg_gain"] is not None
        restored = await RSI.deserialize(data)
        assert restored.metadata.name == "rsi"
        assert restored.is_warmed_up() is True

    async def test_empty_data(self, rsi: RSI) -> None:
        """Test behavior with empty data."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        await rsi.warmup([])
        assert rsi.is_warmed_up() is True

    async def test_single_value(self, rsi: RSI) -> None:
        """Test behavior with single value."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        await rsi.warmup([bar])
        assert rsi.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, rsi: RSI) -> None:
        """Test that update before warmup raises error."""
        config = IndicatorConfig(period=14)
        await rsi.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        from libraries.domain.indicators.exceptions import WarmupError

        with pytest.raises(WarmupError):
            await rsi.update(bar)
