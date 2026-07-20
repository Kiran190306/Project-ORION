"""Tests for SpreadAnalyzer."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market_intelligence.models import ProviderTickData
from libraries.domain.market_intelligence.spread_analyzer import SpreadAnalyzer


class TestSpreadAnalyzer:
    def test_initial_analysis(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer()
            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.sample_count == 0
            assert analysis.best_provider is None

        asyncio.run(exercise())

    def test_single_tick_analysis(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer()
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1052"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.sample_count == 1
            assert analysis.average_spread is not None

        asyncio.run(exercise())

    def test_best_and_worst_provider(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer()
            now = datetime.now(timezone.utc)

            # mt5 has tight spread
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1051"),
                    timestamp=now,
                )
            )
            # binance has wide spread
            await analyzer.record_tick(
                ProviderTickData(
                    provider="binance",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1060"),
                    timestamp=now,
                )
            )

            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.best_provider == "mt5"
            assert analysis.worst_provider == "binance"

        asyncio.run(exercise())

    def test_spread_in_pips(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer(pip_size=Decimal("0.0001"))
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1052"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.spread_pips == 2.0  # 2 pips

        asyncio.run(exercise())

    def test_multiple_ticks_same_provider(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer(window_size=10)
            now = datetime.now(timezone.utc)

            for i in range(5):
                await analyzer.record_tick(
                    ProviderTickData(
                        provider="mt5",
                        symbol="EUR/USD",
                        bid=Decimal("1.1050"),
                        ask=Decimal(str(1.1052 + i * 0.0001)),
                        timestamp=now,
                    )
                )

            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.sample_count == 5
            assert analysis.min_spread <= analysis.max_spread

        asyncio.run(exercise())

    def test_get_provider_spread(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer()
            await analyzer.record_tick(
                ProviderTickData(
                    provider="mt5",
                    symbol="EUR/USD",
                    bid=Decimal("1.1050"),
                    ask=Decimal("1.1052"),
                    timestamp=datetime.now(timezone.utc),
                )
            )
            spread = await analyzer.get_provider_spread("mt5", "EUR/USD")
            assert spread is not None
            assert spread > 0

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            analyzer = SpreadAnalyzer()
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
            analysis = await analyzer.analyze("EUR/USD")
            assert analysis.sample_count == 0

        asyncio.run(exercise())
