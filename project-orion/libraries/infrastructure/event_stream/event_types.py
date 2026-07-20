"""Event types for the production streaming layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EventPriority(StrEnum):
    """Priority levels for stream events."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class EventStreamEvent:
    """Base event for the streaming layer."""

    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "payload": self.payload,
            "priority": self.priority.value,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class TickReceivedEvent(EventStreamEvent):
    """Emitted when a raw tick arrives from a connector."""

    symbol: str = ""
    provider: str = ""
    bid: str = ""
    ask: str = ""

    @classmethod
    def create(
        cls,
        symbol: str,
        provider: str,
        bid: str,
        ask: str,
        source: str = "connector",
    ) -> TickReceivedEvent:
        return cls(
            event_type="tick.received",
            source=source,
            symbol=symbol,
            provider=provider,
            bid=bid,
            ask=ask,
            payload={"symbol": symbol, "provider": provider, "bid": bid, "ask": ask},
        )


@dataclass(frozen=True, slots=True)
class SnapshotPublishedEvent(EventStreamEvent):
    """Emitted when a validated snapshot is published."""

    symbol: str = ""
    accepted_sequence: int = 0

    @classmethod
    def create(
        cls,
        symbol: str,
        accepted_sequence: int,
        source: str = "stream",
    ) -> SnapshotPublishedEvent:
        return cls(
            event_type="snapshot.published",
            source=source,
            symbol=symbol,
            accepted_sequence=accepted_sequence,
            payload={
                "symbol": symbol,
                "accepted_sequence": accepted_sequence,
            },
        )


@dataclass(frozen=True, slots=True)
class BufferDroppedEvent(EventStreamEvent):
    """Emitted when a buffer drops an event due to overflow."""

    symbol: str = ""
    queue_depth: int = 0

    @classmethod
    def create(
        cls,
        symbol: str,
        queue_depth: int,
        source: str = "buffer",
    ) -> BufferDroppedEvent:
        return cls(
            event_type="buffer.dropped",
            source=source,
            symbol=symbol,
            queue_depth=queue_depth,
            payload={"symbol": symbol, "queue_depth": queue_depth},
        )


@dataclass(frozen=True, slots=True)
class QueueDepthEvent(EventStreamEvent):
    """Emitted periodically with queue depth metrics."""

    queue_name: str = ""
    depth: int = 0
    max_size: int = 0

    @classmethod
    def create(
        cls,
        queue_name: str,
        depth: int,
        max_size: int,
        source: str = "queue",
    ) -> QueueDepthEvent:
        return cls(
            event_type="queue.depth",
            source=source,
            queue_name=queue_name,
            depth=depth,
            max_size=max_size,
            payload={"queue_name": queue_name, "depth": depth, "max_size": max_size},
        )


@dataclass(frozen=True, slots=True)
class ThroughputEvent(EventStreamEvent):
    """Emitted with throughput metrics."""

    metric: str = ""
    value: float = 0.0
    unit: str = ""

    @classmethod
    def create(
        cls,
        metric: str,
        value: float,
        unit: str = "events/s",
        source: str = "metrics",
    ) -> ThroughputEvent:
        return cls(
            event_type="throughput",
            source=source,
            metric=metric,
            value=value,
            unit=unit,
            payload={"metric": metric, "value": value, "unit": unit},
        )


@dataclass(frozen=True, slots=True)
class CacheHitRateEvent(EventStreamEvent):
    """Emitted with cache hit/miss metrics."""

    cache_name: str = ""
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0

    @classmethod
    def create(
        cls,
        cache_name: str,
        hits: int,
        misses: int,
        source: str = "cache",
    ) -> CacheHitRateEvent:
        hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0.0
        return cls(
            event_type="cache.hit_rate",
            source=source,
            cache_name=cache_name,
            hits=hits,
            misses=misses,
            hit_rate=hit_rate,
            payload={
                "cache_name": cache_name,
                "hits": hits,
                "misses": misses,
                "hit_rate": hit_rate,
            },
        )


