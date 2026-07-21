"""Tests for the Indicator Registry."""

from __future__ import annotations

import pytest

from libraries.domain.indicators.ema import EMA
from libraries.domain.indicators.exceptions import IndicatorRegistrationError
from libraries.domain.indicators.registry import IndicatorRegistry
from libraries.domain.indicators.rsi import RSI


@pytest.fixture
def registry() -> IndicatorRegistry:
    return IndicatorRegistry()


class TestIndicatorRegistry:
    async def test_register(self, registry: IndicatorRegistry) -> None:
        entry = await registry.register(EMA, name="ema")
        assert entry.name == "ema"
        assert entry.version == "1.0.0"

    async def test_register_duplicate_raises(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        with pytest.raises(IndicatorRegistrationError):
            await registry.register(RSI, name="ema")

    async def test_register_duplicate_force(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        entry = await registry.register(RSI, name="ema", force=True)
        assert entry.name == "ema"

    async def test_unregister(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.unregister("ema")
        assert await registry.is_registered("ema") is False

    async def test_unregister_missing_raises(self, registry: IndicatorRegistry) -> None:
        with pytest.raises(KeyError):
            await registry.unregister("nonexistent")

    async def test_discover_by_type(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        trend_indicators = await registry.discover(indicator_type="trend")
        assert any(e.name == "ema" for e in trend_indicators)
        momentum_indicators = await registry.discover(indicator_type="momentum")
        assert any(e.name == "rsi" for e in momentum_indicators)

    async def test_discover_by_name_pattern(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        results = await registry.discover(name_pattern="em")
        assert len(results) == 1
        assert results[0].name == "ema"

    async def test_get_metadata(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        metadata = await registry.get_metadata("ema")
        assert metadata is not None
        assert metadata.name == "ema"

    async def test_get_class(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        cls = await registry.get_class("ema")
        assert cls is EMA

    async def test_is_registered(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        assert await registry.is_registered("ema") is True
        assert await registry.is_registered("rsi") is False

    async def test_version_compatibility_major_match(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema", version="2.0.0")
        compatible = await registry.check_version_compatibility("ema", "2.5.0")
        assert compatible is True

    async def test_version_compatibility_major_mismatch(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema", version="1.0.0")
        compatible = await registry.check_version_compatibility("ema", "2.0.0")
        assert compatible is False

    async def test_version_compatibility_missing(self, registry: IndicatorRegistry) -> None:
        compatible = await registry.check_version_compatibility("missing", "1.0.0")
        assert compatible is False

    async def test_list_all(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        all_entries = await registry.list_all()
        assert len(all_entries) == 2

    async def test_count(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        count = await registry.count()
        assert count == 2

    async def test_clear(self, registry: IndicatorRegistry) -> None:
        await registry.register(EMA, name="ema")
        await registry.register(RSI, name="rsi")
        await registry.clear()
        assert await registry.count() == 0
