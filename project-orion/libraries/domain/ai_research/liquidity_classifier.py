"""Liquidity classifier for market intelligence.

Classifies market liquidity level (HIGH, LOW, NORMAL) using
volume analysis, spread estimation, and trade frequency.

Consumes historical market data only. No execution logic.
"""

from __future__ import annotations

from math import sqrt

from libraries.domain.ai_research.exceptions import LiquidityClassificationError
from libraries.domain.ai_research.models import (
    LiquidityClassificationResult,
    LiquidityLevel,
    ResearchDataset,
)


class LiquidityClassifier:
    """Classifies market liquidity using volume and spread analysis.

    Uses:
    - Average volume relative to historical volume
    - Price impact estimation (volume vs price change)
    - Trade frequency estimation
    """

    def __init__(
        self,
        volume_period: int = 20,
        volume_low_threshold: float = 0.3,
        volume_high_threshold: float = 0.7,
    ) -> None:
        if volume_period < 1:
            raise LiquidityClassificationError("volume_period must be positive")
        if not 0.0 < volume_low_threshold < volume_high_threshold < 1.0:
            raise LiquidityClassificationError("volume thresholds must satisfy 0 < low < high < 1")
        self._volume_period = volume_period
        self._volume_low_threshold = volume_low_threshold
        self._volume_high_threshold = volume_high_threshold

    async def classify(self, dataset: ResearchDataset) -> LiquidityClassificationResult:
        """Classify liquidity level from a research dataset.

        Args:
            dataset: Historical market data with 'volume', 'close', 'high', 'low' columns.

        Returns:
            LiquidityClassificationResult with level and score.

        Raises:
            LiquidityClassificationError: If dataset has insufficient data.
        """
        if dataset.row_count < self._volume_period:
            raise LiquidityClassificationError(
                f"dataset has {dataset.row_count} rows, need at least {self._volume_period}"
            )

        try:
            volume = [float(row["volume"]) for row in dataset.rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise LiquidityClassificationError(
                "dataset must contain a numeric 'volume' column"
            ) from exc

        close = self._extract_column(dataset, "close")
        high = self._extract_column(dataset, "high")
        low = self._extract_column(dataset, "low")

        # Average volume over period
        recent_volume = volume[-self._volume_period :]
        avg_volume = sum(recent_volume) / len(recent_volume)

        # Volume consistency (low std dev / mean = more consistent)
        volume_mean = avg_volume
        volume_std = sqrt(sum((v - volume_mean) ** 2 for v in recent_volume) / len(recent_volume))
        volume_cv = volume_std / volume_mean if volume_mean > 0 else 1.0

        # Price impact: average range / volume ratio as liquidity proxy
        ranges = [(high[i] - low[i]) / close[i] if close[i] != 0 else 0 for i in range(len(close))]
        avg_range = sum(ranges[-self._volume_period :]) / self._volume_period
        impact_ratio = avg_range / (avg_volume / 1_000_000) if avg_volume > 0 else 1.0

        # Composite liquidity score (0-1, higher = more liquid)
        # Normalized volume score: z-score -> percentile approximation
        volume_z = (avg_volume - sum(volume) / len(volume)) / (
            sqrt(sum((v - sum(volume) / len(volume)) ** 2 for v in volume) / len(volume)) + 1e-10
        )
        volume_score = 1.0 / (1.0 + abs(volume_z))

        # Coefficient of variation score (lower CV = more consistent = more liquid)
        cv_score = max(0.0, 1.0 - volume_cv)

        # Impact score (lower impact = more liquid)
        impact_score = max(0.0, min(1.0, 1.0 - impact_ratio / 10.0))

        # Weighted composite
        score = volume_score * 0.4 + cv_score * 0.3 + impact_score * 0.3
        score = max(0.0, min(1.0, score))

        # Determine level based on score
        if score >= self._volume_high_threshold:
            level = LiquidityLevel.HIGH
        elif score <= self._volume_low_threshold:
            level = LiquidityLevel.LOW
        else:
            level = LiquidityLevel.NORMAL

        details: dict[str, float] = {
            "avg_volume": round(avg_volume, 2),
            "volume_cv": round(volume_cv, 4),
            "impact_ratio": round(impact_ratio, 6),
            "volume_score": round(volume_score, 4),
            "cv_score": round(cv_score, 4),
            "impact_score": round(impact_score, 4),
        }

        return LiquidityClassificationResult(
            level=level,
            score=round(score, 4),
            avg_volume=round(avg_volume, 2),
            details=details,
        )

    @staticmethod
    def _extract_column(dataset: ResearchDataset, column: str) -> list[float]:
        try:
            return [float(row[column]) for row in dataset.rows]
        except (KeyError, TypeError, ValueError) as exc:
            raise LiquidityClassificationError(
                f"column '{column}' must contain numeric values"
            ) from exc
