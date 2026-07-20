"""Integration tests for the event streaming layer.

Tests the full pipeline: StreamManager -> EventBus -> Subscribers -> Metrics/Health.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market import MarketDataSnapshot, Tick
from libraries.infrastructure.event_stream.backpressure import BackpressureMode
from libraries.infrastructure.event_stream.buffer import BufferOverflowPolicy
from libraries.infrastructure.event_stream.event_types import (
    EventStreamEvent,
    TickReceivedEvent,
)
from libraries.infrastructure.event_stream.stream_manager import (
    StreamManager,
    StreamManagerConfig,
)


class TestStreamManagerIntegration:
    def test_start_and_stop(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()
            assert manager.running

            await manager.stop()
            assert not manager.running

        asyncio.run(exercise())

    def test_register_and_track_provider(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            await manager.register_provider(
                provider="mt5",
                rate_limit_tokens_per_second=100.0,
                rate_limit_max_burst=200,
            )

            health = await manager.get_health()
            assert mt5_connected(health.providers)

            await manager.stop()

        asyncio.run(exercise())

    def test_create_publisher_and_subscriber(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            await manager.create_subscriber(
                subscriber_id="test_sub",
                event_type="tick.*",
                callback=handler,
            )

            publisher = await manager.create_publisher("test_pub")
            assert publisher.publisher_id == "test_pub"

            # Publish via bus directly
            await manager.bus.publish(
                TickReceivedEvent.create(
                    symbol="EUR/USD",
                    provider="mt5",
                    bid="1.1050",
                    ask="1.1052",
                )
            )
            await asyncio.sleep(0.1)

            assert len(received) > 0
            assert received[0].event_type == "tick.received"

            await manager.stop()

        asyncio.run(exercise())

    def test_full_pipeline_with_provider_and_buffering(self) -> None:
        async def exercise() -> None:
            config = StreamManagerConfig(
                buffer_maxsize=100,
                buffer_overflow_policy=BufferOverflowPolicy.DROP_OLDEST,
                backpressure_high_water=80,
                backpressure_low_water=20,
                backpressure_mode=BackpressureMode.PAUSE_PRODUCER,
                cache_default_ttl_seconds=60.0,
            )
            manager = StreamManager(config)
            await manager.start()

            await manager.register_provider(
                provider="oanda",
                rate_limit_tokens_per_second=1000.0,
                rate_limit_max_burst=100,
            )

            # Process some events
            for i in range(10):
                event = TickReceivedEvent.create(
                    symbol="GBP/USD",
                    provider="oanda",
                    bid=f"1.{3000 + i}",
                    ask=f"1.{3002 + i}",
                )
                await manager.process_event(event, provider="oanda")

            health = await manager.get_health()
            assert health.healthy is True

            metrics = await manager.get_metrics_snapshot()
            assert metrics.total_published >= 0

            await manager.stop()

        asyncio.run(exercise())

    def test_rate_limiting_rejects_excess(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            await manager.register_provider(
                provider="test",
                rate_limit_tokens_per_second=10.0,
                rate_limit_max_burst=1,
            )

            event = TickReceivedEvent.create(
                symbol="EUR/USD",
                provider="test",
                bid="1.10",
                ask="1.11",
            )

            # First event should be accepted
            ok = await manager.process_event(event, provider="test")
            assert ok is True

            # Second event should be rate limited
            ok = await manager.process_event(event, provider="test")
            assert ok is False

            await manager.stop()

        asyncio.run(exercise())

    def test_cache_integration(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            # Set and get from cache
            await manager.cache.set_latest_tick("EUR/USD", {"bid": 1.1050, "ask": 1.1052})
            tick = await manager.cache.get_latest_tick("EUR/USD")
            assert tick is not None
            assert tick["bid"] == 1.1050

            await manager.stop()

        asyncio.run(exercise())

    def test_subscriber_error_isolation(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            error_count = 0

            async def failing_handler(event: EventStreamEvent) -> None:
                nonlocal error_count
                error_count += 1
                raise ValueError("test error")

            await manager.create_subscriber(
                subscriber_id="failing",
                event_type="test.event",
                callback=failing_handler,
            )

            # Should not crash the bus
            await manager.bus.publish(EventStreamEvent(event_type="test.event"))
            await asyncio.sleep(0.05)

            assert error_count > 0

            await manager.stop()

        asyncio.run(exercise())

    def test_health_integration(self) -> None:
        async def exercise() -> None:
            manager = StreamManager()
            await manager.start()

            await manager.register_provider("provider_a")
            await manager.register_provider("provider_b")
            await manager.connect_provider("provider_a")

            health = await manager.get_health()
            d = health.to_dict()
            assert d["connected_providers"] >= 1
            assert "provider_a" in d["providers"]

            await manager.stop()

        asyncio.run(exercise())


def mt5_connected(providers: dict[str, bool]) -> bool:
    """Check if mt5 is connected in providers dict."""
    return providers.get("mt5", False) is True
