"""Tests for trend_classifier module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import TrendClassificationError
from libraries.domain.ai_research.models import ResearchDataset, TrendDirection
from libraries.domain.ai_research.trend_classifier import TrendClassifier


def _make_dataset(
    close: list[float],
    high: list[float] | None = None,
    low: list[float] | None = None,
    row_count: int | None = None,
) -> ResearchDataset:
    n = row_count or len(close)
    close = close or [100.0] * n
    high = high or [v + 1.0 for v in close]
    low = low or [v - 1.0 for v in close]
    rows = tuple(
        {
            "close": close[i],
            "high": high[i],
            "low": low[i],
            "timestamp": datetime.now(timezone.utc),
        }
        for i in range(len(close))
    )
    return ResearchDataset(
        dataset_id="test", schema=("close", "high", "low", "timestamp"), rows=rows
    )


class TestTrendClassifierInit:
    def test_default_periods(self):
        tc = TrendClassifier()
        assert tc._fast_period == 50
        assert tc._slow_period == 200

    def test_custom_periods(self):
        tc = TrendClassifier(fast_period=10, slow_period=30)
        assert tc._fast_period == 10
        assert tc._slow_period == 30

    def test_fast_period_not_less_than_slow_raises_error(self):
        with pytest.raises(TrendClassificationError, match="fast_period"):
            TrendClassifier(fast_period=20, slow_period=10)

    def test_zero_period_raises_error(self):
        with pytest.raises(TrendClassificationError, match="positive"):
            TrendClassifier(fast_period=0, slow_period=10)


class TestTrendClassifierClassification:
    def test_bull_trend(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 + i * 2.0 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert result.direction == TrendDirection.BULL
        assert result.strength > 0

    def test_bear_trend(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 - i * 2.0 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert result.direction == TrendDirection.BEAR
        assert result.strength > 0

    def test_sideways_trend(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 + (i % 3 - 1) * 0.5 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert isinstance(result.direction, TrendDirection)
        assert result.strength >= 0

    def test_result_has_strength(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 + i * 2.0 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert 0.0 <= result.strength <= 1.0

    def test_result_has_slope(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 + i * 2.0 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert result.slope != 0.0

    def test_result_has_details(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        close = [100.0 + i * 2.0 for i in range(30)]
        ds = _make_dataset(close=close)
        result = asyncio.run(tc.classify(ds))
        assert "fast_sma" in result.details
        assert "slow_sma" in result.details
        assert "current_price" in result.details

    def test_insufficient_data_raises_error(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        ds = _make_dataset(close=[100.0, 101.0], row_count=2)
        with pytest.raises(TrendClassificationError):
            asyncio.run(tc.classify(ds))

    def test_missing_close_column_raises_error(self):
        tc = TrendClassifier(fast_period=3, slow_period=10)
        ds = ResearchDataset(
            dataset_id="test",
            schema=("price",),
            rows=({"price": 100.0}, {"price": 101.0}),
        )
        with pytest.raises(TrendClassificationError):
            asyncio.run(tc.classify(ds))
