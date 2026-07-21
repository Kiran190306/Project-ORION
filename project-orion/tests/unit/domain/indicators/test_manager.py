"""Tests for the Indicator Manager."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.manager import IndicatorManager
from libraries.domain.indicators.models import Bar
from libraries.domain.indicators.registry import IndicatorRegistry
from libraries.domain.indicators.rsi import RSI


@pytest.fixture
def registry() -> IndicatorRegistry:
    return IndicatorRegistry()


@pytest.fixture
def manager(registry: IndicatorRegistry) -> IndicatorManager:
    return IndicatorManager(registry=registry)


@pytest.fixture
def bars() -> list[Bar]:
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            timestamp=ts, open=100.0 + i, high=101.0 + i, low=99.0 + i, close=100.5 + i, volume=1000
        )
        for i in range(20)
    ]


@pytest.fixture
def bar() -> Bar:
    return Bar(
        timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
        open=120.0,
        high=121.0,
        low=119.0,
        close=120.5,
        volume=1000,
    )


class TestIndicatorManager:
    async def test_create_indicator(
        self, manager: IndicatorManager, registry: IndicatorRegistry
    ) -> None:
        await registry.register(EMA, name="ema")
        indicator = await manager.create_indicator("ema", "EURUSD")
        assert indicator.metadata.name == "ema"

    async def test_create_indicator_unregistered_raises(self, manager: IndicatorManager) -> None:
        with pytest.raises(ValueError, match="not registered"):
            await manager.create_indicator("nonexistent", "EURUSD")

    async def test_warmup(
        self, manager: IndicatorManager, registry: IndicatorRegistry, bars: list[Bar]
    ) -> None:
        await registry.register(EMA, name="ema")
        await manager.create_indicator("ema", "EURUSD")
        await manager.warmup("EURUSD", bars)
        indicator = await manager.get_indicator("EURUSD", "ema")
        assert indicator is not None
        assert indicator.is_warmed_up() is True

    async def test_update(
        self, manager: IndicatorManager, registry: IndicatorRegistry, bars: list[Bar], bar: Bar
    ) -> None:
        await registry.register(RSI, name="rsi")
        await manager.create_indicator("rsi", "EURUSD")
        await manager.warmup("EURUSD", bars)
        results = await manager.update("EURUSD", bar)
        assert "rsi" in results
        assert results["rsi"].value is not None

    async def test_batch_calculate(
        self, manager: IndicatorManager, registry: IndicatorRegistry, bars: list[Bar]
    ) -> None:
        await registry.register(EMA, name="ema")
        # Need to create the indicator first so batch_calculate has it
        await manager.create_indicator("ema", "EURUSD")
        results = await manager.batch_calculate("EURUSD", bars, indicator_names=["ema"])
        assert "ema" in results
        assert len(results["ema"]) > 0

    async def test_get_indicator(
        self, manager: IndicatorManager, registry: IndicatorRegistry
    ) -> None:
        await registry.register(EMA, name="ema")
        await manager.create_indicator("ema", "EURUSD")
        indicator = await manager.get_indicator("EURUSD", "ema")
        assert indicator is not None

    async def test_list_indicators(
        self, manager: IndicatorManager, registry: IndicatorRegistry
    ) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        await manager.create_indicator("ema", "EURUSD")
        await manager.create_indicator("rsi", "EURUSD")
        listing = await manager.list_indicators()
        assert "EURUSD" in listing
        assert len(listing["EURUSD"]) == 2

    async def test_remove_indicator(
        self, manager: IndicatorManager, registry: IndicatorRegistry
    ) -> None:
        await registry.register(EMA, name="ema")
        await manager.create_indicator("ema", "EURUSD")
        removed = await manager.remove_indicator("EURUSD", "ema")
        assert removed is True
        indicator = await manager.get_indicator("EURUSD", "ema")
        assert indicator is None

    async def test_remove_indicator_not_found(self, manager: IndicatorManager) -> None:
        removed = await manager.remove_indicator("EURUSD", "nonexistent")
        assert removed is False

    async def test_reset_all(
        self, manager: IndicatorManager, registry: IndicatorRegistry, bars: list[Bar]
    ) -> None:
        await registry.register(EMA, name="ema")
        await manager.create_indicator("ema", "EURUSD")
        await manager.warmup("EURUSD", bars)
        await manager.reset()
        indicator = await manager.get_indicator("EURUSD", "ema")
        assert indicator is not None
        assert indicator.is_warmed_up() is False

    async def test_reset_symbol(
        self, manager: IndicatorManager, registry: IndicatorRegistry, bars: list[Bar]
    ) -> None:
        await registry.register(EMA, name="ema")
        await manager.create_indicator("ema", "EURUSD")
        await manager.warmup("EURUSD", bars)
        await manager.reset(symbol="EURUSD")
        indicator = await manager.get_indicator("EURUSD", "ema")
        assert indicator is not None
        assert indicator.is_warmed_up() is False
