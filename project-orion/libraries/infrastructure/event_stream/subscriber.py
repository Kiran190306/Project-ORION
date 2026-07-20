"""Stream subscriber for the event streaming layer.

Provides async callback-based subscribers with error isolation for
consuming events from the event bus.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from libraries.infrastructure.event_stream.event_bus import (
    EventBus,
    EventSubscription,
)
from libraries.infrastructure.event_stream.event_types import EventStreamEvent


class SubscriberCallbackError(Exception):
    """Raised when a subscriber callback fails."""


@dataclass(frozen=True, slots=True)
class SubscriberStats:
    """Statistics for a stream subscriber."""

    subscriber_id: str
    event_type: str
    total_received: int
    total_errors: int
    last_event_time: str | None
    last_error_time: str | None
    last_error_message: str | None
    active: bool


class StreamSubscriber:
    """Async subscriber for stream events.

    Supports:
    - Event type filtering
    - Async callbacks
    - Error isolation
    - Statistics tracking

    Multiple subscriber instances can coexist on the same bus.
    """

    def __init__(
        self,
        subscriber_id: str,
        bus: EventBus,
        event_type: str,
        callback: Callable[[EventStreamEvent], Coroutine[Any, Any, None] | None],
    ) -> None:
        self._subscriber_id = subscriber_id
        self._bus = bus
        self._event_type = event_type
        self._callback = callback
        self._subscription: EventSubscription | None = None
        self._total_received: int = 0
        self._total_errors: int = 0
        self._last_event_time: datetime | None = None
        self._last_error_time: datetime | None = None
        self._last_error_message: str | None = None
        self._active = False

    @property
    def subscriber_id(self) -> str:
        return self._subscriber_id

    @property
    def event_type(self) -> str:
        return self._event_type

    @property
    def active(self) -> bool:
        return self._active

    async def start(self) -> None:
        """Start the subscriber by subscribing to the bus."""
        if self._active:
            return

        self._subscription = await self._bus.subscribe(
            subscriber_id=self._subscriber_id,
            event_type=self._event_type,
            callback=self._handle_event,
        )
        self._active = True

    async def stop(self) -> None:
        """Stop the subscriber by unsubscribing from the bus."""
        if not self._active:
            return

        if self._subscription is not None:
            await self._bus.unsubscribe(self._subscription)
        self._subscription = None
        self._active = False

    async def _handle_event(
        self,
        event: EventStreamEvent,
    ) -> None:
        """Internal handler that wraps the user callback with error isolation."""
        try:
            result = self._callback(event)
            if asyncio.iscoroutine(result):
                await result
            self._total_received += 1
            self._last_event_time = datetime.now(timezone.utc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._total_errors += 1
            self._last_error_time = datetime.now(timezone.utc)
            self._last_error_message = str(exc)

    async def get_stats(self) -> SubscriberStats:
        """Return subscriber statistics."""
        return SubscriberStats(
            subscriber_id=self._subscriber_id,
            event_type=self._event_type,
            total_received=self._total_received,
            total_errors=self._total_errors,
            last_event_time=(self._last_event_time.isoformat() if self._last_event_time else None),
            last_error_time=(self._last_error_time.isoformat() if self._last_error_time else None),
            last_error_message=self._last_error_message,
            active=self._active,
        )
