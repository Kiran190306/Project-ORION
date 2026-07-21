"""Integration tests for the complete strategy framework."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.strategies.composite import CompositeStrategy
from libraries.domain.strategies.conflict_resolver import ConflictResolver
from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.manager import StrategyManager
from libraries.domain.strategies.strategy import (
    BreakoutStrategy,
    EmaCrossStrategy,
    RsiStrategy,
)
from libraries.domain.strategies.voting import VotingEngine, VotingMethod
from libraries.domain.trading.signals import SignalDirection


class TestStrategyIntegration:
    def test_full_pipeline_buy_signal(self) -> None:
        """Test complete pipeline: register -> evaluate -> result."""

        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()

            await manager.register_strategy(EmaCrossStrategy())
            await manager.register_strategy(RsiStrategy(oversold_threshold=30.0))
            await manager.register_strategy(BreakoutStrategy())

            # Create context that triggers BUY from EMA and RSI
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                rsi=25.0,
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
                price_position=0.7,
                volume_ratio=1.2,
            )

            results = await manager.evaluate("EUR/USD", ctx)
            assert len(results) >= 1

            # Run through voting engine
            voting = VotingEngine()
            vote_result = await voting.vote(results)
            assert vote_result.direction is not None
            assert vote_result.confidence > 0

            await manager.stop()

        asyncio.run(exercise())

    def test_full_pipeline_conflict_resolution(self) -> None:
        """Test composite strategy with conflicting signals."""

        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(EmaCrossStrategy())
            composite.add_strategy(RsiStrategy(oversold_threshold=80.0))

            # EMA says BUY, RSI says SELL (overbought)
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                rsi=85.0,
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )

            result = await composite.evaluate("EUR/USD", ctx)
            assert result.conflict_result is not None
            assert len(result.individual_results) >= 1

        asyncio.run(exercise())

    def test_full_pipeline_breakout(self) -> None:
        """Test breakout detection through the full pipeline."""

        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()

            await manager.register_strategy(BreakoutStrategy())
            await manager.register_strategy(EmaCrossStrategy())

            ctx = StrategyContext(
                symbol="EUR/USD",
                price_position=0.95,
                volume_ratio=2.5,
                ema_fast=Decimal("1.1100"),
                ema_slow=Decimal("1.0800"),
                bid=Decimal("1.1100"),
                ask=Decimal("1.1102"),
            )

            results = await manager.evaluate("EUR/USD", ctx)
            assert len(results) >= 1

            voting = VotingEngine(default_method=VotingMethod.CONFIDENCE_WEIGHTED)
            vote_result = await voting.vote(results)
            assert vote_result.direction == SignalDirection.BUY

            await manager.stop()

        asyncio.run(exercise())

    def test_consensus_required_pipeline(self) -> None:
        """Test consensus voting requirement."""

        async def exercise() -> None:
            composite = CompositeStrategy()
            composite.add_strategy(EmaCrossStrategy())
            composite.add_strategy(RsiStrategy())

            # Both should agree on BUY (EMA bullish, RSI oversold)
            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                rsi=25.0,
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )

            result = await composite.evaluate(
                "EUR/USD",
                ctx,
                voting_method=VotingMethod.CONSENSUS,
            )
            assert result.voting_result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_lifecycle_with_registry(self) -> None:
        """Test strategy lifecycle through manager."""

        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()

            await manager.register_strategy(EmaCrossStrategy())
            await manager.register_strategy(RsiStrategy())

            health = await manager.health_check()
            assert health["total_strategies"] == 2
            assert health["active_strategies"] == 2

            await manager.disable_strategy("ema_cross")
            health = await manager.health_check()
            # Stats should still work
            assert health["total_strategies"] == 2

            await manager.stop()

        asyncio.run(exercise())

    def test_statistics_through_full_pipeline(self) -> None:
        """Test statistics collection through manager."""

        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()

            await manager.register_strategy(EmaCrossStrategy())

            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
            )

            # Execute multiple times
            for _ in range(3):
                await manager.evaluate("EUR/USD", ctx)

            stats_obj = await manager.get_statistics("ema_cross")
            assert stats_obj is not None
            snapshot = await stats_obj.get_stats("ema_cross")
            assert snapshot.execution_count >= 1  # At least some executions tracked

            await manager.stop()

        asyncio.run(exercise())
