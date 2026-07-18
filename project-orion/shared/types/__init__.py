"""
Project ORION - Shared Types & Type Definitions

Core type aliases, type guards, and generic type definitions
used across the platform for type safety.

Provides:
- Type aliases for common data structures
- TypedDict definitions for data transfer objects
- TypeVars for generic programming
- Union types for domain concepts
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import (Any, Callable, Dict, Generic, List, Optional, Protocol,
                    Tuple, TypedDict, TypeVar, Union)

# Re-export for unit tests / public contract compatibility
__all__ = [
    "Any",
    "Callable",
    "Dict",
    "Generic",
    "List",
    "Optional",
    "Protocol",
    "Tuple",
    "TypedDict",
    "TypeVar",
    "Union",
]


# ─── Generic Type Variables ───────────────────────────────────

T = TypeVar("T")
"""Generic type variable."""
K = TypeVar("K")
"""Generic key type variable."""
V = TypeVar("V")
"""Generic value type variable."""
E = TypeVar("E", bound=Exception)
"""Exception type variable."""
JSON = Union[str, int, float, bool, None, Dict[str, "JSON"], List["JSON"]]
"""JSON-compatible type."""

# ─── Primitive Type Aliases ───────────────────────────────────

Price = Decimal
"""Price value type."""
Volume = Decimal
"""Volume/quantity value type."""
PipValue = Decimal
"""Pip value type."""
Percentage = float
"""Percentage value (e.g., 0.05 = 5%)."""
Ratio = float
"""Ratio value (e.g., 1.5 = 1.5:1)."""

Timestamp = datetime
"""UTC timestamp type."""
Duration = int
"""Duration in seconds."""
Milliseconds = int
"""Duration in milliseconds."""

Symbol = str
"""Instrument symbol (e.g., 'EUR/USD')."""
InstrumentId = str
"""Unique instrument identifier."""
AccountId = str
"""Unique account identifier."""
UserId = str
"""Unique user identifier."""
StrategyId = str
"""Unique strategy identifier."""
OrderId = str
"""Unique order identifier."""
PositionId = str
"""Unique position identifier."""
TradeId = str
"""Unique trade identifier."""
SignalId = str
"""Unique signal identifier."""
BacktestId = str
"""Unique backtest identifier."""

# ─── TypedDict Definitions ────────────────────────────────────


class Money(TypedDict):
    """Monetary value with currency."""

    amount: Decimal
    currency: str


class Range(TypedDict, Generic[T]):
    """Generic range with min and max values."""

    min: T
    max: T


class TimeRange(TypedDict):
    """Time range with start and end timestamps."""

    start: Timestamp
    end: Timestamp


class PriceRange(TypedDict):
    """Price range with lower and upper bounds."""

    lower: Price
    upper: Price


class OHLC(TypedDict):
    """OHLC candlestick data."""

    timestamp: Timestamp
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume


class Tick(TypedDict):
    """Market tick data."""

    symbol: Symbol
    timestamp: Timestamp
    bid: Price
    ask: Price
    bid_volume: Volume
    ask_volume: Volume
    source: str


class PositionSize(TypedDict):
    """Position size calculation result."""

    units: Volume
    value: Money
    risk_amount: Money
    risk_percentage: Percentage


# ─── Protocol Definitions ─────────────────────────────────────


class Serializable(Protocol):
    """Protocol for serializable objects."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Serializable:
        """Deserialize from dictionary."""
        ...


class Comparable(Protocol):
    """Protocol for comparable objects."""

    def __lt__(self, other: object) -> bool:
        ...

    def __eq__(self, other: object) -> bool:
        ...


class HasId(Protocol):
    """Protocol for objects with an identifier."""

    id: str


class HasTimestamps(Protocol):
    """Protocol for objects with creation/update timestamps."""

    created_at: Timestamp
    updated_at: Timestamp


# ─── Data Class Definitions ───────────────────────────────────


@dataclass(frozen=True)
class Point:
    """2D point with x/y coordinates."""

    x: float
    y: float


@dataclass(frozen=True)
class LatencyMetrics:
    """Latency measurement data."""

    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    samples: int


@dataclass(frozen=True)
class PaginationParams:
    """Pagination request parameters."""

    page: int = 1
    page_size: int = 100

    def __post_init__(self) -> None:
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.page_size < 1:
            object.__setattr__(self, "page_size", 100)
        if self.page_size > 1000:
            object.__setattr__(self, "page_size", 1000)


@dataclass(frozen=True)
class PaginatedResult(Generic[T]):
    """Paginated result wrapper."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


# ─── JSON Serialization Helpers ──────────────────────────────


def decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    """Convert Decimal to float for JSON serialization."""
    if value is None:
        return None
    return float(value)


def datetime_to_iso(value: Optional[Timestamp]) -> Optional[str]:
    """Convert datetime to ISO format string."""
    if value is None:
        return None
    return value.isoformat()
