"""Tests for the MACD indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.macd import MACD
from libraries.domain.indicators.models import Bar


@pytest.fixture
def macd() -> MACD:
    return MACD(fast_period=12, slow_period=26, signal_period=9)


@pytest.fixture
def bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            timestamp=ts,
            open=float(i),
            high=float(i + 1),
            low=float(i - 1),
            close=float(i),
            volume=1000,
        )
        for i in range(50)
    ]


class TestMACD:
    async def test_initialize(self, macd: MACD) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        assert macd.config is not None

    async def test_warmup_and_update(self, macd: MACD, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        await macd.warmup(bars)
        assert macd.is_warmed_up() is True

        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=50.0,
            high=51.0,
            low=49.0,
            close=50.5,
            volume=1000,
        )
        result = await macd.update(bar)
        assert result.value is not None
        assert "signal" in result.values
        assert "histogram" in result.values

    async def test_macd_components(self, macd: MACD, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        await macd.warmup(bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=50.0,
            high=51.0,
            low=49.0,
            close=50.5,
            volume=1000,
        )
        result = await macd.update(bar)
        assert result.values["signal"] is not None
        assert result.values["histogram"] is not None
        assert result.values["fast_ema"] is not None
        assert result.values["slow_ema"] is not None

    async def test_batch_calculate(self, macd: MACD, bars: list[Bar]) -> None:
        results = await macd.batch_calculate(bars)
        assert len(results) > 0

    async def test_reset(self, macd: MACD, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        await macd.warmup(bars)
        await macd.reset()
        assert macd.is_warmed_up() is False

    async def test_serialize_deserialize(self, macd: MACD, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        await macd.warmup(bars)
        data = await macd.serialize()
        assert data["metadata"]["name"] == "macd"
        restored = await MACD.deserialize(data)
        assert restored.metadata.name == "macd"

    async def test_empty_data(self, macd: MACD) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        await macd.warmup([])
        assert macd.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, macd: MACD) -> None:
        config = IndicatorConfig(period=26)
        await macd.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=10.0,
            high=11.0,
            low=9.0,
            close=10.5,
            volume=1000,
        )
        from libraries.domain.indicators.exceptions import WarmupError

        with pytest.raises(WarmupError):
            await macd.update(bar)
