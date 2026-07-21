"""Tests for the ADX indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.adx import ADX
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar


@pytest.fixture
def adx() -> ADX:
    return ADX(period=14)


@pytest.fixture
def trending_bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    bars = []
    for i in range(30):
        price += 0.5 if i % 2 == 0 else -0.1
        bars.append(
            Bar(
                timestamp=ts,
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=1000,
            )
        )
    return bars


class TestADX:
    async def test_initialize(self, adx: ADX) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        assert adx.config is not None

    async def test_warmup_and_update(self, adx: ADX, trending_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup(trending_bars)
        assert adx.is_warmed_up() is True
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=115.0,
            high=116.0,
            low=114.0,
            close=115.5,
            volume=1000,
        )
        result = await adx.update(bar)
        assert result.value is not None
        assert "di_plus" in result.values
        assert "di_minus" in result.values

    async def test_adx_range(self, adx: ADX, trending_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup(trending_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=115.0,
            high=116.0,
            low=114.0,
            close=115.5,
            volume=1000,
        )
        result = await adx.update(bar)
        assert 0 <= result.value <= 100

    async def test_di_components(self, adx: ADX, trending_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup(trending_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=115.0,
            high=116.0,
            low=114.0,
            close=115.5,
            volume=1000,
        )
        result = await adx.update(bar)
        assert 0 <= result.values["di_plus"] <= 100
        assert 0 <= result.values["di_minus"] <= 100

    async def test_batch_calculate(self, adx: ADX, trending_bars: list[Bar]) -> None:
        results = await adx.batch_calculate(trending_bars)
        assert len(results) > 0

    async def test_reset(self, adx: ADX, trending_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup(trending_bars)
        await adx.reset()
        assert adx.is_warmed_up() is False

    async def test_serialize_deserialize(self, adx: ADX, trending_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup(trending_bars)
        data = await adx.serialize()
        assert data["metadata"]["name"] == "adx"
        restored = await ADX.deserialize(data)
        assert restored.metadata.name == "adx"

    async def test_empty_data(self, adx: ADX) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
        await adx.warmup([])
        assert adx.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, adx: ADX) -> None:
        config = IndicatorConfig(period=14)
        await adx.initialize(config)
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
            await adx.update(bar)
