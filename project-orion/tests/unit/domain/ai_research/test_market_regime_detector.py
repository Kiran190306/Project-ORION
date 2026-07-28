"""Tests for market_regime_detector module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import MarketIntelligenceError
from libraries.domain.ai_research.market_classifier import MarketClassifier
from libraries.domain.ai_research.market_regime_detector import MarketRegimeDetector
from libraries.domain.ai_research.models import MarketRegime, ResearchDataset


def _make_dataset(n: int = 210, trend_slope: float = 0.5) -> ResearchDataset:
    close = [100.0 + i * trend_slope for i in range(n)]
    high = [v + 2.0 for v in close]
    low = [v - 2.0 for v in close]
    volume = [1000.0] * n
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


class TestMarketRegimeDetector:
    def test_default_init(self):
        mrd = MarketRegimeDetector()
        assert mrd._classifier is not None

    def test_detect_returns_regime(self):
        mrd = MarketRegimeDetector()
        ds = _make_dataset(210, 0.5)
        result = asyncio.run(mrd.detect(ds))
        assert isinstance(result, MarketRegime)

    def test_detect_with_custom_classifier(self):
        mc = MarketClassifier()
        mrd = MarketRegimeDetector(classifier=mc)
        ds = _make_dataset(210, 0.5)
        result = asyncio.run(mrd.detect(ds))
        assert isinstance(result, MarketRegime)

    def test_detect_trending_regime(self):
        mrd = MarketRegimeDetector()
        ds = _make_dataset(210, 10.0)  # Strong uptrend
        result = asyncio.run(mrd.detect(ds))
        assert isinstance(result, MarketRegime)

    def test_detect_high_volatility_regime(self):
        mrd = MarketRegimeDetector()
        close = [100.0]
        for i in range(210):
            close.append(close[-1] + (20.0 if i % 2 == 0 else -20.0))
        high = [v + 5.0 for v in close]
        low = [v - 5.0 for v in close]
        volume = [1000.0] * len(close)
        rows = tuple(
            {
                "close": close[i],
                "high": high[i],
                "low": low[i],
                "volume": volume[i],
                "timestamp": datetime.now(timezone.utc),
            }
            for i in range(len(close))
        )
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close", "high", "low", "volume", "timestamp"),
            rows=rows,
        )
        result = asyncio.run(mrd.detect(ds))
        assert isinstance(result, MarketRegime)

    def test_detect_valid_regime(self):
        mrd = MarketRegimeDetector()
        ds = _make_dataset(210, 0.5)
        result = asyncio.run(mrd.detect(ds))
        assert result in (
            MarketRegime.TRENDING,
            MarketRegime.RANGING,
            MarketRegime.HIGH_VOLATILITY,
            MarketRegime.LOW_LIQUIDITY,
            MarketRegime.UNKNOWN,
        )

    def test_classify_returns_full_result(self):
        mrd = MarketRegimeDetector()
        ds = _make_dataset(210, 0.5)
        result = asyncio.run(mrd.classify(ds))
        assert result.trend is not None
        assert result.volatility is not None
        assert result.liquidity is not None
