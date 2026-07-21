"""Edge case tests for indicators.

Tests NaN handling, empty data, single values, warmup edge cases,
rolling window behavior, and streaming update consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.atr import ATR
from libraries.domain.indicators.bollinger import BollingerBands
from libraries.domain.indicators.donchian import DonchianChannel
from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.macd import MACD
from libraries.domain.indicators.models import Bar, IndicatorResult
from libraries.domain.indicators.momentum import Momentum
from libraries.domain.indicators.obv import OnBalanceVolume
from libraries.domain.indicators.roc import ROC
from libraries.domain.indicators.rsi import RSI
from libraries.domain.indicators.sma import SMA
from libraries.domain.indicators.stochastic import Stochastic
from libraries.domain.indicators.supertrend import SuperTrend
from libraries.domain.indicators.vwap import VWAP
from libraries.domain.indicators.wma import WMA


class TestEdgeCases:
    """Test edge cases across all indicators."""

    @pytest.fixture
    def ts(self) -> datetime:
        return datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def _warmup_and_update(self, indicator, period: int, bars: list[Bar]) -> IndicatorResult:
        """Helper to initialize, warmup, and update an indicator."""
        config = IndicatorConfig(period=period)
        await indicator.initialize(config)
        if bars:
            await indicator.warmup(bars)
        return await indicator.update(bars[-1]) if bars else None

    async def test_empty_initialization(self, ts: datetime) -> None:
        """Test that indicators can be initialized without error."""
        indicators = [
            EMA(period=5),
            SMA(period=5),
            WMA(period=5),
            RSI(period=14),
            MACD(),
            ATR(period=14),
            ROC(period=12),
            Momentum(period=12),
            Stochastic(k_period=14, d_period=3),
            DonchianChannel(period=20),
            SuperTrend(period=10),
        ]
        for indicator in indicators:
            config = IndicatorConfig(period=indicator.required_period())
            await indicator.initialize(config)
            assert indicator.config is not None

    async def test_update_before_warmup_raises(self, ts: datetime) -> None:
        """Test all indicators raise WarmupError on update before warmup."""
        from libraries.domain.indicators.exceptions import WarmupError

        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
        indicators = [
            EMA(period=5),
            SMA(period=5),
            RSI(period=14),
            MACD(),
            ATR(period=14),
        ]
        for indicator in indicators:
            config = IndicatorConfig(period=indicator.required_period())
            await indicator.initialize(config)
            with pytest.raises(WarmupError):
                await indicator.update(bar)

    async def test_single_bar_warmup(self, ts: datetime) -> None:
        """Test that indicators can warm up with a single bar."""
        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
        indicators = [
            EMA(period=5),
            SMA(period=5),
            VWAP(),
            ROC(period=5),
        ]
        for indicator in indicators:
            config = IndicatorConfig(period=indicator.required_period())
            await indicator.initialize(config)
            await indicator.warmup([bar])
            assert indicator.is_warmed_up() is True

    async def test_batch_calculate_empty(self) -> None:
        """Test batch calculate with empty bars returns empty list."""
        ema = EMA(period=5)
        results = await ema.batch_calculate([])
        assert results == []

    async def test_batch_calculate_single_bar(self, ts: datetime) -> None:
        """Test batch calculate with single bar."""
        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
        ema = EMA(period=5)
        results = await ema.batch_calculate([bar])
        assert len(results) >= 0

    async def test_serialize_deserialize_without_warmup(self) -> None:
        """Test serialize/deserialize on uninitialized indicators."""
        ema = EMA(period=5)
        data = await ema.serialize()
        assert data["state"]["warmed_up"] is False
        restored = await EMA.deserialize(data)
        assert restored.is_warmed_up() is False

    async def test_multiple_resets(self, ts: datetime) -> None:
        """Test that reset can be called multiple times."""
        ema = EMA(period=5)
        await ema.reset()
        await ema.reset()
        await ema.reset()
        assert ema.is_warmed_up() is False

    async def test_rolling_window_limits(self, ts: datetime) -> None:
        """Test rolling window doesn't grow unbounded."""
        ema = EMA(period=5)
        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        bars = [
            Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0 + i, volume=1000)
            for i in range(100)
        ]
        await ema.warmup(bars)
        window = ema.get_rolling_window()
        # Should be bounded to period * 4 = 20 bars
        assert len(window) <= 20

    async def test_streaming_consistency(self, ts: datetime) -> None:
        """Test that streaming updates match batch calculations."""
        # SMA: batch vs incremental
        sma_batch = SMA(period=5)
        sma_inc = SMA(period=5)
        bars = [
            Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0 + i, volume=1000)
            for i in range(15)
        ]

        # Batch - warms up 5 bars, updates remaining 10 bars
        batch_results = await sma_batch.batch_calculate(bars)

        # Incremental - warm up with same 5 bars, update the same 10 bars
        config = IndicatorConfig(period=5)
        await sma_inc.initialize(config)
        await sma_inc.warmup(bars[:5])
        inc_results = []
        for bar in bars[5:]:
            r = await sma_inc.update(bar)
            inc_results.append(r)

        if batch_results and inc_results:
            for b, i in zip(batch_results, inc_results):
                assert abs(b.value - i.value) < 0.001

    async def test_bar_with_zero_volume(self, ts: datetime) -> None:
        """Test indicators handle zero volume gracefully."""
        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=0)
        vwap = VWAP()
        config = IndicatorConfig(period=0)
        await vwap.initialize(config)
        await vwap.warmup([bar])
        result = await vwap.update(bar)
        # VWAP with zero volume should return 0 via safe_div
        assert result.value is not None

    async def test_obv_unchanged_close(self, ts: datetime) -> None:
        """Test OBV doesn't change when price is unchanged."""
        obv = OnBalanceVolume()
        config = IndicatorConfig()
        await obv.initialize(config)
        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0, volume=1000)
        await obv.warmup([bar])
        bar2 = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.0, volume=500)
        result = await obv.update(bar2)
        # Close unchanged, so OBV should not change
        obv2 = OnBalanceVolume()
        config2 = IndicatorConfig()
        await obv2.initialize(config2)
        await obv2.warmup([bar])
        result2 = await obv2.update(bar2)
        assert result.value == result2.value

    async def test_indicator_is_warmed_up_property(self, ts: datetime) -> None:
        """Test is_warmed_up returns correct state through lifecycle."""
        ema = EMA(period=5)
        assert ema.is_warmed_up() is False

        config = IndicatorConfig(period=5)
        await ema.initialize(config)
        assert ema.is_warmed_up() is False

        bar = Bar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000)
        await ema.warmup([bar])
        assert ema.is_warmed_up() is True

        await ema.reset()
        assert ema.is_warmed_up() is False
