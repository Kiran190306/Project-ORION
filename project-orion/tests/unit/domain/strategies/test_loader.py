"""Tests for StrategyLoader."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.strategies.exceptions import StrategyRegistrationError
from libraries.domain.strategies.loader import StrategyLoader
from libraries.domain.strategies.registry import StrategyRegistry
from libraries.domain.strategies.strategy import EmaCrossStrategy, RsiStrategy


class TestStrategyLoader:
    def test_load_single_strategy(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            strategy = EmaCrossStrategy()
            await loader.load(strategy)
            assert await registry.contains("ema_cross")

        asyncio.run(exercise())

    def test_load_batch(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            strategies = [EmaCrossStrategy(), RsiStrategy()]
            loaded = await loader.load_batch(strategies)
            assert len(loaded) == 2
            assert "ema_cross" in loaded
            assert "rsi_strategy" in loaded

        asyncio.run(exercise())

    def test_load_batch_continues_on_error(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            s1 = EmaCrossStrategy()
            s2 = EmaCrossStrategy()  # Same id, will fail
            await loader.load(s1)
            loaded = await loader.load_batch([s2])
            assert len(loaded) == 0  # Second registration fails silently

        asyncio.run(exercise())

    def test_unload_disposes_strategy(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            strategy = EmaCrossStrategy()
            await loader.load(strategy)
            assert await registry.contains("ema_cross")
            await loader.unload("ema_cross")
            assert not await registry.contains("ema_cross")

        asyncio.run(exercise())

    def test_unload_nonexistent_does_not_raise(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            await loader.unload("nonexistent")  # Should not raise

        asyncio.run(exercise())

    def test_reload_unregisters_and_registers(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            loader = StrategyLoader(registry)
            strategy = EmaCrossStrategy()
            await loader.load(strategy)
            await loader.reload(EmaCrossStrategy())
            assert await registry.contains("ema_cross")

        asyncio.run(exercise())
