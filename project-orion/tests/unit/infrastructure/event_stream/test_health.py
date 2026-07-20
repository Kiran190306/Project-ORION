"""Tests for StreamHealth."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.health import StreamHealth


class TestStreamHealth:
    def test_initial_health_status(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            status = await health.get_health()
            assert status.healthy is True
            assert status.queue_depth == 0
            assert status.connected_providers == 0
            assert status.total_errors == 0

        asyncio.run(exercise())

    def test_set_queue_depth(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_queue_depth(50, 100)
            status = await health.get_health()
            assert status.queue_depth == 50
            assert status.queue_max_size == 100
            assert status.buffer_usage_pct == 50.0

        asyncio.run(exercise())

    def test_provider_connection_tracking(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_provider_connected("mt5")
            await health.set_provider_connected("oanda")

            status = await health.get_health()
            assert status.connected_providers == 2
            assert status.providers.get("mt5") is True

            await health.set_provider_disconnected("mt5")
            status = await health.get_health()
            assert status.connected_providers == 1
            assert status.providers.get("mt5") is False

        asyncio.run(exercise())

    def test_record_tick_updates_last_tick_time(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            assert (await health.get_health()).last_tick_time is None

            await health.record_tick()
            status = await health.get_health()
            assert status.last_tick_time is not None

        asyncio.run(exercise())

    def test_record_error_increments_count(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.record_error()
            await health.record_error()

            status = await health.get_health()
            assert status.total_errors == 2

        asyncio.run(exercise())

    def test_set_cache_hit_rate(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_cache_hit_rate(0.85)
            status = await health.get_health()
            assert status.cache_hit_rate == 0.85

        asyncio.run(exercise())

    def test_set_queue_latency(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_queue_latency(5.5)
            status = await health.get_health()
            assert status.queue_latency_ms == 5.5

        asyncio.run(exercise())

    def test_set_processing_latency(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_processing_latency(2.3)
            status = await health.get_health()
            assert status.processing_latency_ms == 2.3

        asyncio.run(exercise())

    def test_health_to_dict(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            status = await health.get_health()
            d = status.to_dict()
            assert d["healthy"] is True
            assert "checked_at" in d
            assert "queue_depth" in d
            assert "providers" in d

        asyncio.run(exercise())

    def test_reset_clears_all(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.record_error()
            await health.set_queue_depth(50, 100)
            await health.set_provider_connected("mt5")

            await health.reset()

            status = await health.get_health()
            assert status.total_errors == 0
            assert status.queue_depth == 0
            assert status.connected_providers == 0

        asyncio.run(exercise())

    def test_healthy_flag_false_when_queue_near_capacity(self) -> None:
        async def exercise() -> None:
            health = StreamHealth()
            await health.set_queue_depth(95, 100)
            status = await health.get_health()
            # 95% > 90% threshold
            assert status.healthy is False

        asyncio.run(exercise())
