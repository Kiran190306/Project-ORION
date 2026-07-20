"""Tests for QualityScorer."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.quality import PriceQuality, QualityScorer


class TestQualityScorer:
    def test_score_spread_excellent(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_spread(
                spread=Decimal("0.0001"),
                typical_spread=Decimal("0.0002"),
            )
            assert quality == PriceQuality.EXCELLENT
            assert score == 1.0

        asyncio.run(exercise())

    def test_score_spread_unusable(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_spread(
                spread=Decimal("0.005"),
                typical_spread=Decimal("0.0002"),
            )
            assert quality == PriceQuality.UNUSABLE
            assert score == 0.0

        asyncio.run(exercise())

    def test_freshness_excellent(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_freshness(
                timestamp=datetime.now(timezone.utc),
                max_age_seconds=5.0,
            )
            assert quality == PriceQuality.EXCELLENT

        asyncio.run(exercise())

    def test_freshness_unusable(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_freshness(
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=10),
                max_age_seconds=5.0,
            )
            assert quality == PriceQuality.UNUSABLE
            assert score == 0.0

        asyncio.run(exercise())

    def test_consistency_excellent(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_consistency(
                bid=Decimal("1.1050"),
                ask=Decimal("1.1051"),
            )
            assert quality in (PriceQuality.EXCELLENT, PriceQuality.GOOD)

        asyncio.run(exercise())

    def test_consistency_invalid(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_consistency(
                bid=Decimal("1.10"),
                ask=Decimal("1.09"),  # bid > ask
            )
            assert quality == PriceQuality.UNUSABLE
            assert score == 0.0

        asyncio.run(exercise())

    def test_consistency_negative_prices(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.score_consistency(
                bid=Decimal("0"),
                ask=Decimal("1.10"),
            )
            assert quality == PriceQuality.UNUSABLE

        asyncio.run(exercise())

    def test_composite_score(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.composite_score(
                spread_quality=(PriceQuality.GOOD, 0.8),
                freshness=(PriceQuality.GOOD, 0.8),
                consistency=(PriceQuality.GOOD, 0.8),
            )
            assert score >= 0.7
            assert quality in (PriceQuality.GOOD, PriceQuality.EXCELLENT)

        asyncio.run(exercise())

    def test_composite_score_poor(self) -> None:
        async def exercise() -> None:
            scorer = QualityScorer()
            quality, score = await scorer.composite_score(
                spread_quality=(PriceQuality.UNUSABLE, 0.0),
                freshness=(PriceQuality.UNUSABLE, 0.0),
                consistency=(PriceQuality.UNUSABLE, 0.0),
            )
            assert quality == PriceQuality.UNUSABLE
            assert score == 0.0

        asyncio.run(exercise())
