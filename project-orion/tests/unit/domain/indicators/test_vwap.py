"""Tests for the VWAP indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar
from libraries.domain.indicators.vwap import VWAP


@pytest.fixture
def vwap() -> VWAP:
    return VWAP()


@pytest.fixture
def bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000),
        Bar(timestamp=ts, open=100.5, high=102.0, low=100.0, close=101.0, volume=2000),
        Bar(timestamp=ts, open=101.0, high=103.0, low=100.5, close=102.0, volume=1500),
    ]


class TestVWAP:
    async def test_initialize(self, vwap: VWAP) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        assert vwap.config is not None

    async def test_warmup_and_update(self, vwap: VWAP, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup(bars)
        assert vwap.is_warmed_up() is True
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=102.0,
            high=104.0,
            low=101.5,
            close=103.0,
            volume=1800,
        )
        result = await vwap.update(bar)
        assert result.value is not None
        assert result.value > 0

    async def test_vwap_calculation(self, vwap: VWAP) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bar1 = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0, volume=1000)
        bar2 = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0, volume=1000)
        await vwap.warmup([bar1])
        result = await vwap.update(bar2)
        # (100*1000 + 100*1000) / (1000 + 1000) = 100
        assert abs(result.value - 100.0) < 0.001

    async def test_reset_daily(self, vwap: VWAP, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup(bars)
        await vwap.reset_daily()
        assert vwap.is_warmed_up() is False

    async def test_batch_calculate(self, vwap: VWAP, bars: list[Bar]) -> None:
        results = await vwap.batch_calculate(bars)
        assert len(results) > 0

    async def test_reset(self, vwap: VWAP, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup(bars)
        await vwap.reset()
        assert vwap.is_warmed_up() is False

    async def test_serialize_deserialize(self, vwap: VWAP, bars: list[Bar]) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup(bars)
        data = await vwap.serialize()
        assert data["metadata"]["name"] == "vwap"
        restored = await VWAP.deserialize(data)
        assert restored.metadata.name == "vwap"

    async def test_empty_data(self, vwap: VWAP) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup([])
        assert vwap.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, vwap: VWAP) -> None:
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
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
            await vwap.update(bar)
