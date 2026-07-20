"""Tests for LiquidityAnalyzer."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.liquidity import (
    LiquidityAnalyzer,
    SpreadQuality,
)
from libraries.domain.market_intelligence.models import ProviderTickData


class TestLiquidityAnalyzer:
    def test_initial_analysis_returns_illiquid(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer()
            metrics = await analyzer.analyze("EUR/USD")
            assert metrics.spread_quality == SpreadQuality.ILLIQUID
            assert metrics.active_provider_count == 0

        asyncio.run(exercise())

    def test_excellent_spread_quality(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer(excellent_spread_pips=2.0)
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1051"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            metrics = await analyzer.analyze("EUR/USD")
            assert metrics.spread_quality == SpreadQuality.EXCELLENT
            assert metrics.active_provider_count == 1

        asyncio.run(exercise())

    def test_illiquid_spread_quality(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer(excellent_spread_pips=0.1, fair_spread_pips=0.2)
            # Very wide spread
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.10"),
                    ask=Decimal("1.20"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            metrics = await analyzer.analyze("EUR/USD")
            assert metrics.spread_quality == SpreadQuality.ILLIQUID

        asyncio.run(exercise())

    def test_multiple_providers(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer(excellent_spread_pips=2.0)
            now = datetime.now(timezone.utc)

            for provider in ["mt5", "oanda", "binance"]:
                await analyzer.record_tick(
                    ProviderTickData(
                        provider=provider,
                        symbol="EUR/USD",
                        bid=Decimal("1.1050"),
                        ask=Decimal("1.1051"),
                        timestamp=now,
                    )
                )

            metrics = await analyzer.analyze("EUR/USD")
            assert metrics.active_provider_count == 3
            assert len(metrics.provider_confidence_scores) == 3

        asyncio.run(exercise())

    def test_provider_confidence(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer(excellent_spread_pips=2.0)
            now = datetime.now(timezone.utc)

            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.10"),
                    ask=Decimal("1.11"),
                    timestamp=now,
                )
            )

            confidence = await analyzer.get_provider_confidence("mt5", "EUR/USD")
            assert confidence is not None
            assert confidence.provider == "mt5"
            assert confidence.score > 0

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            analyzer = LiquidityAnalyzer()
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.10"),
                    ask=Decimal("1.11"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            await analyzer.clear()
            metrics = await analyzer.analyze("EUR/USD")
            assert metrics.active_provider_count == 0

        asyncio.run(exercise())
