"""Stream publisher for the event streaming layer.

Provides the publishing interface that integrates with the MarketDataManager
via the MarketDataPublisher protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.market import MarketDataSnapshot
from libraries.domain.market.interfaces import MarketDataPublisher
from libraries.infrastructure.event_stream.event_bus import EventBus
from libraries.infrastructure.event_stream.event_types import (
    EventStreamEvent,
    SnapshotPublishedEvent,
    TickReceivedEvent,
)


@dataclass(frozen=True, slots=True)
class PublisherStats:
    """Statistics for a stream publisher."""

    publisher_id: str
    total_published: int
    total_errors: int
    last_publish_time: str | None
    last_error_time: str | None
    last_error_message: str | None


class StreamPublisher(MarketDataPublisher):
    """Stream publisher that bridges MarketDataManager to the event bus.

    Implements the MarketDataPublisher protocol, converting accepted
    MarketDataSnapshot into stream events and publishing them to the bus.

    Multiple publisher instances can operate on the same bus.
    """

    def __init__(
        self,
        publisher_id: str,
        bus: EventBus,
    ) -> None:
        self._publisher_id = publisher_id
        self._bus = bus
        self._total_published: int = 0
        self._total_errors: int = 0
        self._last_publish_time: datetime | None = None
        self._last_error_time: datetime | None = None
        self._last_error_message: str | None = None

    @property
    def publisher_id(self) -> str:
        return self._publisher_id

    async def publish(self, snapshot: MarketDataSnapshot) -> None:
        """Publish a market data snapshot to the event bus.

        Args:
            snapshot: The accepted market data snapshot.

        Raises:
            Any exception from the event bus is caught and tracked
            to maintain error isolation.
        """
        try:
            # Create tick event
            tick_event = TickReceivedEvent.create(
                symbol=snapshot.tick.symbol,
                provider=snapshot.tick.source,
                bid=str(snapshot.tick.bid),
                ask=str(snapshot.tick.ask),
                source=self._publisher_id,
            )
            await self._bus.publish(tick_event)

            # Create snapshot event
            snapshot_event = SnapshotPublishedEvent.create(
                symbol=snapshot.tick.symbol,
                accepted_sequence=snapshot.accepted_sequence,
                source=self._publisher_id,
            )
            await self._bus.publish(snapshot_event)

            self._total_published += 1
            self._last_publish_time = datetime.now(timezone.utc)

        except Exception as exc:
            self._total_errors += 1
            self._last_error_time = datetime.now(timezone.utc)
            self._last_error_message = str(exc)

    async def get_stats(self) -> PublisherStats:
        """Return publisher statistics."""
        return PublisherStats(
            publisher_id=self._publisher_id,
            total_published=self._total_published,
            total_errors=self._total_errors,
            last_publish_time=(
                self._last_publish_time.isoformat() if self._last_publish_time else None
            ),
            last_error_time=(self._last_error_time.isoformat() if self._last_error_time else None),
            last_error_message=self._last_error_message,
        )