@dataclass(frozen=True, slots=True)
class RateLimitEvent(EventStreamEvent):
    """Emitted when rate limiting is applied."""

    provider: str = ""
    tokens_remaining: float = 0.0
    wait_seconds: float = 0.0

    @classmethod
    def create(
        cls,
        provider: str,
        tokens_remaining: float,
        wait_seconds: float = 0.0,
        source: str = "rate_limiter",
    ) -> RateLimitEvent:
        return cls(
            event_type="rate_limit.applied",
            source=source,
            provider=provider,
            tokens_remaining=tokens_remaining,
            wait_seconds=wait_seconds,
            priority=EventPriority.HIGH,
            payload={
                "provider": provider,
                "tokens_remaining": tokens_remaining,
                "wait_seconds": wait_seconds,
            },
        )


@dataclass(frozen=True, slots=True)
class CircuitBreakerEvent(EventStreamEvent):
    """Emitted when circuit breaker state changes."""

    name: str = ""
    previous_state: str = ""
    new_state: str = ""
    failure_count: int = 0

    @classmethod
    def create(
        cls,
        name: str,
        previous_state: str,
        new_state: str,
        failure_count: int = 0,
        source: str = "circuit_breaker",
    ) -> CircuitBreakerEvent:
        return cls(
            event_type="circuit_breaker.state_changed",
            source=source,
            name=name,
            previous_state=previous_state,
            new_state=new_state,
            failure_count=failure_count,
            priority=EventPriority.CRITICAL,
            payload={
                "name": name,
                "previous_state": previous_state,
                "new_state": new_state,
                "failure_count": failure_count,
            },
        )


@dataclass(frozen=True, slots=True)
class ConnectionStatusEvent(EventStreamEvent):
    """Emitted when a provider connection status changes."""

    provider: str = ""
    connected: bool = False

    @classmethod
    def create(
        cls,
        provider: str,
        connected: bool,
        source: str = "connector",
    ) -> ConnectionStatusEvent:
        status = "connected" if connected else "disconnected"
        return cls(
            event_type=f"connection.{status}",
            source=source,
            provider=provider,
            connected=connected,
            priority=EventPriority.HIGH if not connected else EventPriority.NORMAL,
            payload={"provider": provider, "connected": connected},
        )


@dataclass(frozen=True, slots=True)
class ProviderUptimeEvent(EventStreamEvent):
    """Emitted with provider uptime metrics."""

    provider: str = ""
    uptime_seconds: float = 0.0
    disconnect_count: int = 0
    reconnect_count: int = 0

    @classmethod
    def create(
        cls,
        provider: str,
        uptime_seconds: float,
        disconnect_count: int = 0,
        reconnect_count: int = 0,
        source: str = "connector",
    ) -> ProviderUptimeEvent:
        return cls(
            event_type="provider.uptime",
            source=source,
            provider=provider,
            uptime_seconds=uptime_seconds,
            disconnect_count=disconnect_count,
            reconnect_count=reconnect_count,
            payload={
                "provider": provider,
                "uptime_seconds": uptime_seconds,
                "disconnect_count": disconnect_count,
                "reconnect_count": reconnect_count,
            },
        )


@dataclass(frozen=True, slots=True)
class ErrorIsolatedEvent(EventStreamEvent):
    """Emitted when a subscriber error is isolated."""

    subscriber_id: str = ""
    error_message: str = ""

    @classmethod
    def create(
        cls,
        subscriber_id: str,
        error_message: str,
        source: str = "stream",
    ) -> ErrorIsolatedEvent:
        return cls(
            event_type="error.isolated",
            source=source,
            subscriber_id=subscriber_id,
            error_message=error_message,
            priority=EventPriority.HIGH,
            payload={
                "subscriber_id": subscriber_id,
                "error_message": error_message,
            },
        )
