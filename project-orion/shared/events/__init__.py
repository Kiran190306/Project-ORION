"""
Project ORION - Domain Events

Standardized event definitions for the event bus system.
All domain events follow a consistent structure with:
- Unique event ID
- Timestamp
- Event type (from EventType enum)
- Source service name
- Payload data
- Metadata (correlation, causation, version)

Events are immutable dataclasses usable across all services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from shared.enums import EventPriority, EventType
from shared.identifiers import generate_id


@dataclass(frozen=True)
class EventMetadata:
    """Standard metadata attached to all events."""

    correlation_id: str = ""
    """ID correlating related events across services."""
    causation_id: str = ""
    """ID of the event that caused this event."""
    version: str = "1.0"
    """Schema version of the event."""
    source_ip: str = ""
    """Originating IP address."""
    user_agent: str = ""
    """Originating user agent."""
    authenticated_user_id: str = ""
    """User who triggered the event."""


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event for the event bus system."""

    event_id: str = field(default_factory=lambda: generate_id("evt"))
    """Unique event identifier."""
    event_type: str = ""
    """Event type string matching EventType enum values."""
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())
    """UTC timestamp of event creation."""
    source: str = ""
    """Name of the service that produced the event."""
    priority: EventPriority = EventPriority.NORMAL
    """Event priority for message ordering."""
    data: dict[str, Any] = field(default_factory=dict)
    """Event-specific payload data."""
    metadata: EventMetadata = field(default_factory=EventMetadata)
    """Standard event metadata."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for JSON encoding."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "priority": self.priority.value,
            "data": self.data,
            "metadata": {
                "correlation_id": self.metadata.correlation_id,
                "causation_id": self.metadata.causation_id,
                "version": self.metadata.version,
            },
        }


# ─── Market Data Events ───────────────────────────────────────


@dataclass(frozen=True)
class TickReceivedEvent(DomainEvent):
    """Published when a market tick is received."""

    event_type: str = EventType.TICK_RECEIVED

    @classmethod
    def create(
        cls,
        symbol: str,
        bid: str,
        ask: str,
        timestamp: str,
        source: str = "market-data",
        **kwargs: Any,
    ) -> TickReceivedEvent:
        return cls(
            source=source,
            data={
                "symbol": symbol,
                "bid": bid,
                "ask": ask,
                "timestamp": timestamp,
            },
            **kwargs,
        )


@dataclass(frozen=True)
class BarCompletedEvent(DomainEvent):
    """Published when an OHLC candle is completed."""

    event_type: str = EventType.BAR_COMPLETED

    @classmethod
    def create(
        cls,
        symbol: str,
        timeframe: str,
        open_price: str,
        high: str,
        low: str,
        close: str,
        volume: str,
        timestamp: str,
        source: str = "market-data",
        **kwargs: Any,
    ) -> BarCompletedEvent:
        return cls(
            source=source,
            data={
                "symbol": symbol,
                "timeframe": timeframe,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "timestamp": timestamp,
            },
            **kwargs,
        )


# ─── Signal Events ────────────────────────────────────────────


@dataclass(frozen=True)
class SignalGeneratedEvent(DomainEvent):
    """Published when a trading signal is generated."""

    event_type: str = EventType.SIGNAL_GENERATED

    @classmethod
    def create(
        cls,
        signal_id: str,
        strategy_id: str,
        symbol: str,
        signal_type: str,
        direction: str,
        price: str,
        confidence: float,
        source: str = "strategy",
        **kwargs: Any,
    ) -> SignalGeneratedEvent:
        return cls(
            source=source,
            data={
                "signal_id": signal_id,
                "strategy_id": strategy_id,
                "symbol": symbol,
                "signal_type": signal_type,
                "direction": direction,
                "price": price,
                "confidence": confidence,
            },
            **kwargs,
        )


# ─── Order Events ─────────────────────────────────────────────


@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """Published when an order is created."""

    event_type: str = EventType.ORDER_CREATED


@dataclass(frozen=True)
class OrderFilledEvent(DomainEvent):
    """Published when an order is fully or partially filled."""

    event_type: str = EventType.ORDER_FILLED


# ─── Position Events ──────────────────────────────────────────


@dataclass(frozen=True)
class PositionOpenedEvent(DomainEvent):
    """Published when a position is opened."""

    event_type: str = EventType.POSITION_OPENED


@dataclass(frozen=True)
class PositionClosedEvent(DomainEvent):
    """Published when a position is closed."""

    event_type: str = EventType.POSITION_CLOSED


# ─── Risk Events ──────────────────────────────────────────────


@dataclass(frozen=True)
class LimitBreachedEvent(DomainEvent):
    """Published when a risk limit is breached."""

    event_type: str = EventType.LIMIT_BREACHED


@dataclass(frozen=True)
class MarginCallEvent(DomainEvent):
    """Published when a margin call is triggered."""

    event_type: str = EventType.MARGIN_CALL


# ─── Event Factory ────────────────────────────────────────────

_EVENT_REGISTRY: dict[str, type[DomainEvent]] = {
    EventType.TICK_RECEIVED: TickReceivedEvent,
    EventType.BAR_COMPLETED: BarCompletedEvent,
    EventType.SIGNAL_GENERATED: SignalGeneratedEvent,
    EventType.ORDER_CREATED: OrderCreatedEvent,
    EventType.ORDER_FILLED: OrderFilledEvent,
    EventType.POSITION_OPENED: PositionOpenedEvent,
    EventType.POSITION_CLOSED: PositionClosedEvent,
    EventType.LIMIT_BREACHED: LimitBreachedEvent,
    EventType.MARGIN_CALL: MarginCallEvent,
}


def create_event(
    event_type: str,
    source: str = "unknown",
    data: Optional[dict[str, Any]] = None,
    **kwargs: Any,
) -> DomainEvent:
    """
    Create a domain event by type string.

    Args:
        event_type: Event type string from EventType enum.
        source: Name of the producing service.
        data: Event payload data.
        **kwargs: Additional DomainEvent parameters.

    Returns:
        DomainEvent instance of the appropriate type.
    """
    event_class = _EVENT_REGISTRY.get(event_type, DomainEvent)
    return event_class(
        event_type=event_type,
        source=source,
        data=data or {},
        **kwargs,
    )


def event_from_dict(data: dict[str, Any]) -> DomainEvent:
    """
    Deserialize a domain event from a dictionary.

    Args:
        data: Dictionary containing serialized event data.

    Returns:
        DomainEvent instance.
    """
    event_type = data.get("event_type", "")
    event_class = _EVENT_REGISTRY.get(event_type, DomainEvent)
    return event_class(
        event_id=data.get("event_id", generate_id("evt")),
        event_type=event_type,
        timestamp=(
            datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.utcnow()
        ),
        source=data.get("source", "unknown"),
        priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
        data=data.get("data", {}),
        metadata=EventMetadata(
            correlation_id=data.get("metadata", {}).get("correlation_id", ""),
            causation_id=data.get("metadata", {}).get("causation_id", ""),
            version=data.get("metadata", {}).get("version", "1.0"),
        ),
    )
