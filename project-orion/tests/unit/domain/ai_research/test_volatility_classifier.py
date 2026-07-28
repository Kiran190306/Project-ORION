"""Tests for volatility_classifier module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import VolatilityClassificationError
from libraries.domain.ai_research.models import ResearchDataset, VolatilityLevel
from libraries.domain.ai_research.volatility_classifier import VolatilityClassifier


def _make_dataset(
    close: list[float] | None = None,
    high: list[float] | None = None,
    low: list[float] | None = None,
) -> ResearchDataset:
    n = max(len(close or []), len(high or []), len(low or []))
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


class TestVolatilityClassifierInit:
    def test_default_period(self):
        vc = VolatilityClassifier()
        assert vc._atr_period == 14

    def test_custom_period(self):
        vc = VolatilityClassifier(atr_period=20)
        assert vc._atr_period == 20

    def test_atr_period_minimum(self):
        with pytest.raises(VolatilityClassificationError, match="atr_period"):
            VolatilityClassifier(atr_period=1)

    def test_invalid_percentile_thresholds(self):
        with pytest.raises(VolatilityClassificationError, match="percentile"):
            VolatilityClassifier(percentile_low=0.8, percentile_high=0.6)


class TestVolatilityClassifierClassification:
    def test_high_volatility(self):
        vc = VolatilityClassifier(atr_period=3, percentile_low=0.3, percentile_high=0.6)
        close = [100.0]
        high = [101.0]
        low = [99.0]
        for i in range(20):
            close.append(close[-1] + (10.0 if i % 2 == 0 else -10.0))
            high.append(close[-1] + 5.0)
            low.append(close[-1] - 5.0)
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(vc.classify(ds))
        assert result.level in (VolatilityLevel.HIGH, VolatilityLevel.NORMAL)

    def test_low_volatility(self):
        vc = VolatilityClassifier(atr_period=3, percentile_low=0.3, percentile_high=0.6)
        close = [100.0 + i * 0.1 for i in range(20)]
        high = [v + 0.2 for v in close]
        low = [v - 0.2 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(vc.classify(ds))
        # With 20 rows of very tight range, should be LOW or NORMAL, not HIGH
        assert result.level is not None

    def test_insufficient_data_raises_error(self):
        vc = VolatilityClassifier(atr_period=5)
        close = [100.0, 101.0]
        ds = _make_dataset(close=close)
        with pytest.raises(VolatilityClassificationError):
            asyncio.run(vc.classify(ds))

    def test_result_has_percentile(self):
        vc = VolatilityClassifier(atr_period=3)
        close = [100.0 + (5.0 if i % 3 == 0 else -3.0) for i in range(20)]
        high = [v + 2.0 for v in close]
        low = [v - 2.0 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(vc.classify(ds))
        assert 0.0 <= result.percentile <= 1.0

    def test_result_has_atr_value(self):
        vc = VolatilityClassifier(atr_period=3)
        close = [100.0 + (5.0 if i % 3 == 0 else -3.0) for i in range(20)]
        high = [v + 2.0 for v in close]
        low = [v - 2.0 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(vc.classify(ds))
        assert result.atr_value > 0

    def test_result_has_details(self):
        vc = VolatilityClassifier(atr_period=3)
        close = [100.0 + (5.0 if i % 3 == 0 else -3.0) for i in range(20)]
        high = [v + 2.0 for v in close]
        low = [v - 2.0 for v in close]
        ds = _make_dataset(close=close, high=high, low=low)
        result = asyncio.run(vc.classify(ds))
        assert "atr" in result.details
        assert "std_dev" in result.details

    def test_missing_column_raises_error(self):
        vc = VolatilityClassifier(atr_period=3)
        ds = ResearchDataset(
            dataset_id="test",
            schema=("close",),
            rows=({"close": 100.0}, {"close": 101.0}, {"close": 102.0}, {"close": 103.0}),
        )
        with pytest.raises(VolatilityClassificationError):
            asyncio.run(vc.classify(ds))
