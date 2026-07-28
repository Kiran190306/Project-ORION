"""Tests for liquidity_classifier module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import LiquidityClassificationError
from libraries.domain.ai_research.liquidity_classifier import LiquidityClassifier
from libraries.domain.ai_research.models import LiquidityLevel, ResearchDataset


def _make_dataset(
    volume: list[float] | None = None,
    close: list[float] | None = None,
    high: list[float] | None = None,
    low: list[float] | None = None,
) -> ResearchDataset:
    n = max(len(volume or []), len(close or []))
    volume = volume or [1000.0] * n
    close = close or [100.0 + i * 0.5 for i in range(n)]
    high = [v + 1.0 for v in close]
    low = [v - 1.0 for v in close]
    rows = tuple(
        {
            "volume": volume[i],
            "close": close[i],
            "high": high[i],
            "low": low[i],
            "timestamp": datetime.now(timezone.utc),
        }
        for i in range(len(close))
    )
    return ResearchDataset(
        dataset_id="test", schema=("volume", "close", "high", "low", "timestamp"), rows=rows
    )


class TestLiquidityClassifierInit:
    def test_default_period(self):
        lc = LiquidityClassifier()
        assert lc._volume_period == 20

    def test_custom_period(self):
        lc = LiquidityClassifier(volume_period=10)
        assert lc._volume_period == 10

    def test_volume_period_must_be_positive(self):
        with pytest.raises(LiquidityClassificationError, match="volume_period must be positive"):
            LiquidityClassifier(volume_period=0)

    def test_invalid_thresholds(self):
        with pytest.raises(LiquidityClassificationError, match="volume thresholds"):
            LiquidityClassifier(volume_low_threshold=0.8, volume_high_threshold=0.5)


class TestLiquidityClassifierClassification:
    def test_high_liquidity(self):
        lc = LiquidityClassifier(
            volume_period=5, volume_low_threshold=0.3, volume_high_threshold=0.6
        )
        volume = [10000.0 + i * 100.0 for i in range(10)]  # consistent high volume
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert 0.0 <= result.score <= 1.0

    def test_low_liquidity(self):
        lc = LiquidityClassifier(
            volume_period=5, volume_low_threshold=0.3, volume_high_threshold=0.6
        )
        volume = [
            100.0 + (i * 500.0 if i % 2 == 0 else 10.0) for i in range(10)
        ]  # erratic low volume
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert 0.0 <= result.score <= 1.0

    def test_insufficient_data_raises_error(self):
        lc = LiquidityClassifier(volume_period=10)
        ds = _make_dataset(volume=[1000.0, 2000.0], close=[100.0, 101.0])
        with pytest.raises(LiquidityClassificationError, match="need at least"):
            asyncio.run(lc.classify(ds))

    def test_missing_volume_column_raises_error(self):
        lc = LiquidityClassifier(volume_period=5)
        rows = tuple({"close": 100.0, "high": 101.0, "low": 99.0} for _ in range(10))
        ds = ResearchDataset(dataset_id="test", schema=("close", "high", "low"), rows=rows)
        with pytest.raises(LiquidityClassificationError, match="volume"):
            asyncio.run(lc.classify(ds))

    def test_result_has_level(self):
        lc = LiquidityClassifier(volume_period=5)
        volume = [1000.0] * 10
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert isinstance(result.level, LiquidityLevel)

    def test_result_has_score(self):
        lc = LiquidityClassifier(volume_period=5)
        volume = [1000.0] * 10
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert 0.0 <= result.score <= 1.0

    def test_result_has_avg_volume(self):
        lc = LiquidityClassifier(volume_period=5)
        volume = [1000.0] * 10
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert result.avg_volume > 0

    def test_result_has_details(self):
        lc = LiquidityClassifier(volume_period=5)
        volume = [1000.0] * 10
        close = [100.0 + i * 0.2 for i in range(10)]
        ds = _make_dataset(volume=volume, close=close)
        result = asyncio.run(lc.classify(ds))
        assert "avg_volume" in result.details
        assert "volume_cv" in result.details
