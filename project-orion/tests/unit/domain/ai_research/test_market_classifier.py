"""Tests for market_classifier module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import MarketClassificationError
from libraries.domain.ai_research.liquidity_classifier import LiquidityClassifier
from libraries.domain.ai_research.market_classifier import MarketClassifier
from libraries.domain.ai_research.models import MarketCondition, MarketRegime, ResearchDataset
from libraries.domain.ai_research.trend_classifier import TrendClassifier
from libraries.domain.ai_research.volatility_classifier import VolatilityClassifier


def _make_dataset(
    close: list[float] | None = None,
    high: list[float] | None = None,
    low: list[float] | None = None,
    volume: list[float] | None = None,
) -> ResearchDataset:
    n = len(close) if close else 200
    close = close or [100.0 + i * 0.5 for i in range(n)]
    high = high or [v + 2.0 for v in close]
    low = low or [v - 2.0 for v in close]
    volume = volume or [1000.0] * n
    rows = tuple(
        {
            "close": close[i],
            "high": high[i],
            "low": low[i],
            "volume": volume[i],
            "timestamp": datetime.now(timezone.utc),
        }
        for i in range(n)
    )
    return ResearchDataset(
        dataset_id="test", schema=("close", "high", "low", "volume", "timestamp"), rows=rows
    )


class TestMarketClassifier:
    def test_default_init(self):
        mc = MarketClassifier()
        assert mc._trend is not None
        assert mc._volatility is not None
        assert mc._liquidity is not None

    def test_custom_components(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        vc = VolatilityClassifier(atr_period=3)
        lc = LiquidityClassifier(volume_period=5)
        mc = MarketClassifier(
            trend_classifier=tc, volatility_classifier=vc, liquidity_classifier=lc
        )
        assert mc._trend is tc
        assert mc._volatility is vc
        assert mc._liquidity is lc

    def test_classify_returns_complete_result(self):
        mc = MarketClassifier()
        ds = _make_dataset()
        result = asyncio.run(mc.classify(ds))
        assert result.condition is not None
        assert result.regime is not None
        assert result.trend is not None
        assert result.volatility is not None
        assert result.liquidity is not None
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_bull_market(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        vc = VolatilityClassifier(atr_period=3)
        lc = LiquidityClassifier(volume_period=5)
        mc = MarketClassifier(
            trend_classifier=tc, volatility_classifier=vc, liquidity_classifier=lc
        )
        close = [100.0 + i * 2.0 for i in range(30)]
        high = [v + 3.0 for v in close]
        low = [v - 1.0 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(mc.classify(ds))
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.condition, MarketCondition)

    def test_insufficient_data_raises_error(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        mc = MarketClassifier(trend_classifier=tc)
        close = [100.0, 101.0]
        ds = _make_dataset(close=close)
        with pytest.raises(MarketClassificationError):
            asyncio.run(mc.classify(ds))

    def test_classify_with_high_volatility(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        vc = VolatilityClassifier(atr_period=3)
        lc = LiquidityClassifier(volume_period=5)
        mc = MarketClassifier(
            trend_classifier=tc, volatility_classifier=vc, liquidity_classifier=lc
        )
        close = [100.0]
        for i in range(30):
            close.append(close[-1] + (15.0 if i % 2 == 0 else -15.0))
        high = [v + 5.0 for v in close]
        low = [v - 5.0 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(mc.classify(ds))
        assert isinstance(result.regime, MarketRegime)
        assert isinstance(result.condition, MarketCondition)

    def test_classify_unknown_condition(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        vc = VolatilityClassifier(atr_period=3, percentile_low=0.1, percentile_high=0.9)
        lc = LiquidityClassifier(
            volume_period=5, volume_low_threshold=0.1, volume_high_threshold=0.9
        )
        mc = MarketClassifier(
            trend_classifier=tc, volatility_classifier=vc, liquidity_classifier=lc
        )
        close = [100.0 + (i % 3 - 1) * 0.1 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(mc.classify(ds))
        assert isinstance(result.condition, MarketCondition)
        assert isinstance(result.regime, MarketRegime)

    def test_different_regimes(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        vc = VolatilityClassifier(atr_period=3)
        lc = LiquidityClassifier(volume_period=5)
        mc = MarketClassifier(
            trend_classifier=tc, volatility_classifier=vc, liquidity_classifier=lc
        )
        ds = _make_dataset()
        result = asyncio.run(mc.classify(ds))
        assert result.regime in (
            MarketRegime.TRENDING,
            MarketRegime.RANGING,
            MarketRegime.HIGH_VOLATILITY,
            MarketRegime.LOW_LIQUIDITY,
            MarketRegime.UNKNOWN,
        )
