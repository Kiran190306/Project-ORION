"""Tests for StreamBuffer."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.buffer import (
    BufferOverflowPolicy,
    StreamBuffer,
)
from libraries.infrastructure.event_stream.event_types import EventStreamEvent


def make_event(event_type: str = "test.event") -> EventStreamEvent:
    return EventStreamEvent(event_type=event_type)


class TestStreamBuffer:
    def test_enqueue_and_dequeue_fifo(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=10)
            e1 = make_event("event.1")
            e2 = make_event("event.2")

            r1 = await buf.enqueue(e1)
            r2 = await buf.enqueue(e2)
            assert r1 and r2

            d1 = await buf.dequeue()
            d2 = await buf.dequeue()
            assert d1 is e1
            assert d2 is e2

        asyncio.run(exercise())

    def test_drop_oldest_policy(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=2, overflow_policy=BufferOverflowPolicy.DROP_OLDEST)

            await buf.enqueue(make_event("event.1"))
            await buf.enqueue(make_event("event.2"))
            # This should drop event.1
            await buf.enqueue(make_event("event.3"))

            assert buf.total_dropped == 1
            d1 = await buf.dequeue()
            assert d1.event_type == "event.2"
            d2 = await buf.dequeue()
            assert d2.event_type == "event.3"

        asyncio.run(exercise())

    def test_drop_newest_policy(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=2, overflow_policy=BufferOverflowPolicy.DROP_NEWEST)

            await buf.enqueue(make_event("event.1"))
            await buf.enqueue(make_event("event.2"))
            # This should be dropped
            result = await buf.enqueue(make_event("event.3"))

            assert not result
            assert buf.total_dropped == 1
            assert await buf.qsize() == 2

        asyncio.run(exercise())

    def test_blocking_policy(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=1, overflow_policy=BufferOverflowPolicy.BLOCK)

            await buf.enqueue(make_event())

            async def delayed_dequeue() -> None:
                await asyncio.sleep(0.05)
                await buf.dequeue()

            async def blocking_enqueue() -> None:
                result = await buf.enqueue(make_event("blocked"))
                assert result

            await asyncio.gather(blocking_enqueue(), delayed_dequeue())

        asyncio.run(exercise())

    def test_peek_returns_without_removing(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=10)
            await buf.enqueue(make_event("peek"))
            peeked = await buf.peek()
            assert peeked is not None
            assert peeked.event_type == "peek"
            assert await buf.qsize() == 1

        asyncio.run(exercise())

    def test_dequeue_nowait_empty(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=10)
            result = await buf.dequeue_nowait()
            assert result is None

        asyncio.run(exercise())

    def test_clear_empties_buffer(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=10)
            await buf.enqueue(make_event())
            await buf.enqueue(make_event())

            cleared = await buf.clear()
            assert cleared == 2
            assert await buf.is_empty()

        asyncio.run(exercise())

    def test_get_metrics_snapshot(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=100)
            await buf.enqueue(make_event())
            await buf.enqueue(make_event())
            await buf.dequeue()

            metrics = await buf.get_metrics()
            assert metrics.current_size == 1
            assert metrics.max_size == 100
            assert metrics.total_enqueued == 2
            assert metrics.total_dequeued == 1

        asyncio.run(exercise())

    def test_flush_returns_all_events(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=10)
            await buf.enqueue(make_event("flush.1"))
            await buf.enqueue(make_event("flush.2"))

            events = await buf.flush()
            assert len(events) == 2
            assert events[0].event_type == "flush.1"
            assert await buf.is_empty()

        asyncio.run(exercise())

    def test_pop_dropped_events(self) -> None:
        async def exercise() -> None:
            buf = StreamBuffer(maxsize=1, overflow_policy=BufferOverflowPolicy.DROP_OLDEST)
            await buf.enqueue(make_event())
            await buf.enqueue(make_event())

            dropped = buf.pop_dropped_events()
            assert len(dropped) == 1
            assert dropped[0].event_type == "buffer.dropped"

        asyncio.run(exercise())

    def test_validates_maxsize(self) -> None:
        with pytest.raises(ValueError):
            StreamBuffer(maxsize=0)

    def test_maxsize_property(self) -> None:
        buf = StreamBuffer(maxsize=500)
        assert buf.maxsize == 500
        assert buf.overflow_policy == BufferOverflowPolicy.DROP_OLDEST
