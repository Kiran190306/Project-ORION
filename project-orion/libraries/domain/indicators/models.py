"""Immutable data models for the Indicator Engine.

All output models are frozen dataclasses ensuring immutability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class IndicatorType(StrEnum):
    """Classification of indicator types."""

    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    BREAKOUT = "breakout"
    MARKET_STRENGTH = "market_strength"


@dataclass(frozen=True, slots=True)
class Bar:
    """OHLCV bar data for indicator calculations."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    symbol: str = ""

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError("high cannot be less than low")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")


@dataclass(frozen=True, slots=True)
class IndicatorValue:
    """A single computed indicator value with timestamp."""

    timestamp: datetime
    value: float
    quality: float = 1.0  # 0.0 to 1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.quality <= 1.0:
            raise ValueError("quality must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class IndicatorResult:
    """Result from an indicator calculation.

    Contains the primary value and optional metadata like upper/lower bands,
    signal lines, histograms, etc.
    """

    indicator_name: str
    timestamp: datetime
    value: float | None = None
    values: dict[str, float | None] = field(default_factory=dict)
    quality: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_value(self, key: str = "main") -> float | None:
        if key == "main":
            return self.value
        return self.values.get(key)

    def is_valid(self) -> bool:
        return self.value is not None or bool(self.values)


@dataclass(frozen=True, slots=True)
class IndicatorMetadata:
    """Metadata describing an indicator implementation."""

    name: str
    indicator_type: IndicatorType
    display_name: str
    version: str = "1.0.0"
    description: str = ""
    min_period: int = 1
    default_period: int = 14
    params: tuple[str, ...] = field(default_factory=tuple)
