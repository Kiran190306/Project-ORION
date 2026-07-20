"""Priority-based async queue for the event streaming layer.

Provides an asyncio-compatible priority queue that supports EventPriority
levels for ordering market data events.
"""

from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import Any

from libraries.infrastructure.event_stream.event_types import (
    EventPriority,
    EventStreamEvent,
)


@dataclass(frozen=True, slots=True)
class PriorityQueueItem:
    """Wrapper for priority queue ordering.

    Lower priority value = higher priority.
    """

    priority: int
    sequence: int
    event: EventStreamEvent

    def __lt__(self, other: PriorityQueueItem) -> bool:
        if self.priority == other.priority:
            return self.sequence < other.sequence
        return self.priority < other.priority


class PriorityQueue:
    """Async priority queue for streaming events.

    Supports:
    - Priority-based ordering via EventPriority
    - Bounded capacity
    - Non-blocking put with overflow detection
    - Queue depth monitoring
    """

    def __init__(self, maxsize: int = 0) -> None:
        self._maxsize = maxsize
        self._queue: list[PriorityQueueItem] = []
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._total_put: int = 0
        self._total_get: int = 0
        self._total_dropped: int = 0

    @property
    def maxsize(self) -> int:
        """Return the maximum queue size (0 = unbounded)."""
        return self._maxsize

    @property
    def qsize(self) -> int:
        """Return the approximate number of items in the queue."""
        return len(self._queue)

    @property
    def total_put(self) -> int:
        """Total number of items ever put into the queue."""
        return self._total_put

    @property
    def total_get(self) -> int:
        """Total number of items ever retrieved from the queue."""
        return self._total_get

    @property
    def total_dropped(self) -> int:
        """Total number of items dropped due to overflow."""
        return self._total_dropped

    def _priority_value(self, priority: EventPriority) -> int:
        """Map EventPriority to integer for heap ordering."""
        mapping = {
            EventPriority.CRITICAL: 0,
            EventPriority.HIGH: 1,
            EventPriority.NORMAL: 2,
            EventPriority.LOW: 3,
        }
        return mapping.get(priority, 2)

    async def put(self, event: EventStreamEvent) -> bool:
        """Put an event into the queue.

        Args:
            event: Event to enqueue.

        Returns:
            True if the event was enqueued, False if dropped (overflow).
        """
        async with self._lock:
            if self._maxsize > 0 and len(self._queue) >= self._maxsize:
                self._total_dropped += 1
                return False

            self._sequence += 1
            priority_val = self._priority_value(event.priority)
            item = PriorityQueueItem(
                priority=priority_val,
                sequence=self._sequence,
                event=event,
            )
            heapq.heappush(self._queue, item)
            self._total_put += 1
            self._not_empty.notify()
            return True

    async def put_blocking(self, event: EventStreamEvent) -> None:
        """Put an event into the queue, blocking if full.

        Args:
            event: Event to enqueue.
        """
        async with self._lock:
            while self._maxsize > 0 and len(self._queue) >= self._maxsize:
                await self._not_full.wait()

            self._sequence += 1
            priority_val = self._priority_value(event.priority)
            item = PriorityQueueItem(
                priority=priority_val,
                sequence=self._sequence,
                event=event,
            )
            heapq.heappush(self._queue, item)
            self._total_put += 1
            self._not_empty.notify()

    async def get(self) -> EventStreamEvent:
        """Get the highest-priority event from the queue.

        Blocks until an item is available.
        """
        async with self._lock:
            while not self._queue:
                await self._not_empty.wait()

            item = heapq.heappop(self._queue)
            self._total_get += 1
            if self._maxsize > 0:
                self._not_full.notify()
            return item.event

    async def get_nowait(self) -> EventStreamEvent | None:
        """Get the highest-priority event if available, without blocking.

        Returns:
            Event if available, None if queue is empty.
        """
        async with self._lock:
            if not self._queue:
                return None
            item = heapq.heappop(self._queue)
            self._total_get += 1
            if self._maxsize > 0:
                self._not_full.notify()
            return item.event

    async def peek(self) -> EventStreamEvent | None:
        """Return the highest-priority event without removing it.

        Returns:
            Event if available, None if queue is empty.
        """
        async with self._lock:
            if not self._queue:
                return None
            return self._queue[0].event

    async def clear(self) -> int:
        """Remove all items from the queue.

        Returns:
            Number of items cleared.
        """
        async with self._lock:
            count = len(self._queue)
            self._queue.clear()
            if self._maxsize > 0:
                self._not_full.notify_all()
            return count

    async def is_empty(self) -> bool:
        """Return True if the queue is empty."""
        async with self._lock:
            return not self._queue

    async def is_full(self) -> bool:
        """Return True if the queue is at capacity."""
        async with self._lock:
            if self._maxsize <= 0:
                return False
            return len(self._queue) >= self._maxsize
