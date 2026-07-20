"""Priority event bus for the event streaming layer.

Extends the existing infrastructure event bus with priority-based delivery,
fan-out, dead-letter queue, and error isolation.

Designed to be extensible for Kafka, Redis Streams, NATS, RabbitMQ, and
ZeroMQ by implementing the EventBus interface.
"""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from libraries.infrastructure.event_stream.event_types import (
    ErrorIsolatedEvent,
    EventPriority,
    EventStreamEvent,
)
from libraries.infrastructure.event_stream.queue import PriorityQueue


class EventBusError(Exception):
    """Raised when event bus operations fail."""


class EventSubscription:
    """Represents a subscription to the event bus.

    Provides a handle for unsubscribing and tracking.
    """

    def __init__(
        self,
        subscriber_id: str,
        event_type: str,
        callback: Callable[[EventStreamEvent], Coroutine[Any, Any, None] | None],
    ) -> None:
        self.subscriber_id = subscriber_id
        self.event_type = event_type
        self.callback = callback
        self.created_at = datetime.now(timezone.utc)
        self.delivery_count: int = 0
        self.error_count: int = 0


class EventBus(ABC):
    """Abstract event bus interface.

    Implementations: InMemoryPriorityBus, KafkaEventBus, RedisStreamBus,
    NATSEventBus, RabbitMQEventBus, ZeroMQEventBus
    """

    @abstractmethod
    async def publish(self, event: EventStreamEvent) -> None:
        """Publish an event to all matching subscribers."""
        ...

    @abstractmethod
    async def subscribe(
        self,
        subscriber_id: str,
        event_type: str,
        callback: Callable[[EventStreamEvent], Coroutine[Any, Any, None] | None],
    ) -> EventSubscription:
        """Subscribe to an event type."""
        ...

    @abstractmethod
    async def unsubscribe(self, subscription: EventSubscription) -> None:
        """Unsubscribe from an event type."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus."""
        ...

    @abstractmethod
    async def get_dead_letter_count(self) -> int:
        """Return the number of events in the dead-letter queue."""
        ...


@dataclass(frozen=True, slots=True)
class DeadLetterEvent:
    """An event that failed delivery and was routed to the dead-letter queue."""

    event: EventStreamEvent
    subscriber_id: str
    error: str
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0


