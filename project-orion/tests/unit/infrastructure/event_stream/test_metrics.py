"""Tests for StreamMetricsCollector."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.metrics import (
    MetricSample,
    StreamMetricsCollector,
)


class TestStreamMetricsCollector:
    def test_record_tick(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_tick()
            snap = await metrics.snapshot()
            # Tick count is tracked; throughput computed over time
            assert snap.ticks_per_second >= 0

        asyncio.run(exercise())

    def test_record_disconnect_and_reconnect(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_disconnect("mt5")
            await metrics.record_disconnect("oanda")
            await metrics.record_reconnect("mt5")

            snap = await metrics.snapshot()
            assert snap.disconnect_count == 2
            assert snap.reconnect_count == 1

        asyncio.run(exercise())

    def test_record_buffer_drop(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_buffer_drop()
            await metrics.record_buffer_drop()

            snap = await metrics.snapshot()
            assert snap.buffer_drops == 2

        asyncio.run(exercise())

    def test_cache_hit_and_miss(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_cache_hit()
            await metrics.record_cache_hit()
            await metrics.record_cache_hit()
            await metrics.record_cache_miss()

            snap = await metrics.snapshot()
            assert snap.cache_hit_ratio == 0.75

        asyncio.run(exercise())

    def test_queue_latency_tracking(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_queue_latency(5.0)
            await metrics.record_queue_latency(15.0)

            snap = await metrics.snapshot()
            assert snap.queue_latency_ms == 10.0

        asyncio.run(exercise())

    def test_processing_latency_tracking(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_processing_latency(2.0)
            await metrics.record_processing_latency(4.0)

            snap = await metrics.snapshot()
            assert snap.processing_latency_ms == 3.0

        asyncio.run(exercise())

    def test_record_publish_and_subscribe(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_publish()
            await metrics.record_publish()
            await metrics.record_subscribe()

            snap = await metrics.snapshot()
            assert snap.total_published == 2
            assert snap.total_subscribed == 1

        asyncio.run(exercise())

    def test_record_error_and_dead_letter(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_error()
            await metrics.record_dead_letter()
            await metrics.record_error()

            snap = await metrics.snapshot()
            assert snap.total_errors == 2
            assert snap.total_dead_letter == 1

        asyncio.run(exercise())

    def test_provider_uptime_tracking(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_provider_start("mt5")

            snap = await metrics.snapshot()
            assert "mt5" in snap.provider_uptime_seconds
            assert snap.provider_uptime_seconds["mt5"] >= 0

        asyncio.run(exercise())

    def test_record_sample(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            metrics.record_sample("gauge", "test.metric", value=42.0, tags={"env": "test"})

            samples = metrics.get_samples()
            assert len(samples) == 1
            assert samples[0].kind == "gauge"
            assert samples[0].name == "test.metric"
            assert samples[0].value == 42.0

        asyncio.run(exercise())

    def test_reset_clears_all(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_tick()
            await metrics.record_buffer_drop()
            await metrics.record_disconnect("mt5")

            await metrics.reset()

            snap = await metrics.snapshot()
            assert snap.buffer_drops == 0
            assert snap.disconnect_count == 0

        asyncio.run(exercise())

    def test_multiple_provider_disconnects(self) -> None:
        async def exercise() -> None:
            metrics = StreamMetricsCollector()
            await metrics.record_disconnect("mt5")
            await metrics.record_disconnect("mt5")
            await metrics.record_reconnect("mt5")

            snap = await metrics.snapshot()
            assert snap.disconnect_count == 2
            assert snap.reconnect_count == 1

        asyncio.run(exercise())
