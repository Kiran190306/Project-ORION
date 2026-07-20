"""Tests for ProviderRankingEngine."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.market_intelligence.provider_ranking import (
    ProviderRankingEngine,
    RankingCriteria,
)


class TestProviderRankingEngine:
    def test_rank_empty_returns_empty(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            ranked = await engine.rank()
            assert ranked == []

        asyncio.run(exercise())

    def test_rank_single_provider(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            await engine.record_latency("mt5", 10.0)
            await engine.record_spread("mt5", 0.0002)
            await engine.record_uptime("mt5")

            ranked = await engine.rank(providers=["mt5"])
            assert len(ranked) == 1
            assert ranked[0].provider == "mt5"
            assert ranked[0].rank == 1

        asyncio.run(exercise())

    def test_rank_multiple_providers(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            # mt5: low latency, tight spread
            await engine.record_latency("mt5", 5.0)
            await engine.record_spread("mt5", 0.0001)
            await engine.record_uptime("mt5")

            # oanda: high latency, wide spread
            await engine.record_latency("oanda", 50.0)
            await engine.record_spread("oanda", 0.001)
            await engine.record_uptime("oanda")

            ranked = await engine.rank()
            assert len(ranked) == 2
            assert ranked[0].provider == "mt5"  # mt5 should rank higher

        asyncio.run(exercise())

    def test_rank_by_latency(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            await engine.record_latency("mt5", 5.0)
            await engine.record_latency("oanda", 50.0)
            await engine.record_uptime("mt5")
            await engine.record_uptime("oanda")

            ranked = await engine.rank(criteria=RankingCriteria.LATENCY)
            assert len(ranked) == 2
            assert ranked[0].provider == "mt5"
            assert ranked[0].latency_score > ranked[1].latency_score

        asyncio.run(exercise())

    def test_get_best_provider(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            await engine.record_latency("mt5", 5.0)
            await engine.record_latency("oanda", 50.0)
            await engine.record_uptime("mt5")
            await engine.record_uptime("oanda")

            best = await engine.get_best_provider()
            assert best == "mt5"

        asyncio.run(exercise())

    def test_validates_weights(self) -> None:
        with pytest.raises(ValueError):
            ProviderRankingEngine(
                latency_weight=1.0,
                uptime_weight=1.0,
                spread_weight=0.0,
                stability_weight=0.0,
            )

    def test_clear(self) -> None:
        async def exercise() -> None:
            engine = ProviderRankingEngine()
            await engine.record_latency("mt5", 10.0)
            await engine.clear()
            ranked = await engine.rank()
            assert ranked == []

        asyncio.run(exercise())
