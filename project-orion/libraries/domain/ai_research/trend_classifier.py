"""Trend classifier for market intelligence.

Classifies market trend direction (BULL, BEAR, SIDEWAYS) using
moving average crossovers and linear regression slope analysis.

Consumes historical market data only. No execution logic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import sqrt

from libraries.domain.ai_research.exceptions import TrendClassificationError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    TrendClassificationResult,
    TrendDirection,
)


class TrendClassifier:
    """Classifies market trend using moving averages and slope analysis.

    Uses:
    - SMA(50) vs SMA(200) crossovers for primary trend direction
    - Linear regression slope for trend strength
    - Price vs SMA position for confirmation
    """

    def __init__(self, fast_period: int = 50, slow_period: int = 200) -> None:
        if fast_period < 1 or slow_period < 1:
            raise TrendClassificationError("periods must be positive")
        if fast_period >= slow_period:
            raise TrendClassificationError("fast_period must be less than slow_period")
        self._fast_period = fast_period
        self._slow_period = slow_period

    async def classify(self, dataset: ResearchDataset) -> TrendClassificationResult:
        """Classify the trend direction from a research dataset.

        Args:
            dataset: Historical market data with 'close' column.

        Returns:
            TrendClassificationResult with direction and strength.

        Raises:
            TrendClassificationError: If dataset has insufficient data.
        """
        if dataset.row_count < self._slow_period:
            raise TrendClassificationError(
                f"dataset has {dataset.row_count} rows, need at least {self._slow_period}"
            )

        close = self._extract_column(dataset, "close")
        fast_sma = self._sma(close, self._fast_period)
        slow_sma = self._sma(close, self._slow_period)

        # Use most recent values for comparison
        current_fast = fast_sma[-1]
        current_slow = slow_sma[-1]
        current_price = close[-1]

        # Calculate slope of linear regression on last 20 periods
        lookback = min(20, len(close))
        slope = self._linear_slope(close[-lookback:])

        # Determine direction
        if current_fast > current_slow and current_price > current_fast:
            direction = TrendDirection.BULL
            strength = min(1.0, abs(slope) * 100.0)
        elif current_fast < current_slow and current_price < current_fast:
            direction = TrendDirection.BEAR
            strength = min(1.0, abs(slope) * 100.0)
        else:
            direction = TrendDirection.SIDEWAYS
            strength = max(0.0, 1.0 - abs(slope) * 100.0)

        details: dict[str, float] = {
            "fast_sma": current_fast,
            "slow_sma": current_slow,
            "current_price": current_price,
            "slope": slope,
            "price_above_fast": 1.0 if current_price > current_fast else 0.0,
        }

        return TrendClassificationResult(
            direction=direction,
            strength=round(strength, 4),
            slope=round(slope, 6),
            details=details,
        )

    @staticmethod
    def _extract_column(dataset: ResearchDataset, column: str) -> list[float]:
        try:
            return [float(row[column]) for row in dataset.rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise TrendClassificationError(
                f"column '{column}' must contain numeric values"
            ) from exc

    @staticmethod
    def _sma(values: Sequence[float], period: int) -> list[float]:
        return [
            sum(values[max(0, i - period + 1) : i + 1]) / min(i + 1, period)
            for i in range(len(values))
        ]

    @staticmethod
    def _linear_slope(values: Sequence[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0
