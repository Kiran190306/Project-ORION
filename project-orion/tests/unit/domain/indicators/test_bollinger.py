"""Tests for the Bollinger Bands indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.bollinger import BollingerBands
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar


@pytest.fixture
def bb() -> BollingerBands:
    return BollingerBands(period=5, num_std=2.0)


@pytest.fixture
def stable_bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0, volume=1000)
        for _ in range(10)
    ]


class TestBollingerBands:
    async def test_initialize(self, bb: BollingerBands) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        assert bb.config is not None

    async def test_warmup_and_update(self, bb: BollingerBands, stable_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup(stable_bars)
        assert bb.is_warmed_up() is True
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = await bb.update(bar)
        assert result.value is not None
        assert "upper" in result.values
        assert "lower" in result.values
        assert "bandwidth" in result.values
        assert "percent_b" in result.values

    async def test_bands_ordered(self, bb: BollingerBands, stable_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup(stable_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = await bb.update(bar)
        assert result.values["upper"] >= result.value >= result.values["lower"]

    async def test_batch_calculate(self, bb: BollingerBands, stable_bars: list[Bar]) -> None:
        results = await bb.batch_calculate(stable_bars)
        assert len(results) > 0

    async def test_reset(self, bb: BollingerBands, stable_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup(stable_bars)
        await bb.reset()
        assert bb.is_warmed_up() is False

    async def test_empty_data(self, bb: BollingerBands) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup([])
        assert bb.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, bb: BollingerBands) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
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
            await bb.update(bar)

    async def test_bandwidth_non_negative(self, bb: BollingerBands, stable_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup(stable_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = await bb.update(bar)
        assert result.values["bandwidth"] >= 0

    async def test_percent_b_between_zero_and_one(
        self, bb: BollingerBands, stable_bars: list[Bar]
    ) -> None:
        config = IndicatorConfig(period=5)
        await bb.initialize(config)
        await bb.warmup(stable_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = await bb.update(bar)
        assert 0 <= result.values["percent_b"] <= 1
