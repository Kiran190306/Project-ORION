"""Registry for Candlestick Pattern definitions and detector functions."""

from __future__ import annotations

from typing import Callable

from .models import (
    CandlestickPattern,
    PatternDefinition,
    PatternDirection,
    PatternStrength,
)
from .rules import (
    CanonicalCandle,
    detect_bearish_engulfing,
    detect_bearish_harami,
    detect_bullish_engulfing,
    detect_bullish_harami,
    detect_doji,
    detect_evening_star,
    detect_hammer,
    detect_hanging_man,
    detect_inside_bar,
    detect_inverted_hammer,
    detect_morning_star,
    detect_shooting_star,
    detect_three_black_crows,
    detect_three_white_soldiers,
)

DetectorCallable = Callable[[tuple[CanonicalCandle, ...]], CandlestickPattern | None]


class PatternRegistry:
    """Registry maintaining candlestick pattern definitions and pure detector callables."""

    def __init__(self) -> None:
        self._definitions: dict[str, PatternDefinition] = {}
        self._detectors: dict[str, DetectorCallable] = {}

    def register(self, definition: PatternDefinition, detector: DetectorCallable) -> None:
        """Register a pattern definition and its detection callable."""
        self._definitions[definition.pattern_id] = definition
        self._detectors[definition.pattern_id] = detector

    def get_definition(self, pattern_id: str) -> PatternDefinition | None:
        """Retrieve definition metadata for a pattern ID."""
        return self._definitions.get(pattern_id)

    def get_detector(self, pattern_id: str) -> DetectorCallable | None:
        """Retrieve detection callable for a pattern ID."""
        return self._detectors.get(pattern_id)

    def list_definitions(self) -> list[PatternDefinition]:
        """List all registered pattern definitions."""
        return list(self._definitions.values())

    def list_pattern_ids(self) -> list[str]:
        """List all registered pattern IDs."""
        return list(self._definitions.keys())

    def filter_by_direction(self, direction: PatternDirection) -> list[PatternDefinition]:
        """Filter pattern definitions by directional bias."""
        return [d for d in self._definitions.values() if d.direction == direction]

    def __len__(self) -> int:
        return len(self._definitions)


def get_default_pattern_registry() -> PatternRegistry:
    """Build and return standard default registry pre-loaded with the 14 core Forex patterns."""
    registry = PatternRegistry()

    registry.register(
        PatternDefinition(
            pattern_id="doji",
            name="Doji",
            direction=PatternDirection.NEUTRAL,
            strength=PatternStrength.MODERATE,
            required_candles=1,
            description="Indecision candle with tiny body and bilateral shadows",
            tags=("reversal", "indecision", "single_bar"),
        ),
        detect_doji,
    )

    registry.register(
        PatternDefinition(
            pattern_id="hammer",
            name="Hammer",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.STRONG,
            required_candles=2,
            description="Bullish reversal candle with long lower shadow rejecting lows",
            tags=("reversal", "bullish", "pin_bar"),
        ),
        detect_hammer,
    )

    registry.register(
        PatternDefinition(
            pattern_id="inverted_hammer",
            name="Inverted Hammer",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.MODERATE,
            required_candles=2,
            description="Bullish bottom reversal characterized by upper shadow buying probe",
            tags=("reversal", "bullish"),
        ),
        detect_inverted_hammer,
    )

    registry.register(
        PatternDefinition(
            pattern_id="shooting_star",
            name="Shooting Star",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.STRONG,
            required_candles=2,
            description="Bearish top reversal with extended upper shadow rejecting highs",
            tags=("reversal", "bearish", "pin_bar"),
        ),
        detect_shooting_star,
    )

    registry.register(
        PatternDefinition(
            pattern_id="hanging_man",
            name="Hanging Man",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.MODERATE,
            required_candles=2,
            description="Bearish top warning signal with long lower shadow after an advance",
            tags=("reversal", "bearish"),
        ),
        detect_hanging_man,
    )

    registry.register(
        PatternDefinition(
            pattern_id="bullish_engulfing",
            name="Bullish Engulfing",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.STRONG,
            required_candles=2,
            description="Bullish reversal: buyers decisively overwhelmed prior bearish session",
            tags=("reversal", "bullish", "engulfing", "multi_bar"),
        ),
        detect_bullish_engulfing,
    )

    registry.register(
        PatternDefinition(
            pattern_id="bearish_engulfing",
            name="Bearish Engulfing",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.STRONG,
            required_candles=2,
            description="Bearish reversal: sellers decisively overwhelmed prior bullish session",
            tags=("reversal", "bearish", "engulfing", "multi_bar"),
        ),
        detect_bearish_engulfing,
    )

    registry.register(
        PatternDefinition(
            pattern_id="bullish_harami",
            name="Bullish Harami",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.MODERATE,
            required_candles=2,
            description="Bullish reversal: contraction candle contained inside prior bearish body",
            tags=("reversal", "bullish", "harami", "multi_bar"),
        ),
        detect_bullish_harami,
    )

    registry.register(
        PatternDefinition(
            pattern_id="bearish_harami",
            name="Bearish Harami",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.MODERATE,
            required_candles=2,
            description="Bearish reversal: contraction candle contained inside prior bullish body",
            tags=("reversal", "bearish", "harami", "multi_bar"),
        ),
        detect_bearish_harami,
    )

    registry.register(
        PatternDefinition(
            pattern_id="inside_bar",
            name="Inside Bar",
            direction=PatternDirection.NEUTRAL,
            strength=PatternStrength.MODERATE,
            required_candles=2,
            description="Volatility contraction: price range strictly contained within previous bar",
            tags=("consolidation", "neutral", "breakout_setup"),
        ),
        detect_inside_bar,
    )

    registry.register(
        PatternDefinition(
            pattern_id="morning_star",
            name="Morning Star",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.STRONG,
            required_candles=3,
            description="3-bar bullish bottom reversal with central star and deep bullish recovery",
            tags=("reversal", "bullish", "star", "three_bar"),
        ),
        detect_morning_star,
    )

    registry.register(
        PatternDefinition(
            pattern_id="evening_star",
            name="Evening Star",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.STRONG,
            required_candles=3,
            description="3-bar bearish top reversal with central star and deep bearish close",
            tags=("reversal", "bearish", "star", "three_bar"),
        ),
        detect_evening_star,
    )

    registry.register(
        PatternDefinition(
            pattern_id="three_white_soldiers",
            name="Three White Soldiers",
            direction=PatternDirection.BULLISH,
            strength=PatternStrength.STRONG,
            required_candles=3,
            description="Three consecutive advancing bullish candles demonstrating sustained buying force",
            tags=("continuation", "bullish", "three_bar"),
        ),
        detect_three_white_soldiers,
    )

    registry.register(
        PatternDefinition(
            pattern_id="three_black_crows",
            name="Three Black Crows",
            direction=PatternDirection.BEARISH,
            strength=PatternStrength.STRONG,
            required_candles=3,
            description="Three consecutive declining bearish candles demonstrating sustained selling force",
            tags=("continuation", "bearish", "three_bar"),
        ),
        detect_three_black_crows,
    )

    return registry
