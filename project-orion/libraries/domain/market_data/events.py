"""Domain events for the Market Data Abstraction Layer.

Defines immutable event types emitted by market data providers and
consumed by downstream components. Every event carries a timestamp,
symbol, and type discriminator for routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.domain.market_data.models import (
    Bar,
    CorporateAction,
    EconomicEvent,
    MarketSession,
    OHLCV,
    OrderBookSnapshot,
    Tick,
)


class MarketDataEventType(StrEnum):
    """Discriminated event types for market data domain events."""

    TICK_RECEIVED = "tick_received"
    BAR_COMPLETED = "bar_completed"
    BAR_UPDATED = "bar_updated"
    ORDER_BOOK_SNAPSHOT = "order_book_snapshot"
    ORDER_BOOK_UPDATE = "order_book_update"
    MARKET_SESSION_OPEN = "market_session_open"
    MARKET_SESSION_CLOSE = "market_session_close"
    CORPORATE_ACTION = "corporate_action"
    ECONOMIC_EVENT = "economic_event"
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_ERROR = "provider_error"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"


@dataclass(frozen=True, slots=True)
class MarketDataEvent:
    """Base domain event for market data.

    All market data events inherit from this base. The ``event_type``
    discriminator enables routing without ``isinstance`` checks.
    """

    event_type: MarketDataEventType
    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TickEvent(MarketDataEvent):
    """Emitted when a new tick is received from a provider."""

    tick: Tick

    def __init__(self, tick: Tick, **kwargs: Any) -> None:
        object.__setattr__(self, "event_type", MarketDataEventType.TICK_RECEIVED)
        object.__setattr__(self, "symbol", tick.symbol)
        object.__setattr__(self, "timestamp", tick.timestamp)
        object.__setattr__(self, "tick", tick)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class BarEvent(MarketDataEvent):
    """Emitted when a bar is completed or updated."""

    bar: Bar
    is_complete: bool = True

    def __init__(self, bar: Bar, is_complete: bool = True, **kwargs: Any) -> None:
        event_type = (
            MarketDataEventType.BAR_COMPLETED
            if is_complete
            else MarketDataEventType.BAR_UPDATED
        )
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "symbol", bar.symbol)
        object.__setattr__(self, "timestamp", bar.timestamp)
        object.__setattr__(self, "bar", bar)
        object.__setattr__(self, "is_complete", is_complete)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class OHLCVEvent(MarketDataEvent):
    """Emitted when a new OHLCV data point is received."""

    ohlcv: OHLCV

    def __init__(self, ohlcv: OHLCV, **kwargs: Any) -> None:
        object.__setattr__(self, "event_type", MarketDataEventType.BAR_UPDATED)
        object.__setattr__(self, "symbol", ohlcv.symbol)
        object.__setattr__(self, "timestamp", ohlcv.timestamp)
        object.__setattr__(self, "ohlcv", ohlcv)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class OrderBookEvent(MarketDataEvent):
    """Emitted when an order book snapshot or update is received."""

    snapshot: OrderBookSnapshot

    def __init__(self, snapshot: OrderBookSnapshot, **kwargs: Any) -> None:
        event_type = (
            MarketDataEventType.ORDER_BOOK_SNAPSHOT
            if snapshot.snapshot_type == "snapshot"
            else MarketDataEventType.ORDER_BOOK_UPDATE
        )
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "symbol", snapshot.symbol)
        object.__setattr__(self, "timestamp", snapshot.timestamp)
        object.__setattr__(self, "snapshot", snapshot)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class SessionEvent(MarketDataEvent):
    """Emitted when a market session opens or closes."""

    session: MarketSession
    is_open: bool = True

    def __init__(self, session: MarketSession, is_open: bool = True, **kwargs: Any) -> None:
        event_type = (
            MarketDataEventType.MARKET_SESSION_OPEN
            if is_open
            else MarketDataEventType.MARKET_SESSION_CLOSE
        )
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "symbol", session.symbol)
        object.__setattr__(self, "timestamp", session.open_time if is_open else session.close_time)
        object.__setattr__(self, "session", session)
        object.__setattr__(self, "is_open", is_open)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class CorporateActionEvent(MarketDataEvent):
    """Emitted when a corporate action is announced or goes effective."""

    action: CorporateAction

    def __init__(self, action: CorporateAction, **kwargs: Any) -> None:
        object.__setattr__(self, "event_type", MarketDataEventType.CORPORATE_ACTION)
        object.__setattr__(self, "symbol", action.symbol)
        object.__setattr__(self, "timestamp", action.announcement_date)
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class EconomicEventEvent(MarketDataEvent):
    """Emitted when an economic event is released."""

    event: EconomicEvent

    def __init__(self, event: EconomicEvent, **kwargs: Any) -> None:
        object.__setattr__(self, "event_type", MarketDataEventType.ECONOMIC_EVENT)
        object.__setattr__(self, "symbol", event.currency)
        object.__setattr__(self, "timestamp", event.timestamp)
        object.__setattr__(self, "event", event)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))


@dataclass(frozen=True, slots=True)
class ProviderEvent(MarketDataEvent):
    """Emitted when a data provider connects, disconnects, or errors."""

    provider_name: str = ""
    error_message: str = ""

    def __init__(
        self,
        event_type: MarketDataEventType,
        symbol: str,
        provider_name: str = "",
        error_message: str = "",
        **kwargs: Any,
    ) -> None:
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timestamp", datetime.now(timezone.utc))
        object.__setattr__(self, "provider_name", provider_name)
        object.__setattr__(self, "error_message", error_message)
        object.__setattr__(self, "metadata", kwargs.get("metadata", {}))

