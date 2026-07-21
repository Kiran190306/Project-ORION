"""Tests for the Indicator Cache."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.indicators.cache import IndicatorCache, IndicatorCacheConfig
from libraries.domain.indicators.models import Bar, IndicatorResult


@pytest.fixture
def cache() -> IndicatorCache:
    config = IndicatorCacheConfig(default_ttl_seconds=60, max_entries_per_indicator=10)
    return IndicatorCache(config)


@pytest.fixture
def bar() -> Bar:
    return Bar(
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
        symbol="EURUSD",
    )


@pytest.fixture
def result(bar: Bar) -> IndicatorResult:
    return IndicatorResult(
        indicator_name="rsi",
        timestamp=bar.timestamp,
        value=55.0,
    )


class TestIndicatorCache:
    async def test_set_and_get(
        self, cache: IndicatorCache, bar: Bar, result: IndicatorResult
    ) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD")
        cached = await cache.get("rsi", bar, symbol="EURUSD")
        assert cached is not None
        assert cached.value == 55.0

    async def test_miss(self, cache: IndicatorCache, bar: Bar) -> None:
        cached = await cache.get("ema", bar, symbol="EURUSD")
        assert cached is None

    async def test_ttl_expiry(self) -> None:
        config = IndicatorCacheConfig(default_ttl_seconds=0, max_entries_per_indicator=10)
        cache = IndicatorCache(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = IndicatorResult(indicator_name="rsi", timestamp=bar.timestamp, value=55.0)
        await cache.set("rsi", bar, result)
        cached = await cache.get("rsi", bar)
        assert cached is None  # Expired immediately

    async def test_cache_hit_ratio(
        self, cache: IndicatorCache, bar: Bar, result: IndicatorResult
    ) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD")
        await cache.get("rsi", bar, symbol="EURUSD")
        await cache.get("missing", bar, symbol="EURUSD")
        stats = await cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5

    async def test_invalidate_by_indicator(
        self, cache: IndicatorCache, bar: Bar, result: IndicatorResult
    ) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD")
        await cache.set("ema", bar, result, symbol="EURUSD")
        count = await cache.invalidate(indicator_name="rsi")
        assert count == 1
        assert await cache.get("rsi", bar, symbol="EURUSD") is None
        assert await cache.get("ema", bar, symbol="EURUSD") is not None

    async def test_invalidate_by_symbol(
        self, cache: IndicatorCache, bar: Bar, result: IndicatorResult
    ) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD")
        await cache.set("rsi", bar, result, symbol="GBPUSD")
        count = await cache.invalidate(symbol="EURUSD")
        assert count >= 1

    async def test_clear(self, cache: IndicatorCache, bar: Bar, result: IndicatorResult) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD")
        await cache.clear()
        stats = await cache.get_stats()
        assert stats["size"] == 0

    async def test_max_entries(self) -> None:
        config = IndicatorCacheConfig(default_ttl_seconds=300, max_entries_per_indicator=2)
        cache = IndicatorCache(config)
        bar = Bar(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000,
        )
        result = IndicatorResult(indicator_name="rsi", timestamp=bar.timestamp, value=55.0)
        await cache.set("rsi", bar, result, symbol="EURUSD")
        bar2 = Bar(
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc),
            open=101.0,
            high=102.0,
            low=100.0,
            close=101.5,
            volume=1000,
        )
        result2 = IndicatorResult(indicator_name="rsi", timestamp=bar2.timestamp, value=56.0)
        await cache.set("rsi", bar2, result2, symbol="EURUSD")
        bar3 = Bar(
            timestamp=datetime(2024, 1, 3, tzinfo=timezone.utc),
            open=102.0,
            high=103.0,
            low=101.0,
            close=102.5,
            volume=1000,
        )
        result3 = IndicatorResult(indicator_name="rsi", timestamp=bar3.timestamp, value=57.0)
        await cache.set("rsi", bar3, result3, symbol="EURUSD")
        stats = await cache.get_stats()
        assert stats["size"] <= 2

    async def test_timeframe_scoped(
        self, cache: IndicatorCache, bar: Bar, result: IndicatorResult
    ) -> None:
        await cache.set("rsi", bar, result, symbol="EURUSD", timeframe="1h")
        cached_1h = await cache.get("rsi", bar, symbol="EURUSD", timeframe="1h")
        assert cached_1h is not None
        cached_4h = await cache.get("rsi", bar, symbol="EURUSD", timeframe="4h")
        assert cached_4h is None
