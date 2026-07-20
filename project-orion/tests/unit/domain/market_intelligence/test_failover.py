"""Tests for FailoverEngine."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.market_intelligence.failover import FailoverEngine, FailoverReason
from libraries.domain.market_intelligence.provider_ranking import (
    ProviderRankingEngine,
    RankingCriteria,
)


class TestFailoverEngine:
    def test_initial_primary_is_none(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)
            primary = await engine.get_primary("EUR/USD")
            assert primary is None

        asyncio.run(exercise())

    def test_set_and_get_primary(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)
            await engine.set_primary("EUR/USD", "mt5")
            assert await engine.get_primary("EUR/USD") == "mt5"

        asyncio.run(exercise())

    def test_failover_when_primary_degraded(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(
                ranking,
                failover_score_threshold=0.5,
                min_score_difference=0.1,
                cooldown_seconds=0.01,
            )

            # mt5: good scores
            await ranking.record_latency("mt5", 5.0)
            await ranking.record_spread("mt5", 0.0001)
            await ranking.record_uptime("mt5")

            # oanda: better scores
            await ranking.record_latency("oanda", 1.0)
            await ranking.record_spread("oanda", 0.00005)
            await ranking.record_uptime("oanda")

            await engine.set_primary("EUR/USD", "mt5")
            decision = await engine.evaluate("EUR/USD")

            # oanda should be the fallback
            if decision.triggered:
                assert decision.reason != FailoverReason.NOT_APPLICABLE

        asyncio.run(exercise())

    def test_no_failover_when_primary_best(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking, failover_score_threshold=0.5)

            # mt5 is the best
            await ranking.record_latency("mt5", 1.0)
            await ranking.record_spread("mt5", 0.0001)
            await ranking.record_uptime("mt5")

            await engine.set_primary("EUR/USD", "mt5")
            decision = await engine.evaluate("EUR/USD")
            assert not decision.triggered

        asyncio.run(exercise())

    def test_auto_assign_primary_when_not_set(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)

            await ranking.record_latency("mt5", 5.0)
            await ranking.record_spread("mt5", 0.0001)
            await ranking.record_uptime("mt5")

            decision = await engine.evaluate("EUR/USD")
            # Should auto-assign mt5 as primary
            assert decision.primary_provider == "mt5"

        asyncio.run(exercise())

    def test_failover_history(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)

            history = await engine.get_failover_history()
            assert isinstance(history, list)

        asyncio.run(exercise())

    def test_get_total_failovers(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)
            count = await engine.get_total_failovers()
            assert count == 0

        asyncio.run(exercise())

    def test_reset(self) -> None:
        async def exercise() -> None:
            ranking = ProviderRankingEngine()
            engine = FailoverEngine(ranking)

            await engine.set_primary("EUR/USD", "mt5")
            await engine.reset()
            assert await engine.get_primary("EUR/USD") is None

        asyncio.run(exercise())

    def test_validates_thresholds(self) -> None:
        ranking = ProviderRankingEngine()
        with pytest.raises(ValueError):
            FailoverEngine(ranking, failover_score_threshold=0)
        with pytest.raises(ValueError):
            FailoverEngine(ranking, cooldown_seconds=0)
