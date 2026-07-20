"""Tests for StreamPublisher."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.market import MarketDataSnapshot, Tick
from libraries.infrastructure.event_stream.event_bus import InMemoryPriorityBus
from libraries.infrastructure.event_stream.publisher import StreamPublisher


class TestStreamPublisher:
    def test_publish_sends_events_to_bus(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[str] = []

            async def handler(event) -> None:
                received.append(event.event_type)

            await bus.subscribe("test", "tick.received", handler)
            await bus.subscribe("test2", "snapshot.published", handler)

            publisher = StreamPublisher(publisher_id="test_pub", bus=bus)

            tick = Tick(
                symbol="EUR/USD",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
                source="test",
            )
            snapshot = MarketDataSnapshot(
                tick=tick,
                active_sessions=("london",),
                received_at=datetime.now(timezone.utc),
                accepted_sequence=1,
            )

            await publisher.publish(snapshot)
            await asyncio.sleep(0.05)

            assert "tick.received" in received
            assert "snapshot.published" in received

            await bus.stop()

        asyncio.run(exercise())

    def test_publish_error_isolation(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            publisher = StreamPublisher(publisher_id="test_pub", bus=bus)

            # Publishing when bus is stopped should not crash publisher
            await bus.stop()
            # Should not raise - error is recorded internally
            tick = Tick(
                symbol="EUR/USD",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
                source="test",
            )
            snapshot = MarketDataSnapshot(
                tick=tick,
                active_sessions=(),
                received_at=datetime.now(timezone.utc),
                accepted_sequence=1,
            )
            await publisher.publish(snapshot)

            stats = await publisher.get_stats()
            assert stats.total_errors > 0

        asyncio.run(exercise())

    def test_get_stats_returns_correct_counts(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            publisher = StreamPublisher(publisher_id="stats_pub", bus=bus)

            tick = Tick(
                symbol="EUR/USD",
                timestamp=datetime.now(timezone.utc),
                bid=Decimal("1.1050"),
                ask=Decimal("1.1052"),
                source="test",
            )
            snapshot = MarketDataSnapshot(
                tick=tick,
                active_sessions=(),
                received_at=datetime.now(timezone.utc),
                accepted_sequence=1,
            )

            await publisher.publish(snapshot)
            await publisher.publish(snapshot)

            stats = await publisher.get_stats()
            assert stats.publisher_id == "stats_pub"
            assert stats.total_published == 2

            await bus.stop()

        asyncio.run(exercise())

    def test_implements_market_data_publisher_protocol(self) -> None:
        from libraries.domain.market.interfaces import MarketDataPublisher

        bus = InMemoryPriorityBus()
        publisher = StreamPublisher(publisher_id="test", bus=bus)
        assert isinstance(publisher, MarketDataPublisher)
