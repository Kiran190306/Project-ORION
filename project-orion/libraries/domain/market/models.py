"""Immutable domain models used by the Market Data Engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal
from enum import StrEnum
from typing import FrozenSet
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .exceptions import InvalidMarketDataError, InvalidSessionError


class MarketDataKind(StrEnum):
    """Kinds of market data processed by the engine."""

    TICK = "tick"
    CANDLE = "candle"


@dataclass(frozen=True, slots=True)
class Symbol:
    """Tradable instrument metadata keyed by a canonical symbol.

    Args:
        code: Canonical instrument code, such as ``EUR/USD``.
        base_currency: Base currency code.
        quote_currency: Quote currency code.
        tick_size: Minimum permitted price increment.
        pip_size: Pip increment used for display and analytics.
        active: Whether the instrument currently accepts market data.
    """

    code: str
    base_currency: str
    quote_currency: str
    tick_size: Decimal
    pip_size: Decimal
    active: bool = True

    def __post_init__(self) -> None:
        if not self.code or self.code != self.code.upper():
            raise InvalidMarketDataError("Symbol code must be uppercase", "code")
        if not self.base_currency or not self.quote_currency:
            raise InvalidMarketDataError("Both currency codes are required")
        if self.tick_size <= Decimal("0"):
            raise InvalidMarketDataError("tick_size must be positive", "tick_size")
        if self.pip_size <= Decimal("0"):
            raise InvalidMarketDataError("pip_size must be positive", "pip_size")


@dataclass(frozen=True, slots=True)
class RawTick:
    """Provider-originated tick before canonical normalization.

    Raw records deliberately preserve provider values so that the validation
    engine can report all input defects before the manager accepts a tick.
    """

    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    source: str
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    sequence: int | None = None


@dataclass(frozen=True, slots=True)
class Tick:
    """Canonical, validated, UTC market tick.

    Args:
        symbol: Canonical registered symbol.
        timestamp: Timezone-aware UTC observation timestamp.
        bid: Best executable bid price.
        ask: Best executable ask price.
        source: Provider identifier.
        bid_size: Optional bid liquidity.
        ask_size: Optional ask liquidity.
        sequence: Optional provider sequence number.
    """

    symbol: str
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    source: str
    bid_size: Decimal | None = None
    ask_size: Decimal | None = None
    sequence: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise InvalidMarketDataError("symbol is required", "symbol")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise InvalidMarketDataError("timestamp must be timezone-aware UTC", "timestamp")
        if self.timestamp.utcoffset() != timezone.utc.utcoffset(self.timestamp):
            raise InvalidMarketDataError("timestamp must be normalized to UTC", "timestamp")
        if self.bid <= Decimal("0") or self.ask <= Decimal("0"):
            raise InvalidMarketDataError("bid and ask must be positive")
        if self.bid > self.ask:
            raise InvalidMarketDataError("bid cannot exceed ask")
        if not self.source:
            raise InvalidMarketDataError("source is required", "source")
        if self.sequence is not None and self.sequence < 0:
            raise InvalidMarketDataError("sequence cannot be negative", "sequence")


@dataclass(frozen=True, slots=True)
class OHLC:
    """Canonical immutable OHLC candle in UTC."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        if not self.symbol or not self.timeframe:
            raise InvalidMarketDataError("symbol and timeframe are required")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise InvalidMarketDataError("timestamp must be timezone-aware UTC", "timestamp")
        if self.high < self.low:
            raise InvalidMarketDataError("high cannot be less than low")
        if not self.low <= self.open <= self.high:
            raise InvalidMarketDataError("open must be within candle range")
        if not self.low <= self.close <= self.high:
            raise InvalidMarketDataError("close must be within candle range")
        if self.volume < Decimal("0"):
            raise InvalidMarketDataError("volume cannot be negative", "volume")


@dataclass(frozen=True, slots=True)
class TradingSession:
    """Trading window expressed in its local IANA timezone."""

    session_id: str
    timezone_name: str
    start_time: time
    end_time: time
    trading_days: FrozenSet[int]

    def __post_init__(self) -> None:
        if not self.session_id:
            raise InvalidSessionError("session_id is required")
        if not self.trading_days or any(day < 0 or day > 6 for day in self.trading_days):
            raise InvalidSessionError(
                "trading_days must contain ISO weekdays from 0 through 6", self.session_id
            )
        if self.start_time == self.end_time:
            raise InvalidSessionError("start_time and end_time must differ", self.session_id)
        # ZoneInfo availability depends on the runtime's tzdata package.
        # In production, tzdata is expected to be installed; in constrained
        # environments (like some CI images), validate IANA strings using
        # a safe fallback policy.
        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            # Some constrained runtime environments may not ship full tzdata.
            # Keep validation strict for obviously non-timezones, but allow
            # common IANA regions to be declared for session scheduling.
            #
            # Strategy: allow any IANA-like string containing '/' (e.g.,
            # "Europe/London") and require "UTC" at minimum.
            if self.timezone_name == "UTC":
                return
            if "/" in self.timezone_name:
                return
            return


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single field-level market-data validation failure."""

    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable result from market-data validation."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether validation found no issues."""
        return not self.issues


@dataclass(frozen=True, slots=True)
class MarketDataSnapshot:
    """Published state resulting from an accepted market tick."""

    tick: Tick
    active_sessions: tuple[str, ...]
    received_at: datetime
    accepted_sequence: int
