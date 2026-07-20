"""Tests for StreamSubscriber."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.event_bus import InMemoryPriorityBus
from libraries.infrastructure.event_stream.event_types import EventStreamEvent
from libraries.infrastructure.event_stream.subscriber import StreamSubscriber


class TestStreamSubscriber:
    def test_subscriber_receives_events(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            subscriber = StreamSubscriber(
                subscriber_id="sub1",
                bus=bus,
                event_type="test.event",
                callback=handler,
            )
            await subscriber.start()

            await bus.publish(EventStreamEvent(event_type="test.event"))
            await asyncio.sleep(0.05)

            assert len(received) == 1
            assert received[0].event_type == "test.event"

            await subscriber.stop()
            await bus.stop()

        asyncio.run(exercise())

    def test_subscriber_can_be_stopped(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            subscriber = StreamSubscriber(
                subscriber_id="sub1",
                bus=bus,
                event_type="test.event",
                callback=handler,
            )
            await subscriber.start()
            await subscriber.stop()

            await bus.publish(EventStreamEvent(event_type="test.event"))
            await asyncio.sleep(0.05)

            assert len(received) == 0

            await bus.stop()

        asyncio.run(exercise())

    def test_subscriber_error_does_not_crash(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            async def failing_handler(event: EventStreamEvent) -> None:
                raise ValueError("handler failure")

            subscriber = StreamSubscriber(
                subscriber_id="failing",
                bus=bus,
                event_type="test.event",
                callback=failing_handler,
            )
            await subscriber.start()

            # This should not raise
            await bus.publish(EventStreamEvent(event_type="test.event"))
            await asyncio.sleep(0.05)

            stats = await subscriber.get_stats()
            assert stats.total_errors == 1

            await subscriber.stop()
            await bus.stop()

        asyncio.run(exercise())

    def test_get_stats_returns_correct_counts(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            subscriber = StreamSubscriber(
                subscriber_id="stats_sub",
                bus=bus,
                event_type="test.event",
                callback=handler,
            )
            await subscriber.start()

            await bus.publish(EventStreamEvent(event_type="test.event"))
            await bus.publish(EventStreamEvent(event_type="test.event"))
            await asyncio.sleep(0.05)

            stats = await subscriber.get_stats()
            assert stats.subscriber_id == "stats_sub"
            assert stats.total_received == 2
            assert stats.event_type == "test.event"
            assert stats.active is True

            await subscriber.stop()
            await bus.stop()

        asyncio.run(exercise())

    def test_idempotent_start_stop(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            async def handler(event: EventStreamEvent) -> None:
                pass

            subscriber = StreamSubscriber(
                subscriber_id="sub1",
                bus=bus,
                event_type="test.event",
                callback=handler,
            )

            # Start twice should be idempotent
            await subscriber.start()
            await subscriber.start()
            assert subscriber.active

            # Stop twice should be idempotent
            await subscriber.stop()
            await subscriber.stop()
            assert not subscriber.active

            await bus.stop()

        asyncio.run(exercise())