class InMemoryPriorityBus(EventBus):
    """In-memory priority event bus implementation.

    Supports:
    - Multiple publishers
    - Multiple subscribers per event type
    - Fan-out delivery (all subscribers receive each event)
    - Async callbacks
    - Priority events (higher priority delivered first)
    - Dead-letter queue for failed deliveries
    - Error isolation (subscriber failure doesn't affect others)
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        max_dead_letter: int = 1000,
    ) -> None:
        self._queue = PriorityQueue(maxsize=max_queue_size)
        self._subscriptions: dict[str, list[EventSubscription]] = {}
        self._dead_letter: list[DeadLetterEvent] = []
        self._max_dead_letter = max_dead_letter
        self._running = False
        self._worker_task: asyncio.Task[None] | None = None
        self._cancel_event = asyncio.Event()
        self._dispatched_count: int = 0
        self._failed_count: int = 0

    async def publish(self, event: EventStreamEvent) -> None:
        """Publish an event to the bus.

        Args:
            event: Event to publish.

        Raises:
            EventBusError: If the bus is not running.
        """
        if not self._running:
            raise EventBusError("Event bus is not running")

        enqueued = await self._queue.put(event)
        if not enqueued:
            # Queue full - route to dead letter
            async with self._queue._lock:
                pass
            self._route_to_dead_letter(
                DeadLetterEvent(
                    event=event,
                    subscriber_id="__bus__",
                    error="Queue full, event dropped",
                )
            )

    async def subscribe(
        self,
        subscriber_id: str,
        event_type: str,
        callback: Callable[[EventStreamEvent], Coroutine[Any, Any, None] | None],
    ) -> EventSubscription:
        """Subscribe to an event type.

        Supports wildcard patterns: "tick.*" matches "tick.received", etc.

        Args:
            subscriber_id: Stable subscriber identifier.
            event_type: Event type or pattern to subscribe to.
            callback: Async callback to invoke on matching events.

        Returns:
            EventSubscription handle for unsubscribing.
        """
        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            event_type=event_type,
            callback=callback,
        )
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []
        self._subscriptions[event_type].append(subscription)
        return subscription

    async def unsubscribe(self, subscription: EventSubscription) -> None:
        """Unsubscribe from an event type."""
        subs = self._subscriptions.get(subscription.event_type, [])
        if subscription in subs:
            subs.remove(subscription)

    async def start(self) -> None:
        """Start the event bus worker."""
        if self._running:
            return
        self._running = True
        self._cancel_event.clear()
        self._worker_task = asyncio.create_task(self._delivery_loop())

    async def stop(self) -> None:
        """Stop the event bus worker."""
        self._running = False
        self._cancel_event.set()
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def get_dead_letter_count(self) -> int:
        """Return the number of events in the dead-letter queue."""
        return len(self._dead_letter)

    def get_dead_letter_events(self) -> list[DeadLetterEvent]:
        """Return and clear dead-letter events."""
        events = list(self._dead_letter)
        self._dead_letter.clear()
        return events

    async def get_subscriptions(self, event_type: str) -> list[EventSubscription]:
        """Get all subscriptions matching an event type (including wildcards)."""
        subs: list[EventSubscription] = []

        # Direct matches
        if event_type in self._subscriptions:
            subs.extend(self._subscriptions[event_type])

        # Wildcard matches (e.g., "tick.*" matches "tick.received")
        for pattern, pattern_subs in self._subscriptions.items():
            if pattern.endswith(".*") and event_type.startswith(pattern[:-1]):
                subs.extend(pattern_subs)

        return subs

    async def _delivery_loop(self) -> None:
        """Main delivery loop processing events from the priority queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                await self._deliver(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    async def _deliver(self, event: EventStreamEvent) -> None:
        """Deliver an event to all matching subscribers."""
        subs = await self.get_subscriptions(event.event_type)
        if not subs:
            return

        for sub in subs:
            try:
                result = sub.callback(event)
                if inspect.isawaitable(result):
                    await result
                sub.delivery_count += 1
                self._dispatched_count += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                sub.error_count += 1
                self._failed_count += 1
                error_msg = f"{type(exc).__name__}: {exc}"
                self._route_to_dead_letter(
                    DeadLetterEvent(
                        event=event,
                        subscriber_id=sub.subscriber_id,
                        error=error_msg,
                    )
                )
                # Emit error isolation event
                await self._emit_error_isolation(sub.subscriber_id, error_msg)

    def _route_to_dead_letter(self, dead_letter: DeadLetterEvent) -> None:
        """Route a failed event to the dead-letter queue."""
        if len(self._dead_letter) >= self._max_dead_letter:
            self._dead_letter.pop(0)
        self._dead_letter.append(dead_letter)

    async def _emit_error_isolation(self, subscriber_id: str, error_message: str) -> None:
        """Emit an error isolation event."""
        error_event = ErrorIsolatedEvent.create(
            subscriber_id=subscriber_id,
            error_message=error_message,
        )
        # Recursive publish to notify monitoring
        subs = await self.get_subscriptions(error_event.event_type)
        for sub in subs:
            try:
                result = sub.callback(error_event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                pass


class PriorityEventBus:
    """High-level facade wrapping EventBus with priority support.

    Provides a simpler API for publishing events with priority levels
    and subscribing with automatic event type extraction.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def publish(self, event: EventStreamEvent) -> None:
        """Publish an event with its priority."""
        await self._bus.publish(event)

    async def subscribe(
        self,
        subscriber_id: str,
        event_type: str,
        callback: Callable[[EventStreamEvent], Coroutine[Any, Any, None] | None],
    ) -> EventSubscription:
        """Subscribe to an event type."""
        return await self._bus.subscribe(subscriber_id, event_type, callback)

    async def unsubscribe(self, subscription: EventSubscription) -> None:
        """Unsubscribe."""
        await self._bus.unsubscribe(subscription)

    async def start(self) -> None:
        """Start the underlying bus."""
        await self._bus.start()

    async def stop(self) -> None:
        """Stop the underlying bus."""
        await self._bus.stop()
