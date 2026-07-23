"""Event scheduler for backtesting.

Schedules market events during backtest replay, enabling scenario
testing with events like high volatility, low liquidity, spread spikes,
flash crashes, news events, broker disconnects, and gap opens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ScheduledEvent(ABC):
    """Base class for scheduled events during backtesting."""

    timestamp: datetime
    symbol: str = ""
    severity: str = "medium"  # low, medium, high, critical
    metadata: dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        """Apply the event to the backtest context.

        Args:
            context: Current backtest context.

        Returns:
            Updated context with event effects applied.
        """
        ...


@dataclass(frozen=True, slots=True)
class HighVolatilityEvent(ScheduledEvent):
    """Event simulating a period of high market volatility."""

    volatility_multiplier: float = 2.0
    duration_minutes: int = 60

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["volatility"] = ctx.get("volatility", 1.0) * self.volatility_multiplier
        ctx["event_active"] = True
        ctx["event_type"] = "high_volatility"
        return ctx


@dataclass(frozen=True, slots=True)
class LowLiquidityEvent(ScheduledEvent):
    """Event simulating a period of reduced market liquidity."""

    liquidity_multiplier: float = 0.3
    duration_minutes: int = 30

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["liquidity_score"] = ctx.get("liquidity_score", 1.0) * self.liquidity_multiplier
        ctx["event_active"] = True
        ctx["event_type"] = "low_liquidity"
        return ctx


@dataclass(frozen=True, slots=True)
class SpreadSpikeEvent(ScheduledEvent):
    """Event simulating a sudden spread widening."""

    spread_multiplier: float = 5.0
    duration_minutes: int = 15

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["spread_pips"] = ctx.get("spread_pips", 1.0) * self.spread_multiplier
        ctx["event_active"] = True
        ctx["event_type"] = "spread_spike"
        return ctx


@dataclass(frozen=True, slots=True)
class FlashCrashEvent(ScheduledEvent):
    """Event simulating a flash crash."""

    price_drop_pct: float = 5.0
    recovery_minutes: int = 10

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["flash_crash"] = True
        ctx["price_drop_pct"] = self.price_drop_pct
        ctx["event_active"] = True
        ctx["event_type"] = "flash_crash"
        return ctx


@dataclass(frozen=True, slots=True)
class NewsEvent(ScheduledEvent):
    """Event simulating a high-impact news release."""

    impact_duration_minutes: int = 30
    spread_widen_multiplier: float = 3.0

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["is_news_hour"] = True
        ctx["spread_pips"] = ctx.get("spread_pips", 1.0) * self.spread_widen_multiplier
        ctx["event_active"] = True
        ctx["event_type"] = "news"
        return ctx


@dataclass(frozen=True, slots=True)
class BrokerDisconnectEvent(ScheduledEvent):
    """Event simulating a broker disconnection."""

    disconnect_duration_seconds: int = 60

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["broker_connected"] = False
        ctx["event_active"] = True
        ctx["event_type"] = "broker_disconnect"
        return ctx


@dataclass(frozen=True, slots=True)
class GapOpenEvent(ScheduledEvent):
    """Event simulating a gap open (e.g., after weekend)."""

    gap_pips: float = 20.0
    direction: str = "up"  # up or down

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(context)
        ctx["gap_open"] = True
        ctx["gap_pips"] = self.gap_pips
        ctx["gap_direction"] = self.direction
        ctx["event_active"] = True
        ctx["event_type"] = "gap_open"
        return ctx


class EventScheduler:
    """Manages scheduled events during backtest replay.

    Events are sorted by timestamp and triggered at the appropriate
    time during replay.
    """

    def __init__(self) -> None:
        """Initialize event scheduler."""
        self._events: list[ScheduledEvent] = []
        self._sorted: bool = False

    def add_event(self, event: ScheduledEvent) -> None:
        """Add an event to the schedule.

        Args:
            event: Event to schedule.
        """
        self._events.append(event)
        self._sorted = False

    def add_events(self, events: list[ScheduledEvent]) -> None:
        """Add multiple events.

        Args:
            events: List of events to schedule.
        """
        self._events.extend(events)
        self._sorted = False

    def get_events_at(
        self,
        timestamp: datetime,
        tolerance_seconds: float = 1.0,
    ) -> list[ScheduledEvent]:
        """Get events scheduled at or near the given timestamp.

        Args:
            timestamp: Target timestamp.
            tolerance_seconds: Match tolerance in seconds.

        Returns:
            List of matching events.
        """
        if not self._sorted:
            self._events.sort(key=lambda e: e.timestamp)
            self._sorted = True

        matching = []
        for event in self._events:
            diff = abs((event.timestamp - timestamp).total_seconds())
            if diff <= tolerance_seconds:
                matching.append(event)

        return matching

    def get_upcoming_events(
        self,
        from_timestamp: datetime,
        limit: int = 10,
    ) -> list[ScheduledEvent]:
        """Get upcoming events from a timestamp.

        Args:
            from_timestamp: Starting timestamp.
            limit: Maximum number of events.

        Returns:
            List of upcoming events.
        """
        if not self._sorted:
            self._events.sort(key=lambda e: e.timestamp)
            self._sorted = True

        return [e for e in self._events if e.timestamp >= from_timestamp][:limit]

    def clear(self) -> None:
        """Clear all scheduled events."""
        self._events.clear()
        self._sorted = False

    @property
    def event_count(self) -> int:
        """Return the number of scheduled events."""
        return len(self._events)
