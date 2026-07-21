"""Tests for the EMA indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar


@pytest.fixture
def ema() -> EMA:
    return EMA(period=5)


@pytest.fixture
def bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(timestamp=ts, open=10.0, high=11.0, low=9.5, close=10.5, volume=1000),
        Bar(timestamp=ts, open=10.5, high=11.5, low=10.0, close=11.0, volume=1200),
        Bar(timestamp=ts, open=11.0, high=12.0, low=10.5, close=11.5, volume=1100),
        Bar(timestamp=ts, open=11.5, high=12.5, low=11.0, close=12.0, volume=1300),
        Bar(timestamp=ts, open=12.0, high=13.0, low=11.5, close=12.5, volume=1400),
        Bar(timestamp=ts, open=12.5, high=13.5, low=12.0, close=13.0, volume=1500),
    ]


class TestEMA:
    """Test suite for EMA indicator."""

    async def test_initialize(self, ema: EMA) -> None:
        """Test indicator initialization."""
        config = IndicatorConfig(period=10, symbol="EURUSD")
        await ema.initialize(config)
        assert ema.config is not None
        assert ema.config.period == 10
        assert ema.config.symbol == "EURUSD"

    async def test_initialize_default(self, ema: EMA) -> None:
        """Test initialization with default config."""
        config = IndicatorConfig()
        await ema.initialize(config)
        assert ema.is_warmed_up() is False

    async def test_warmup_and_update(self, ema: EMA, bars: list[Bar]) -> None:
        """Test warmup followed by streaming update."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        await ema.warmup(bars)
        assert ema.is_warmed_up() is True

        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=13.0,
            high=14.0,
            low=12.5,
            close=13.5,
            volume=1600,
        )
        result = await ema.update(new_bar)
        assert result.value is not None
        assert result.indicator_name == "ema"

    async def test_update_before_warmup_raises(self, ema: EMA) -> None:
        """Test that update before warmup raises WarmupError."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=1000,
        )
        from libraries.domain.indicators.exceptions import WarmupError

        with pytest.raises(WarmupError):
            await ema.update(bar)

    async def test_empty_warmup(self, ema: EMA) -> None:
        """Test warmup with empty bars."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        await ema.warmup([])
        assert ema.is_warmed_up() is True

    async def test_single_bar_warmup(self, ema: EMA) -> None:
        """Test warmup with a single bar."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=10.0,
            high=11.0,
            low=9.5,
            close=10.5,
            volume=1000,
        )
        await ema.warmup([bar])
        assert ema.is_warmed_up() is True
        result = await ema.update(bar)
        assert result.value is not None

    async def test_batch_calculate(self, ema: EMA, bars: list[Bar]) -> None:
        """Test batch calculation."""
        results = await ema.batch_calculate(bars)
        assert len(results) > 0
        for r in results:
            assert r.indicator_name == "ema"

    async def test_reset(self, ema: EMA, bars: list[Bar]) -> None:
        """Test reset returns to initial state."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        await ema.warmup(bars)
        assert ema.is_warmed_up() is True

        await ema.reset()
        assert ema.is_warmed_up() is False

    async def test_serialize_deserialize(self, ema: EMA, bars: list[Bar]) -> None:
        """Test serialize/deserialize round-trip."""
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        await ema.warmup(bars)

        new_bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=13.0,
            high=14.0,
            low=12.5,
            close=13.5,
            volume=1600,
        )
        await ema.update(new_bar)

        data = await ema.serialize()
        assert data["metadata"]["name"] == "ema"
        assert data["state"]["warmed_up"] is True
        assert data["state"]["current_ema"] is not None

        restored = await EMA.deserialize(data)
        assert restored.metadata.name == "ema"
        assert restored.is_warmed_up() is True

    async def test_required_period(self, ema: EMA) -> None:
        """Test required period returns correct value."""
        assert ema.required_period() == 5

    async def test_get_recent_values(self, ema: EMA, bars: list[Bar]) -> None:
        """Test retrieving recent computed values."""
        await ema.batch_calculate(bars)
        recent = ema.get_recent_values(3)
        assert len(recent) <= 3

    async def test_indicator_type(self, ema: EMA) -> None:
        """Test indicator type is TREND."""
        assert ema.metadata.indicator_type.value == "trend"

    async def test_ema_values(self) -> None:
        """Test EMA calculation produces expected values."""
        ema = EMA(period=3)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bars = [
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=1.0, volume=100),
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=2.0, volume=100),
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=3.0, volume=100),
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=4.0, volume=100),
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=5.0, volume=100),
        ]
        results = await ema.batch_calculate(bars)
        assert len(results) == len(bars) - 3
        # After warmup on 3 bars (1,2,3) -> SMA = 2.0
        # Update close=4: ema = (4-2)*0.5+2 = 3.0
        # Update close=5: ema = (5-3)*0.5+3 = 4.0
        assert results[0].value is not None and abs(results[0].value - 3.0) < 0.01
        assert results[1].value is not None and abs(results[1].value - 4.0) < 0.01

    async def test_ema_with_nan(self) -> None:
        """Test EMA handles NaN-like edge cases gracefully."""
        ema = EMA(period=3)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bar = Bar(timestamp=ts, open=0.0, high=0.0, low=0.0, close=0.0, volume=0)
        config = IndicatorConfig(period=3)
        await ema.initialize(config)
        await ema.warmup([bar, bar, bar])
        result = await ema.update(bar)
        assert result.value is not None and result.value == 0.0
