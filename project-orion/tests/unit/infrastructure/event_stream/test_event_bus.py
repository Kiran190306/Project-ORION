"""Tests for EventBus and PriorityEventBus."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.event_bus import (
    DeadLetterEvent,
    EventBusError,
    InMemoryPriorityBus,
    PriorityEventBus,
)
from libraries.infrastructure.event_stream.event_types import (
    EventPriority,
    EventStreamEvent,
)


def make_event(event_type: str = "test.event") -> EventStreamEvent:
    return EventStreamEvent(event_type=event_type)


class TestInMemoryPriorityBus:
    def test_publish_and_subscribe(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            await bus.subscribe("sub1", "test.event", handler)
            await bus.publish(make_event("test.event"))

            # Give delivery time
            await asyncio.sleep(0.05)
            assert len(received) == 1
            assert received[0].event_type == "test.event"

            await bus.stop()

        asyncio.run(exercise())

    def test_fan_out_multiple_subscribers(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received1: list[EventStreamEvent] = []
            received2: list[EventStreamEvent] = []

            async def handler1(event: EventStreamEvent) -> None:
                received1.append(event)

            async def handler2(event: EventStreamEvent) -> None:
                received2.append(event)

            await bus.subscribe("sub1", "test.event", handler1)
            await bus.subscribe("sub2", "test.event", handler2)

            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)

            assert len(received1) == 1
            assert len(received2) == 1

            await bus.stop()

        asyncio.run(exercise())

    def test_wildcard_subscription(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            await bus.subscribe("wild", "tick.*", handler)

            await bus.publish(make_event("tick.received"))
            await bus.publish(make_event("tick.processed"))
            await bus.publish(make_event("other.event"))
            await asyncio.sleep(0.05)

            assert len(received) == 2
            assert received[0].event_type == "tick.received"
            assert received[1].event_type == "tick.processed"

            await bus.stop()

        asyncio.run(exercise())

    def test_error_isolation(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def failing_handler(event: EventStreamEvent) -> None:
                raise ValueError("handler error")

            async def good_handler(event: EventStreamEvent) -> None:
                received.append(event)

            await bus.subscribe("failing", "test.event", failing_handler)
            await bus.subscribe("good", "test.event", good_handler)

            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)

            # Good handler should still receive the event
            assert len(received) == 1

            await bus.stop()

        asyncio.run(exercise())

    def test_dead_letter_on_failure(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            async def failing_handler(event: EventStreamEvent) -> None:
                raise ValueError("fail")

            await bus.subscribe("sub1", "test.event", failing_handler)
            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)

            assert await bus.get_dead_letter_count() > 0

            await bus.stop()

        asyncio.run(exercise())

    def test_publish_before_start_raises(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            with pytest.raises(EventBusError):
                await bus.publish(make_event())

        asyncio.run(exercise())

    def test_unsubscribe_removes_handler(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            sub = await bus.subscribe("sub1", "test.event", handler)
            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)
            assert len(received) == 1

            await bus.unsubscribe(sub)
            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)
            assert len(received) == 1  # Still 1

            await bus.stop()

        asyncio.run(exercise())

    def test_get_dead_letter_events(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            async def failing_handler(event: EventStreamEvent) -> None:
                raise RuntimeError("fail")

            await bus.subscribe("sub1", "test.event", failing_handler)
            await bus.publish(make_event("test.event"))
            await asyncio.sleep(0.05)

            dead = bus.get_dead_letter_events()
            assert len(dead) == 1
            assert isinstance(dead[0], DeadLetterEvent)

            await bus.stop()

        asyncio.run(exercise())

    def test_priority_event_bus_wrapper(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            pb = PriorityEventBus(bus)
            received: list[EventStreamEvent] = []

            async def handler(event: EventStreamEvent) -> None:
                received.append(event)

            await pb.subscribe("sub1", "test.event", handler)
            await pb.publish(make_event("test.event"))
            await asyncio.sleep(0.05)

            assert len(received) == 1

            await pb.stop()

        asyncio.run(exercise())

    def test_multiple_event_types(self) -> None:
        async def exercise() -> None:
            bus = InMemoryPriorityBus()
            await bus.start()

            received: list[str] = []

            async def handler_a(event: EventStreamEvent) -> None:
                received.append("a")

            async def handler_b(event: EventStreamEvent) -> None:
                received.append("b")

            await bus.subscribe("sa", "type.a", handler_a)
            await bus.subscribe("sb", "type.b", handler_b)

            await bus.publish(make_event("type.a"))
            await bus.publish(make_event("type.b"))
            await asyncio.sleep(0.05)

            assert received == ["a", "b"]

            await bus.stop()

        asyncio.run(exercise())
