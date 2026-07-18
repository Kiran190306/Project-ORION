"""
Project ORION - Event Bus Abstraction

Abstract event bus interface and in-memory implementation.
Supports publish/subscribe pattern with topic routing.

Provides:
- Event bus interface
- In-memory event bus (default)
- Topic-based subscriptions
- Async event handling
"""

from __future__ import annotations

import asyncio
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from libraries.infrastructure.logging import get_logger
from shared.events import DomainEvent

logger = get_logger("infrastructure.event_bus")

EventHandlerFn = Callable[[DomainEvent], Any]


class EventBusError(Exception):
    """Raised when event bus operations fail."""

    pass


@dataclass
class Subscription:
    """A subscription to a specific event type."""

    topic: str
    handler: EventHandlerFn
    handler_name: str = ""

    def __post_init__(self) -> None:
        if not self.handler_name:
            self.handler_name = getattr(self.handler, "__name__", "unknown")


class EventBus(ABC):
    """Abstract event bus interface."""

    @abstractmethod
    async def publish(self, topic: str, event: DomainEvent) -> None:
        """Publish an event to a topic."""
        ...

    @abstractmethod
    def subscribe(self, topic: str, handler: EventHandlerFn) -> Subscription:
        """Subscribe a handler to a topic."""
        ...

    @abstractmethod
    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe a handler."""
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start the event bus."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus."""
        ...


class InMemoryEventBus(EventBus):
    """
    In-memory event bus implementation for development and testing.

    Events are delivered synchronously (not persisted).
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._subscriptions: dict[str, list[Subscription]] = {}
        self._queue: asyncio.Queue[tuple[str, DomainEvent]] = asyncio.Queue(maxsize=max_queue_size)
        self._running = False
        self._worker_task: Optional[asyncio.Task[None]] = None

    async def publish(self, topic: str, event: DomainEvent) -> None:
        """
        Publish an event to a topic.

        Args:
            topic: Topic/channel name.
            event: Domain event to publish.

        Raises:
            EventBusError: If queue is full.
        """
        try:
            await self._queue.put((topic, event))
        except asyncio.QueueFull:
            raise EventBusError(f"Event bus queue is full (max={self._queue.maxsize})")

        logger.debug(
            "Published event %s to topic %s (event_id=%s)",
            event.event_type,
            topic,
            event.event_id,
        )

    def subscribe(self, topic: str, handler: EventHandlerFn) -> Subscription:
        """
        Subscribe a handler to a topic.

        Args:
            topic: Topic to subscribe to (supports wildcard: "market.*").
            handler: Handler function.

        Returns:
            Subscription object for unsubscribing.
        """
        sub = Subscription(topic=topic, handler=handler)

        if topic not in self._subscriptions:
            self._subscriptions[topic] = []

        self._subscriptions[topic].append(sub)
        logger.debug(
            "Subscribed %s to topic %s",
            sub.handler_name,
            topic,
        )
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        """Unsubscribe a handler from its topic."""
        subs = self._subscriptions.get(subscription.topic, [])
        if subscription in subs:
            subs.remove(subscription)
            logger.debug(
                "Unsubscribed %s from topic %s",
                subscription.handler_name,
                subscription.topic,
            )

    def get_subscriptions(self, topic: str) -> list[Subscription]:
        """Get all subscriptions matching a topic (including wildcards)."""
        subs: list[Subscription] = []

        # Direct matches
        if topic in self._subscriptions:
            subs.extend(self._subscriptions[topic])

        # Wildcard matches
        for pattern, pattern_subs in self._subscriptions.items():
            if pattern.endswith(".*") and topic.startswith(pattern[:-1]):
                subs.extend(pattern_subs)

        return subs

    async def start(self) -> None:
        """Start the event bus worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("In-memory event bus started")

    async def stop(self) -> None:
        """Stop the event bus worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("In-memory event bus stopped")

    async def _worker_loop(self) -> None:
        """Worker loop that processes queued events."""
        while self._running:
            try:
                topic, event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._deliver(topic, event)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Event bus worker error: %s", exc)

    async def _deliver(self, topic: str, event: DomainEvent) -> None:
        """Deliver an event to all matching subscribers."""
        subs = self.get_subscriptions(topic)
        if not subs:
            logger.debug("No subscribers for topic %s", topic)
            return

        for sub in subs:
            try:
                result = sub.handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                logger.error(
                    "Handler %s failed for event %s: %s",
                    sub.handler_name,
                    event.event_id,
                    exc,
                )


# ─── Singleton ────────────────────────────────────────────────

_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _bus
    if _bus is None:
        _bus = InMemoryEventBus()
    return _bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus instance."""
    global _bus
    _bus = bus


def reset_event_bus() -> None:
    """Reset the global event bus (for testing)."""
    global _bus
    _bus = None
