"""Configurable stream buffer for the event streaming layer.

Provides a bounded FIFO buffer with configurable overflow policies,
supporting market data stream buffering between producers and consumers.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.infrastructure.event_stream.event_types import (
    BufferDroppedEvent,
    EventStreamEvent,
    QueueDepthEvent,
)


class BufferOverflowPolicy(StrEnum):
    """Policy for handling buffer overflow."""

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class BufferMetrics:
    """Snapshot of buffer metrics."""

    current_size: int
    max_size: int
    total_enqueued: int
    total_dequeued: int
    total_dropped: int
    oldest_timestamp: str | None
    newest_timestamp: str | None


class StreamBuffer:
    """Bounded FIFO buffer for streaming events.

    Supports:
    - Configurable max size
    - Overflow policies: drop oldest, drop newest, block
    - Metrics collection (enqueue/dequeue/drop counts)
    - Timestamp tracking
    """

    def __init__(
        self,
        maxsize: int = 10000,
        overflow_policy: BufferOverflowPolicy = BufferOverflowPolicy.DROP_OLDEST,
    ) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._overflow_policy = overflow_policy
        self._buffer: deque[EventStreamEvent] = deque(maxlen=maxsize)
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._total_enqueued: int = 0
        self._total_dequeued: int = 0
        self._total_dropped: int = 0
        self._oldest_timestamp: datetime | None = None
        self._newest_timestamp: datetime | None = None
        self._dropped_events: list[BufferDroppedEvent] = []

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def overflow_policy(self) -> BufferOverflowPolicy:
        return self._overflow_policy

    @property
    def total_enqueued(self) -> int:
        return self._total_enqueued

    @property
    def total_dequeued(self) -> int:
        return self._total_dequeued

    @property
    def total_dropped(self) -> int:
        return self._total_dropped

    async def qsize(self) -> int:
        """Return the current number of items in the buffer."""
        async with self._lock:
            return len(self._buffer)

    async def is_empty(self) -> bool:
        """Return True if the buffer is empty."""
        async with self._lock:
            return not self._buffer

    async def is_full(self) -> bool:
        """Return True if the buffer is at capacity."""
        async with self._lock:
            return len(self._buffer) >= self._maxsize

    async def enqueue(self, event: EventStreamEvent) -> bool:
        """Add an event to the buffer.

        Args:
            event: Event to buffer.

        Returns:
            True if enqueued, False if dropped.
        """
        async with self._lock:
            if len(self._buffer) >= self._maxsize:
                if self._overflow_policy == BufferOverflowPolicy.BLOCK:
                    while len(self._buffer) >= self._maxsize:
                        await self._not_full.wait()
                elif self._overflow_policy == BufferOverflowPolicy.DROP_OLDEST:
                    dropped = self._buffer.popleft()
                    self._total_dropped += 1
                    self._dropped_events.append(
                        BufferDroppedEvent.create(
                            symbol=dropped.payload.get("symbol", ""),
                            queue_depth=len(self._buffer),
                        )
                    )
                elif self._overflow_policy == BufferOverflowPolicy.DROP_NEWEST:
                    self._total_dropped += 1
                    self._dropped_events.append(
                        BufferDroppedEvent.create(
                            symbol=event.payload.get("symbol", ""),
                            queue_depth=len(self._buffer),
                        )
                    )
                    return False

            now = datetime.now(timezone.utc)
            self._buffer.append(event)
            self._total_enqueued += 1
            if self._oldest_timestamp is None:
                self._oldest_timestamp = now
            self._newest_timestamp = now
            self._not_empty.notify()
            return True

    async def dequeue(self) -> EventStreamEvent:
        """Remove and return the oldest event from the buffer.

        Blocks until an event is available.
        """
        async with self._lock:
            while not self._buffer:
                await self._not_empty.wait()

            event = self._buffer.popleft()
            self._total_dequeued += 1
            if self._maxsize > 0:
                self._not_full.notify()

            if not self._buffer:
                self._oldest_timestamp = None
                self._newest_timestamp = None

            return event

    async def dequeue_nowait(self) -> EventStreamEvent | None:
        """Remove and return the oldest event, or None if empty."""
        async with self._lock:
            if not self._buffer:
                return None
            event = self._buffer.popleft()
            self._total_dequeued += 1
            if self._maxsize > 0:
                self._not_full.notify()
            return event

    async def peek(self) -> EventStreamEvent | None:
        """Return the oldest event without removing it."""
        async with self._lock:
            if not self._buffer:
                return None
            return self._buffer[0]

    async def clear(self) -> int:
        """Remove all items from the buffer.

        Returns:
            Number of items cleared.
        """
        async with self._lock:
            count = len(self._buffer)
            self._buffer.clear()
            self._oldest_timestamp = None
            self._newest_timestamp = None
            if self._maxsize > 0:
                self._not_full.notify_all()
            return count

    async def get_metrics(self) -> BufferMetrics:
        """Return a snapshot of current buffer metrics."""
        async with self._lock:
            return BufferMetrics(
                current_size=len(self._buffer),
                max_size=self._maxsize,
                total_enqueued=self._total_enqueued,
                total_dequeued=self._total_dequeued,
                total_dropped=self._total_dropped,
                oldest_timestamp=(
                    self._oldest_timestamp.isoformat() if self._oldest_timestamp else None
                ),
                newest_timestamp=(
                    self._newest_timestamp.isoformat() if self._newest_timestamp else None
                ),
            )

    async def flush(self) -> list[EventStreamEvent]:
        """Remove and return all events currently in the buffer.

        Returns:
            List of all buffered events in FIFO order.
        """
        async with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
            self._oldest_timestamp = None
            self._newest_timestamp = None
            self._total_dequeued += len(events)
            if self._maxsize > 0:
                self._not_full.notify_all()
            return events

    def pop_dropped_events(self) -> list[BufferDroppedEvent]:
        """Return and clear accumulated drop notification events."""
        events = list(self._dropped_events)
        self._dropped_events.clear()
        return events
