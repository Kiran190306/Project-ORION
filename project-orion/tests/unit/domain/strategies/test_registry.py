"""Tests for StrategyRegistry."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.strategies.exceptions import (
    StrategyNotFoundError,
    StrategyRegistrationError,
)
from libraries.domain.strategies.interfaces import (
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.models import StrategyConfig, StrategyStatus
from libraries.domain.strategies.registry import StrategyRegistry
from libraries.domain.strategies.strategy import (
    BaseStrategy,
    EmaCrossStrategy,
    RsiStrategy,
)


class TestStrategyRegistry:
    def test_register_and_get(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            strategy = EmaCrossStrategy()
            await registry.register(strategy)
            retrieved = await registry.get("ema_cross")
            assert retrieved.id == "ema_cross"
            assert retrieved.name == "EMA Cross"

        asyncio.run(exercise())

    def test_duplicate_id_raises(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            strategy = EmaCrossStrategy()
            await registry.register(strategy)
            with pytest.raises(StrategyRegistrationError, match="already registered"):
                await registry.register(strategy)

        asyncio.run(exercise())

    def test_duplicate_name_raises(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            s1 = EmaCrossStrategy()
            s2 = EmaCrossStrategy()  # Same name
            await registry.register(s1)
            with pytest.raises(StrategyRegistrationError):
                await registry.register(s2)

        asyncio.run(exercise())

    def test_get_not_found_raises(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            with pytest.raises(StrategyNotFoundError):
                await registry.get("nonexistent")

        asyncio.run(exercise())

    def test_unregister_removes_strategy(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            strategy = EmaCrossStrategy()
            await registry.register(strategy)
            assert await registry.contains("ema_cross")
            await registry.unregister("ema_cross")
            assert not await registry.contains("ema_cross")

        asyncio.run(exercise())

    def test_unregister_not_found_raises(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            with pytest.raises(StrategyNotFoundError):
                await registry.unregister("nonexistent")

        asyncio.run(exercise())

    def test_list_returns_all(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            await registry.register(EmaCrossStrategy())
            await registry.register(RsiStrategy())

            strategies = await registry.list()
            assert len(strategies) == 2

        asyncio.run(exercise())

    def test_list_filter_by_market(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            await registry.register(EmaCrossStrategy())
            strategies = await registry.list(market="forex")
            assert len(strategies) >= 1

        asyncio.run(exercise())

    def test_list_filter_by_timeframe(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            await registry.register(EmaCrossStrategy())
            strategies = await registry.list(timeframe="H1")
            assert len(strategies) >= 1

        asyncio.run(exercise())

    def test_discover(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            await registry.register(EmaCrossStrategy())
            discovered = await registry.discover()
            assert len(discovered) == 1

        asyncio.run(exercise())

    def test_contains(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            strategy = EmaCrossStrategy()
            await registry.register(strategy)
            assert await registry.contains("ema_cross")
            assert not await registry.contains("nonexistent")

        asyncio.run(exercise())

    def test_count(self) -> None:
        async def exercise() -> None:
            registry = StrategyRegistry()
            assert await registry.count() == 0
            await registry.register(EmaCrossStrategy())
            assert await registry.count() == 1

        asyncio.run(exercise())

    def test_version_compatibility(self) -> None:
        assert StrategyRegistry.check_version_compatibility("1.0.0", "1.0.0")
        assert StrategyRegistry.check_version_compatibility("1.5.0", "1.0.0")
        assert not StrategyRegistry.check_version_compatibility("0.9.0", "1.0.0")
        assert StrategyRegistry.check_version_compatibility("1.5.0", "1.0.0", "2.0.0")
        assert not StrategyRegistry.check_version_compatibility("2.1.0", "1.0.0", "2.0.0")
