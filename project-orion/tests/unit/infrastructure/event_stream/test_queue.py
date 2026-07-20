"""Tests for PriorityQueue."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.event_types import (
    EventPriority,
    EventStreamEvent,
)
from libraries.infrastructure.event_stream.queue import PriorityQueue


def make_event(priority: EventPriority = EventPriority.NORMAL) -> EventStreamEvent:
    return EventStreamEvent(
        event_type="test.event",
        priority=priority,
    )


class TestPriorityQueue:
    def test_put_and_get_respects_priority(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            await q.put(make_event(EventPriority.LOW))
            await q.put(make_event(EventPriority.HIGH))
            await q.put(make_event(EventPriority.CRITICAL))

            e1 = await q.get()
            e2 = await q.get()
            e3 = await q.get()

            assert e1.priority == EventPriority.CRITICAL
            assert e2.priority == EventPriority.HIGH
            assert e3.priority == EventPriority.LOW

        asyncio.run(exercise())

    def test_qsize_tracks_put_and_get(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            assert await q.is_empty()

            await q.put(make_event())
            assert q.qsize == 1
            assert not await q.is_empty()

            await q.get()
            assert q.qsize == 0

        asyncio.run(exercise())

    def test_bounded_queue_drops_on_overflow(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue(maxsize=2)

            r1 = await q.put(make_event())
            r2 = await q.put(make_event())
            r3 = await q.put(make_event())

            assert r1
            assert r2
            assert not r3
            assert q.total_dropped == 1
            assert q.qsize == 2

        asyncio.run(exercise())

    def test_get_nowait_returns_none_when_empty(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            result = await q.get_nowait()
            assert result is None

        asyncio.run(exercise())

    def test_get_nowait_returns_event_when_available(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            await q.put(make_event())
            result = await q.get_nowait()
            assert result is not None
            assert result.event_type == "test.event"

        asyncio.run(exercise())

    def test_peek_returns_event_without_removing(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            await q.put(make_event(EventPriority.HIGH))
            peeked = await q.peek()
            assert peeked is not None
            assert peeked.priority == EventPriority.HIGH
            assert q.qsize == 1

        asyncio.run(exercise())

    def test_clear_empties_queue(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            await q.put(make_event())
            await q.put(make_event())
            cleared = await q.clear()
            assert cleared == 2
            assert q.qsize == 0

        asyncio.run(exercise())

    def test_put_blocking_waits_until_space(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue(maxsize=1)
            await q.put(make_event())

            async def delayed_get() -> None:
                await asyncio.sleep(0.05)
                await q.get()

            async def blocking_put() -> None:
                await q.put_blocking(make_event())
                assert q.qsize == 1

            await asyncio.gather(blocking_put(), delayed_get())

        asyncio.run(exercise())

    def test_unbounded_queue_never_drops(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()  # maxsize=0 = unbounded
            for _ in range(100):
                await q.put(make_event())
            assert q.total_dropped == 0
            assert q.qsize == 100

        asyncio.run(exercise())

    def test_priority_ordering_within_same_priority(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            e1 = make_event(EventPriority.NORMAL)
            e2 = make_event(EventPriority.NORMAL)
            e3 = make_event(EventPriority.NORMAL)

            await q.put(e1)
            await q.put(e2)
            await q.put(e3)

            # Same priority = FIFO within priority level
            r1 = await q.get()
            r2 = await q.get()
            r3 = await q.get()
            assert r1 is e1
            assert r2 is e2
            assert r3 is e3

        asyncio.run(exercise())

    def test_is_full_detects_capacity(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue(maxsize=2)
            assert not await q.is_full()

            await q.put(make_event())
            assert not await q.is_full()

            await q.put(make_event())
            assert await q.is_full()

        asyncio.run(exercise())

    def test_totals_tracking(self) -> None:
        async def exercise() -> None:
            q = PriorityQueue()
            assert q.total_put == 0
            assert q.total_get == 0
            assert q.total_dropped == 0

            await q.put(make_event())
            assert q.total_put == 1

            await q.get()
            assert q.total_get == 1

        asyncio.run(exercise())
