"""Tests for the SMA indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar
from libraries.domain.indicators.sma import SMA


@pytest.fixture
def sma() -> SMA:
    return SMA(period=3)


@pytest.fixture
def bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=1.0, volume=100),
        Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=2.0, volume=100),
        Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=3.0, volume=100),
        Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=4.0, volume=100),
        Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=5.0, volume=100),
    ]


class TestSMA:
    async def test_initialize(self, sma: SMA) -> None:
        config = IndicatorConfig(period=5, symbol="EURUSD")
        await sma.initialize(config)
        assert sma.config is not None
        assert sma.config.period == 5

    async def test_warmup_and_update(self, sma: SMA, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup(bars)
        assert sma.is_warmed_up() is True

        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=5.0,
            high=6.0,
            low=4.5,
            close=6.0,
            volume=100,
        )
        result = await sma.update(bar)
        assert result.value is not None

    async def test_sma_value(self, sma: SMA, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup(bars[:3])
        # After warmup on [1,2,3], SMA = 2.0
        # Rolling closes = [1,2,3], sum = 6
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=4.0,
            high=5.0,
            low=3.5,
            close=4.0,
            volume=100,
        )
        result = await sma.update(bar)
        # SMA = (6 - 1 + 4) / 3 = 9/3 = 3.0
        assert result.value is not None and abs(result.value - 3.0) < 0.01

    async def test_batch_calculate(self, sma: SMA, bars: list[Bar]) -> None:
        results = await sma.batch_calculate(bars)
        assert len(results) > 0

    async def test_reset(self, sma: SMA, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup(bars)
        await sma.reset()
        assert sma.is_warmed_up() is False

    async def test_serialize_deserialize(self, sma: SMA, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup(bars)
        data = await sma.serialize()
        assert data["metadata"]["name"] == "sma"
        assert data["state"]["rolling_sum"] is not None
        restored = await SMA.deserialize(data)
        assert restored.metadata.name == "sma"
        assert restored.is_warmed_up() is True

    async def test_incremental_tracking(self) -> None:
        sma = SMA(period=3)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bars = [
            Bar(timestamp=ts, open=1.0, high=2.0, low=0.5, close=float(i + 1), volume=100)
            for i in range(5)
        ]
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup(bars)
        # Values should be: 1, 2, 3, 4, 5
        # After warmup: rolling_closes = [1,2,3,4,5]
        bar = Bar(timestamp=ts, open=6.0, high=7.0, low=5.5, close=6.0, volume=100)
        result = await sma.update(bar)
        # SMA of [4,5,6] = 5.0
        assert result.value is not None and abs(result.value - 5.0) < 0.01

    async def test_empty_data(self, sma: SMA) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
        await sma.warmup([])
        assert sma.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, sma: SMA) -> None:
        config = IndicatorConfig(period=3)
        await sma.initialize(config)
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
            await sma.update(bar)
