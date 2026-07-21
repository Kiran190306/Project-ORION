"""Tests for the ATR indicator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.atr import ATR
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import Bar


@pytest.fixture
def atr() -> ATR:
    return ATR(period=14)


@pytest.fixture
def volatile_bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(timestamp=ts, open=100.0, high=105.0, low=95.0, close=100.0, volume=1000)
        for _ in range(20)
    ]


class TestATR:
    async def test_initialize(self, atr: ATR) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        assert atr.config is not None
        assert atr.config.period == 14

    async def test_warmup_and_update(self, atr: ATR, volatile_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        await atr.warmup(volatile_bars)
        assert atr.is_warmed_up() is True
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=106.0,
            low=94.0,
            close=100.0,
            volume=1000,
        )
        result = await atr.update(bar)
        assert result.value is not None
        assert result.value > 0

    async def test_atr_value_range(self, atr: ATR, volatile_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        await atr.warmup(volatile_bars)
        bar = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=100.0,
            high=106.0,
            low=94.0,
            close=100.0,
            volume=1000,
        )
        result = await atr.update(bar)
        # ATR should be positive and reasonable
        assert result.value > 0
        assert result.value < 20

    async def test_batch_calculate(self, atr: ATR, volatile_bars: list[Bar]) -> None:
        results = await atr.batch_calculate(volatile_bars)
        assert len(results) > 0

    async def test_reset(self, atr: ATR, volatile_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        await atr.warmup(volatile_bars)
        await atr.reset()
        assert atr.is_warmed_up() is False

    async def test_serialize_deserialize(self, atr: ATR, volatile_bars: list[Bar]) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        await atr.warmup(volatile_bars)
        data = await atr.serialize()
        assert data["metadata"]["name"] == "atr"
        restored = await ATR.deserialize(data)
        assert restored.metadata.name == "atr"

    async def test_true_range_component(self, atr: ATR) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=110.0,
            low=90.0,
            close=100.0,
            volume=1000,
        )
        await atr.warmup([bar])
        result = await atr.update(bar)
        assert "tr" in result.values

    async def test_empty_data(self, atr: ATR) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
        await atr.warmup([])
        assert atr.is_warmed_up() is True

    async def test_update_before_warmup_raises(self, atr: ATR) -> None:
        config = IndicatorConfig(period=14)
        await atr.initialize(config)
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
            await atr.update(bar)

    async def test_incremental_same_as_batch(self) -> None:
        """Test that incremental updates match batch calculation."""
        atr1 = ATR(period=5)
        atr2 = ATR(period=5)
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        bars = [
            Bar(
                timestamp=ts,
                open=100.0,
                high=float(100 + i + 2),
                low=float(100 - i - 2),
                close=100.0,
                volume=1000,
            )
            for i in range(10)
        ]

        # Batch - warms up 5 bars, updates 5 bars
        batch_results = await atr1.batch_calculate(bars)

        # Incremental - warm up with same 5 bars, update the same 5 bars
        config = IndicatorConfig(period=5)
        await atr2.initialize(config)
        await atr2.warmup(bars[:5])
        inc_results = []
        for bar in bars[5:]:
            r = await atr2.update(bar)
            inc_results.append(r)

        if batch_results and inc_results:
            assert abs(batch_results[-1].value - inc_results[-1].value) < 0.001
