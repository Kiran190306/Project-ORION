"""Protocol/port definitions for the Market Data Abstraction Layer.

Defines all broker-agnostic ports for consuming financial market data.
Every external dependency (broker API, data vendor, file parser) is
injected through these protocol ports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from libraries.domain.market_data.models import (
    Bar,
    CorporateAction,
    EconomicEvent,
    MarketSession,
    OHLCV,
    OrderBookSnapshot,
    Tick,
    TickData,
)


@runtime_checkable
class TickDataProviderPort(Protocol):
    """Port for streaming real-time tick data from any source."""

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to tick data for the given symbols."""
        ...

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from tick data for the given symbols."""
        ...

    async def stream(self) -> AsyncIterator[Tick]:
        """Yield ticks as they arrive from the provider."""
        ...

    async def latest_tick(self, symbol: str) -> Tick | None:
        """Return the most recent tick for a symbol, or None."""
        ...

    async def is_connected(self) -> bool:
        """Return whether the provider connection is active."""
        ...


@runtime_checkable
class HistoricalDataProviderPort(Protocol):
    """Port for loading historical market data (OHLCV bars)."""

    async def load_bars(
        self,
        symbol: str,
        bar_type: str,
        start: datetime,
        end: datetime,
        **kwargs: Any,
    ) -> AsyncIterator[OHLCV]:
        """Yield historical OHLCV bars within the date range."""
        ...

    async def load_ticks(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        **kwargs: Any,
    ) -> AsyncIterator[Tick]:
        """Yield historical ticks within the date range."""
        ...

    async def validate_availability(
        self,
        symbol: str,
        bar_type: str,
        start: datetime,
        end: datetime,
    ) -> bool:
        """Check if historical data is available for the given parameters."""
        ...

    async def available_symbols(self) -> list[str]:
        """Return list of symbols with available historical data."""
        ...

    async def available_bar_types(self, symbol: str) -> list[str]:
        """Return list of bar types available for a symbol."""
        ...

    async def date_range(
        self,
        symbol: str,
        bar_type: str,
    ) -> tuple[datetime, datetime] | None:
        """Return (start, end) date range for available data, or None."""
        ...


@runtime_checkable
class OrderBookProviderPort(Protocol):
    """Port for streaming order book snapshots."""

    async def subscribe(self, symbols: list[str], depth: int = 10) -> None:
        """Subscribe to order book data for the given symbols."""
        ...

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from order book data."""
        ...

    async def stream(self) -> AsyncIterator[OrderBookSnapshot]:
        """Yield order book snapshots as they arrive."""
        ...

    async def snapshot(self, symbol: str, depth: int = 10) -> OrderBookSnapshot | None:
        """Return the current order book snapshot, or None."""
        ...


@runtime_checkable
class SessionCalendarPort(Protocol):
    """Port for querying market trading sessions and calendars."""

    async def active_sessions(
        self,
        symbol: str,
        instant: datetime | None = None,
    ) -> list[MarketSession]:
        """Return sessions active at the given instant (default: now)."""
        ...

    async def is_market_open(self, symbol: str, instant: datetime | None = None) -> bool:
        """Return whether the market is open at the given instant."""
        ...

    async def next_session_open(
        self,
        symbol: str,
        after: datetime | None = None,
    ) -> MarketSession | None:
        """Return the next session opening after the given time."""
        ...

    async def next_session_close(
        self,
        symbol: str,
        after: datetime | None = None,
    ) -> MarketSession | None:
        """Return the next session closing after the given time."""
        ...


@runtime_checkable
class CorporateActionProviderPort(Protocol):
    """Port for fetching corporate action events."""

    async def get_actions(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> list[CorporateAction]:
        """Return corporate actions for a symbol within a date range."""
        ...

    async def get_upcoming_actions(
        self,
        symbol: str,
        lookahead_days: int = 30,
    ) -> list[CorporateAction]:
        """Return upcoming corporate actions for a symbol."""
        ...


@runtime_checkable
class EconomicCalendarPort(Protocol):
    """Port for fetching scheduled economic events."""

    async def get_events(
        self,
        start: datetime,
        end: datetime,
        currency: str | None = None,
        importance: str | None = None,
    ) -> list[EconomicEvent]:
        """Return economic events within a date range with optional filters."""
        ...

    async def get_high_impact_events(
        self,
        lookahead_days: int = 7,
        currency: str | None = None,
    ) -> list[EconomicEvent]:
        """Return high-impact economic events within the lookahead window."""
        ...


@runtime_checkable
class MarketDataConsumerPort(Protocol):
    """Consumer of processed market data for downstream use."""

    async def on_tick(self, tick: Tick) -> None:
        """Called when a new tick is received."""
        ...

    async def on_bar(self, bar: Bar) -> None:
        """Called when a new bar is completed."""
        ...

    async def on_order_book(self, snapshot: OrderBookSnapshot) -> None:
        """Called when an order book snapshot is received."""
        ...


@runtime_checkable
class BarBuilderPort(Protocol):
    """Port for building aggregated bars from tick data."""

    async def add_tick(self, tick: Tick) -> Bar | None:
        """Add a tick and return a completed bar if one is ready, else None."""
        ...

    async def current_bar(self) -> Bar | None:
        """Return the in-progress bar without completing it."""
        ...


@runtime_checkable
class MarketSnapshotProviderPort(Protocol):
    """Port for fetching point-in-time market snapshots.

    Provides a request-response interface for current market state
    without requiring a persistent subscription. Useful for one-off
    queries, health checks, and initial state loading.
    """

    async def snapshot(
        self,
        symbol: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return a full market snapshot for the given symbol.

        The snapshot dict typically contains tick, quote, order book,
        and session information merged into a single response.
        """
        ...

    async def latest(self, symbol: str) -> Tick | None:
        """Return the latest data point for a symbol, or None."""
        ...

    async def stream(self) -> AsyncIterator[Tick]:
        """Yield market snapshots as they change."""
        ...

    async def snapshot_tick(self, symbol: str) -> Tick | None:
        """Return the latest tick snapshot, or None if unavailable."""
        ...

    async def snapshot_quote(self, symbol: str) -> Tick | None:
        """Return the latest quote (bid/ask) snapshot, or None."""
        ...

    async def snapshot_order_book(
        self,
        symbol: str,
        depth: int = 10,
    ) -> OrderBookSnapshot | None:
        """Return the current order book snapshot, or None."""
        ...
