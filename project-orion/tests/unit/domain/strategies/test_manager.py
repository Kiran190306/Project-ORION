"""Tests for StrategyManager."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.exceptions import StrategyNotFoundError
from libraries.domain.strategies.manager import StrategyManager, StrategyManagerConfig
from libraries.domain.strategies.models import StrategyPriority
from libraries.domain.strategies.strategy import (
    BreakoutStrategy,
    EmaCrossStrategy,
    RsiStrategy,
)


class TestStrategyManager:
    def test_initialization(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            assert not manager.running

        asyncio.run(exercise())

    def test_start_and_stop(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            assert manager.running
            await manager.stop()
            assert not manager.running

        asyncio.run(exercise())

    def test_register_strategy(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            strategy_id = await manager.register_strategy(strategy)
            assert strategy_id == "ema_cross"
            assert await manager.registry.contains("ema_cross")
            await manager.stop()

        asyncio.run(exercise())

    def test_unregister_strategy(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            await manager.unregister_strategy("ema_cross")
            assert not await manager.registry.contains("ema_cross")
            await manager.stop()

        asyncio.run(exercise())

    def test_enable_disable_strategy(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            await manager.disable_strategy("ema_cross")
            # Should not raise
            await manager.enable_strategy("ema_cross")
            await manager.stop()

        asyncio.run(exercise())

    def test_disable_nonexistent_raises(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            with pytest.raises(StrategyNotFoundError):
                await manager.disable_strategy("nonexistent")

        asyncio.run(exercise())

    def test_set_priority(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            await manager.set_priority("ema_cross", StrategyPriority.HIGH)
            priority = await manager.get_priority("ema_cross")
            assert priority == StrategyPriority.HIGH.numeric
            await manager.stop()

        asyncio.run(exercise())

    def test_set_priority_nonexistent_raises(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            with pytest.raises(StrategyNotFoundError):
                await manager.set_priority("nonexistent", StrategyPriority.HIGH)

        asyncio.run(exercise())

    def test_evaluate_returns_results(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)

            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
            )
            results = await manager.evaluate("EUR/USD", ctx)
            assert len(results) >= 1
            await manager.stop()

        asyncio.run(exercise())

    def test_evaluate_returns_empty_when_stopped(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            # Don't start
            ctx = StrategyContext(symbol="EUR/USD")
            results = await manager.evaluate("EUR/USD", ctx)
            assert results == []

        asyncio.run(exercise())

    def test_get_statistics(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)

            stats = await manager.get_statistics("ema_cross")
            assert stats is not None

            await manager.stop()

        asyncio.run(exercise())

    def test_reset_statistics(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            await manager.reset_statistics("ema_cross")

            stats_obj = await manager.get_statistics("ema_cross")
            assert stats_obj is not None
            snapshot = await stats_obj.get_stats("ema_cross")
            assert snapshot.execution_count == 0

            await manager.stop()

        asyncio.run(exercise())

    def test_health_check(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)

            health = await manager.health_check()
            assert health["running"] is True
            assert health["total_strategies"] >= 1
            assert "ema_cross" in health["strategies"]

            await manager.stop()

        asyncio.run(exercise())

    def test_pause_and_resume_strategy(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            await manager.pause_strategy("ema_cross")
            await manager.resume_strategy("ema_cross")
            await manager.pause_strategy("ema_cross")
            await manager.stop()

        asyncio.run(exercise())

    def test_pause_nonexistent_raises(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            with pytest.raises(StrategyNotFoundError):
                await manager.pause_strategy("nonexistent")

        asyncio.run(exercise())

    def test_resume_nonexistent_raises(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            with pytest.raises(StrategyNotFoundError):
                await manager.resume_strategy("nonexistent")

        asyncio.run(exercise())

    def test_shutdown_strategy_handles_nonexistent(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            # Should not raise
            await manager.shutdown_strategy("nonexistent")
            await manager.stop()

        asyncio.run(exercise())

    def test_stop_twice_is_idempotent(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            await manager.stop()
            await manager.stop()  # Should not raise
            assert not manager.running

        asyncio.run(exercise())

    def test_evaluate_with_strategy_not_found_in_registry(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            strategy = EmaCrossStrategy()
            await manager.register_strategy(strategy)
            # Manually remove from registry to trigger not found
            # This simulates a stale lifecycle entry
            await manager.registry.unregister("ema_cross")

            ctx = StrategyContext(symbol="EUR/USD")
            results = await manager.evaluate("EUR/USD", ctx)
            # Should handle gracefully - strategy not in registry but lifecycle exists
            await manager.stop()

        asyncio.run(exercise())

    def test_evaluate_error_records_statistics(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()

            # Create a strategy that raises on evaluate
            class FailingStrategy(EmaCrossStrategy):
                async def evaluate(self, symbol: str, context: StrategyContext) -> None:
                    raise ValueError("test error")

            await manager.register_strategy(FailingStrategy())

            ctx = StrategyContext(symbol="EUR/USD")
            results = await manager.evaluate("EUR/USD", ctx)
            assert len(results) == 0

            stats = await manager.get_statistics("ema_cross")
            assert stats is not None
            snap = await stats.get_stats("ema_cross")
            assert snap.error_count > 0

            await manager.stop()

        asyncio.run(exercise())

    def test_multiple_strategies_evaluation(self) -> None:
        async def exercise() -> None:
            manager = StrategyManager()
            await manager.start()
            await manager.register_strategy(EmaCrossStrategy())
            await manager.register_strategy(RsiStrategy())

            ctx = StrategyContext(
                symbol="EUR/USD",
                ema_fast=Decimal("1.1050"),
                ema_slow=Decimal("1.1000"),
                rsi=25.0,
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
            )
            results = await manager.evaluate("EUR/USD", ctx)
            assert len(results) >= 1

            await manager.stop()

        asyncio.run(exercise())
