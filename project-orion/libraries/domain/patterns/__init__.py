"""Candlestick Pattern Recognition Engine.

Institutional price action pattern analysis for Project ORION.
"""

from __future__ import annotations

from .engine import (
    CandlestickPatternEngine,
    detect_patterns,
    detect_patterns_at,
    get_default_engine,
)
from .models import (
    CandlestickPattern,
    PatternDefinition,
    PatternDirection,
    PatternStrength,
)
from .registry import PatternRegistry, get_default_pattern_registry
from .rules import CanonicalCandle, normalize_candle

__all__ = [
    "CandlestickPattern",
    "CandlestickPatternEngine",
    "CanonicalCandle",
    "PatternDefinition",
    "PatternDirection",
    "PatternRegistry",
    "PatternStrength",
    "detect_patterns",
    "detect_patterns_at",
    "get_default_engine",
    "get_default_pattern_registry",
    "normalize_candle",
]
