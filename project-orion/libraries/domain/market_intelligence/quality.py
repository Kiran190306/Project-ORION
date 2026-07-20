"""Price quality scoring engine for multi-provider market data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum


class PriceQuality(StrEnum):
    """Classification of price data quality."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class QualityScorer:
    """Scores the quality of price data from providers.

    Evaluates based on:
    - Spread quality relative to instrument
    - Data freshness
    - Provider consistency
    - Price reasonability
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def score_spread(
        self,
        spread: Decimal,
        typical_spread: Decimal,
    ) -> tuple[PriceQuality, float]:
        """Score spread quality compared to typical spread.

        Returns:
            Tuple of (quality_level, score_0_to_1).
        """
        if typical_spread <= Decimal("0"):
            return PriceQuality.GOOD, 0.7

        ratio = float(spread / typical_spread)

        if ratio <= 1.0:
            return PriceQuality.EXCELLENT, 1.0
        elif ratio <= 2.0:
            return PriceQuality.GOOD, 0.8
        elif ratio <= 3.0:
            return PriceQuality.FAIR, 0.6
        elif ratio <= 5.0:
            return PriceQuality.POOR, 0.3
        else:
            return PriceQuality.UNUSABLE, 0.0

    async def score_freshness(
        self,
        timestamp: datetime,
        max_age_seconds: float = 5.0,
    ) -> tuple[PriceQuality, float]:
        """Score data freshness based on age.

        Returns:
            Tuple of (quality_level, score_0_to_1).
        """
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()

        if age <= 0.0:
            return PriceQuality.EXCELLENT, 1.0
        elif age <= max_age_seconds * 0.1:
            return PriceQuality.EXCELLENT, 1.0
        elif age <= max_age_seconds * 0.25:
            return PriceQuality.GOOD, 0.8
        elif age <= max_age_seconds * 0.5:
            return PriceQuality.FAIR, 0.6
        elif age <= max_age_seconds * 0.75:
            return PriceQuality.POOR, 0.3
        else:
            return PriceQuality.UNUSABLE, 0.0

    async def score_consistency(
        self,
        bid: Decimal,
        ask: Decimal,
    ) -> tuple[PriceQuality, float]:
        """Score the internal consistency of a bid-ask pair."""
        if bid <= Decimal("0") or ask <= Decimal("0"):
            return PriceQuality.UNUSABLE, 0.0
        if bid >= ask:
            return PriceQuality.UNUSABLE, 0.0

        spread = ask - bid
        mid = (bid + ask) / Decimal("2")

        if mid <= Decimal("0"):
            return PriceQuality.UNUSABLE, 0.0

        spread_pct = float(spread / mid) * 100.0

        if spread_pct <= 0.01:
            return PriceQuality.EXCELLENT, 1.0
        elif spread_pct <= 0.05:
            return PriceQuality.GOOD, 0.8
        elif spread_pct <= 0.1:
            return PriceQuality.FAIR, 0.6
        elif spread_pct <= 0.5:
            return PriceQuality.POOR, 0.3
        else:
            return PriceQuality.UNUSABLE, 0.0

    async def composite_score(
        self,
        spread_quality: tuple[PriceQuality, float],
        freshness: tuple[PriceQuality, float],
        consistency: tuple[PriceQuality, float],
        weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
    ) -> tuple[PriceQuality, float]:
        """Compute a weighted composite quality score."""
        score = (
            spread_quality[1] * weights[0] + freshness[1] * weights[1] + consistency[1] * weights[2]
        )

        if score >= 0.9:
            return PriceQuality.EXCELLENT, round(score, 4)
        elif score >= 0.7:
            return PriceQuality.GOOD, round(score, 4)
        elif score >= 0.5:
            return PriceQuality.FAIR, round(score, 4)
        elif score >= 0.2:
            return PriceQuality.POOR, round(score, 4)
        else:
            return PriceQuality.UNUSABLE, round(score, 4)
