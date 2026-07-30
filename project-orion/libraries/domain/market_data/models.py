"""Immutable data models for Market Data Abstraction.

Defines broker-agnostic representations of all financial market data
primitives: ticks, bars (OHLCV), order book snapshots, corporate actions,
economic events, and market sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class TickPriceType(StrEnum):
    """Classification of tick price type."""

    TRADE = "trade"
    BID = "bid"
    ASK = "ask"
    MID = "mid"


class BarType(StrEnum):
    """Supported bar / timeframe types."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN1 = "1mo"


class MarketSessionType(StrEnum):
    """Standard market session types."""

    ASIAN = "asian"
    EUROPEAN = "european"
    NORTH_AMERICAN = "north_american"
    LONDON = "london"
    TOKYO = "tokyo"
    SYDNEY = "sydney"
    NEW_YORK = "new_york"
    OVERNIGHT = "overnight"
    CLOSED = "closed"


class CorporateActionType(StrEnum):
    """Types of corporate actions affecting instrument valuation."""

    DIVIDEND = "dividend"
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    MERGER = "merger"
    RIGHTS_ISSUE = "rights_issue"
    SPIN_OFF = "spin_off"
    NAME_CHANGE = "name_change"
    SYMBOL_CHANGE = "symbol_change"


class EconomicEventImportance(StrEnum):
    """Importance level of scheduled economic events."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NON_FARM = "non_farm"


@dataclass(frozen=True, slots=True)
class Tick:
    """A single price tick from any source (trade, bid, ask, mid)."""

    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    price_type: TickPriceType = TickPriceType.TRADE
    bid: Decimal | None = None
    ask: Decimal | None = None
    exchange_timestamp: datetime | None = None
    provider: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TickData:
    """Container for a batch of ticks, typically one per symbol per bar."""

    symbol: str
    ticks: tuple[Tick, ...] = field(default_factory=tuple)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class TradeTick:
    """An executed trade tick with bid/ask context."""

    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    side: str = ""  # buy / sell / neutral
    bid: Decimal | None = None
    ask: Decimal | None = None
    aggressor: str = ""  # buyer / seller / unknown
    exchange_timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Quote:
    """A single quote with bid, ask, and mid prices."""

    symbol: str
    bid: Decimal
    ask: Decimal
    timestamp: datetime
    bid_volume: Decimal | None = None
    ask_volume: Decimal | None = None
    provider: str = ""
    exchange_timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Trade:
    """A generic executed trade (broker-agnostic)."""

    trade_id: str
    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    side: str = ""  # buy / sell
    aggressor: str = ""  # buyer / seller / unknown
    exchange_timestamp: datetime | None = None
    commission: Decimal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OHLCV:
    """Open, High, Low, Close, Volume data point."""

    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    tick_volume: Decimal | None = None
    spread: Decimal | None = None
    bar_type: BarType = BarType.M1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Bar:
    """Aggregated bar data with OHLCV and additional statistics."""

    symbol: str
    bar_type: BarType
    timestamp: datetime
    ohlcv: OHLCV
    vwap: Decimal | None = None
    count: int = 0  # number of ticks in this bar
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BookLevel:
    """A single level in the order book."""

    price: Decimal
    volume: Decimal
    order_count: int = 0


@dataclass(frozen=True, slots=True)
class OrderBook:
    """A snapshot of the order book."""

    symbol: str
    timestamp: datetime
    bids: tuple[BookLevel, ...] = field(default_factory=tuple)
    asks: tuple[BookLevel, ...] = field(default_factory=tuple)
    depth: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    """Full order book snapshot with sequence tracking."""

    symbol: str
    timestamp: datetime
    bids: tuple[BookLevel, ...] = field(default_factory=tuple)
    asks: tuple[BookLevel, ...] = field(default_factory=tuple)
    sequence: int = 0
    snapshot_type: str = "snapshot"  # snapshot | incremental
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketSession:
    """Definition of a market trading session."""

    session_type: MarketSessionType
    symbol: str
    open_time: datetime
    close_time: datetime
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CorporateAction:
    """A corporate action event affecting instrument valuation."""

    symbol: str
    action_type: CorporateActionType
    announcement_date: datetime
    effective_date: datetime
    description: str = ""
    ratio: Decimal | None = None
    dividend_amount: Decimal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    """A scheduled economic event / news release."""

    event_id: str
    title: str
    timestamp: datetime
    importance: EconomicEventImportance = EconomicEventImportance.MEDIUM
    currency: str = ""
    actual: str = ""
    forecast: str = ""
    previous: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
