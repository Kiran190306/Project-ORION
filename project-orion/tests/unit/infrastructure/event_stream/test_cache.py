"""Tests for MarketSnapshotCache."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.cache import MarketSnapshotCache


class TestMarketSnapshotCache:
    def test_set_and_get_latest_tick(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.1050, "ask": 1.1052})

            tick = await cache.get_latest_tick("EUR/USD")
            assert tick is not None
            assert tick["bid"] == 1.1050

        asyncio.run(exercise())

    def test_get_latest_tick_miss(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache()
            tick = await cache.get_latest_tick("EUR/USD")
            assert tick is None

        asyncio.run(exercise())

    def test_set_and_get_latest_ohlc(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            ohlc_data = {"open": 1.10, "high": 1.11, "low": 1.09, "close": 1.105}
            await cache.set_latest_ohlc("EUR/USD", "M1", ohlc_data)

            result = await cache.get_latest_ohlc("EUR/USD", "M1")
            assert result is not None
            assert result["open"] == 1.10

        asyncio.run(exercise())

    def test_get_latest_ohlc_miss(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache()
            result = await cache.get_latest_ohlc("EUR/USD", "M1")
            assert result is None

        asyncio.run(exercise())

    def test_set_and_get_latest_spread(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_spread("EUR/USD", {"spread": 0.0002})

            spread = await cache.get_latest_spread("EUR/USD")
            assert spread is not None
            assert spread["spread"] == 0.0002

        asyncio.run(exercise())

    def test_ttl_expiry(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=0.01)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})
            await asyncio.sleep(0.02)

            tick = await cache.get_latest_tick("EUR/USD")
            assert tick is None

        asyncio.run(exercise())

    def test_cache_hit_rate_tracking(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})

            # Miss
            await cache.get_latest_tick("GBP/USD")
            # Hit
            await cache.get_latest_tick("EUR/USD")
            # Hit
            await cache.get_latest_tick("EUR/USD")

            metrics = await cache.get_metrics()
            assert metrics.hits == 2
            assert metrics.misses == 1
            assert metrics.hit_rate == 2 / 3

        asyncio.run(exercise())

    def test_invalidate_symbol(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})
            await cache.set_latest_spread("EUR/USD", {"spread": 0.0002})

            count = await cache.invalidate_symbol("EUR/USD")
            assert count == 2
            assert await cache.get_latest_tick("EUR/USD") is None

        asyncio.run(exercise())

    def test_clear_all(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})
            await cache.set_latest_tick("GBP/USD", {"bid": 1.30})
            await cache.set_latest_ohlc("EUR/USD", "M1", {})
            await cache.set_latest_spread("EUR/USD", {})

            cleared = await cache.clear()
            assert cleared == 4
            metrics = await cache.get_metrics()
            assert metrics.entries == 0

        asyncio.run(exercise())

    def test_has_latest_tick(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            assert not await cache.has_latest_tick("EUR/USD")

            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})
            assert await cache.has_latest_tick("EUR/USD")

        asyncio.run(exercise())

    def test_get_hit_rate_event(self) -> None:
        async def exercise() -> None:
            cache = MarketSnapshotCache(default_ttl_seconds=60.0)
            await cache.set_latest_tick("EUR/USD", {"bid": 1.10})
            await cache.get_latest_tick("EUR/USD")  # hit
            await cache.get_latest_tick("EUR/USD")  # hit
            await cache.get_latest_tick("GBP/USD")  # miss

            event = await cache.get_hit_rate_event()
            assert event.event_type == "cache.hit_rate"
            assert event.hit_rate == 2 / 3

        asyncio.run(exercise())

    def test_validates_default_ttl(self) -> None:
        with pytest.raises(ValueError):
            MarketSnapshotCache(default_ttl_seconds=0)
