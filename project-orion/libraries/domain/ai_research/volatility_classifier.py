"""Volatility classifier for market intelligence.

Classifies market volatility level (HIGH, LOW, NORMAL) using
ATR and standard deviation analysis on historical price data.

Consumes historical market data only. No execution logic.
"""

from __future__ import annotations

from math import sqrt

from libraries.domain.ai_research.exceptions import VolatilityClassificationError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    VolatilityClassificationResult,
    VolatilityLevel,
)


class VolatilityClassifier:
    """Classifies market volatility using ATR and standard deviation.

    Uses:
    - Average True Range (ATR) for absolute volatility
    - Price return standard deviation for relative volatility
    - Percentile ranking against historical volatility
    """

    def __init__(
        self, atr_period: int = 14, percentile_low: float = 0.3, percentile_high: float = 0.7
    ) -> None:
        if atr_period < 2:
            raise VolatilityClassificationError("atr_period must be at least 2")
        if not 0.0 < percentile_low < percentile_high < 1.0:
            raise VolatilityClassificationError(
                "percentile thresholds must satisfy 0 < low < high < 1"
            )
        self._atr_period = atr_period
        self._percentile_low = percentile_low
        self._percentile_high = percentile_high

    async def classify(self, dataset: ResearchDataset) -> VolatilityClassificationResult:
        """Classify volatility level from a research dataset.

        Args:
            dataset: Historical market data with 'close', 'high', 'low' columns.

        Returns:
            VolatilityClassificationResult with level and percentile.

        Raises:
            VolatilityClassificationError: If dataset has insufficient data.
        """
        if dataset.row_count < self._atr_period + 1:
            raise VolatilityClassificationError(
                f"dataset has {dataset.row_count} rows, need at least {self._atr_period + 1}"
            )

        close = self._extract_column(dataset, "close")
        high = self._extract_column(dataset, "high")
        low = self._extract_column(dataset, "low")

        atr_values = self._atr(high, low, close, self._atr_period)
        current_atr = atr_values[-1] if atr_values else 0.0

        # Calculate daily returns for volatility analysis
        returns = [close[i] / close[i - 1] - 1.0 for i in range(1, len(close))]
        std_dev = sqrt(sum(r * r for r in returns) / len(returns)) if returns else 0.0

        # Calculate percentile of current ATR within historical range
        sorted_atr = sorted(atr_values)
        n = len(sorted_atr)
        if n > 1:
            rank = sum(1 for v in sorted_atr if v <= current_atr) - 1
            percentile = max(0.0, min(1.0, rank / (n - 1)))
        else:
            percentile = 0.5

        # Determine level based on percentile thresholds
        if percentile >= self._percentile_high:
            level = VolatilityLevel.HIGH
        elif percentile <= self._percentile_low:
            level = VolatilityLevel.LOW
        else:
            level = VolatilityLevel.NORMAL

        details: dict[str, float] = {
            "atr": round(current_atr, 6),
            "std_dev": round(std_dev, 6),
            "annualized_volatility": round(std_dev * sqrt(252), 6),
        }

        return VolatilityClassificationResult(
            level=level,
            percentile=round(percentile, 4),
            atr_value=round(current_atr, 6),
            details=details,
        )

    @staticmethod
    def _extract_column(dataset: ResearchDataset, column: str) -> list[float]:
        try:
            return [float(row[column]) for row in dataset.rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise VolatilityClassificationError(
                f"column '{column}' must contain numeric values"
            ) from exc

    @staticmethod
    def _atr(high: list[float], low: list[float], close: list[float], period: int) -> list[float]:
        if len(high) < 2:
            return []
        true_ranges: list[float] = [high[0] - low[0]]
        for i in range(1, len(close)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
            true_ranges.append(tr)
        # SMA of true ranges
        return [
            sum(true_ranges[max(0, i - period + 1) : i + 1]) / min(i + 1, period)
            for i in range(len(true_ranges))
        ]
