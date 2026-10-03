"""Domain data models and enumerations for Candlestick Pattern Recognition."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class PatternDirection(StrEnum):
    """Directional bias indicated by a candlestick pattern."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class PatternStrength(StrEnum):
    """Deterministic strength classification of a pattern."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass(frozen=True, slots=True)
class CandlestickPattern:
    """Immutable representation of a recognized candlestick pattern event."""

    pattern_id: str
    name: str
    direction: PatternDirection
    strength: PatternStrength
    candle_index: int
    timestamp: datetime
    description: str
    confidence: Decimal = Decimal("1.00")
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert pattern event to a JSON-serializable dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "candle_index": self.candle_index,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "confidence": str(self.confidence),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PatternDefinition:
    """Metadata specification for a registered candlestick pattern."""

    pattern_id: str
    name: str
    direction: PatternDirection
    strength: PatternStrength
    required_candles: int
    description: str
    tags: tuple[str, ...] = field(default_factory=tuple)
