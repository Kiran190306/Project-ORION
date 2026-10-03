"""Candlestick Pattern Recognition Engine.

Provides deterministic, pure, side-effect-free detection of price action candlestick patterns.
Strictly causal: patterns detected at index N only consult candles <= N, guaranteeing
zero look-ahead bias and 100% compatibility with backtesting and event replay.
"""

from __future__ import annotations

from typing import Any, Sequence

from .models import CandlestickPattern
from .registry import PatternRegistry, get_default_pattern_registry
from .rules import CanonicalCandle, normalize_candle


class CandlestickPatternEngine:
    """Institutional-grade Candlestick Pattern Recognition Engine."""

    def __init__(self, registry: PatternRegistry | None = None) -> None:
        self._registry = registry or get_default_pattern_registry()

    @property
    def registry(self) -> PatternRegistry:
        """Access underlying pattern registry."""
        return self._registry

    def detect_patterns(
        self,
        candles: Sequence[Any],
        pattern_ids: Sequence[str] | None = None,
    ) -> list[CandlestickPattern]:
        """Detect all matching candlestick patterns across candle sequence in chronological order.

        Args:
            candles: Chronological sequence of OHLCV, Bar, or dict candle objects.
            pattern_ids: Optional subset of pattern IDs to evaluate (defaults to all registered).

        Returns:
            Chronologically sorted list of detected CandlestickPattern instances.
        """
        if not candles:
            return []

        # Convert to immutable canonical candles once
        canonical_candles = tuple(
            normalize_candle(c, index=i) for i, c in enumerate(candles)
        )

        detected: list[CandlestickPattern] = []
        for i in range(len(canonical_candles)):
            matches = self._detect_at_index(canonical_candles, i, pattern_ids=pattern_ids)
            detected.extend(matches)

        return detected

    def detect_patterns_at(
        self,
        candles: Sequence[Any],
        index: int,
        pattern_ids: Sequence[str] | None = None,
    ) -> list[CandlestickPattern]:
        """Detect patterns concluding specifically at candle `index`.

        Strictly enforces causal evaluation: only candles with indices <= `index`
        are provided to detector functions. No future data is ever inspected.

        Args:
            candles: Sequence of candle objects.
            index: Target 0-based index to evaluate.
            pattern_ids: Optional subset of pattern IDs to evaluate.

        Returns:
            List of patterns concluding on the candle at `index`.
        """
        if not candles or index < 0 or index >= len(candles):
            return []

        # Only normalize candles up to `index` to strictly guarantee zero look-ahead
        causal_slice = tuple(
            normalize_candle(c, index=i) for i, c in enumerate(candles[: index + 1])
        )

        return self._detect_at_index(causal_slice, index, pattern_ids=pattern_ids)

    def _detect_at_index(
        self,
        canonical_candles: tuple[CanonicalCandle, ...],
        index: int,
        pattern_ids: Sequence[str] | None = None,
    ) -> list[CandlestickPattern]:
        """Internal helper to evaluate all detectors at a specific index."""
        if index < 0 or index >= len(canonical_candles):
            return []

        target_ids = pattern_ids if pattern_ids is not None else self._registry.list_pattern_ids()
        results: list[CandlestickPattern] = []

        for pid in target_ids:
            definition = self._registry.get_definition(pid)
            detector = self._registry.get_detector(pid)
            if definition is None or detector is None:
                continue

            req = definition.required_candles
            # Insufficient history before index -> skip safely
            if index + 1 < req:
                continue

            # Extract exact window concluding at `index`: strictly candles <= index
            window = canonical_candles[index - req + 1 : index + 1]
            match = detector(window)
            if match is not None:
                results.append(match)

        return results


# ─── Top-level Convenience APIs ──────────────────────────────────────────────


_DEFAULT_ENGINE: CandlestickPatternEngine | None = None


def get_default_engine() -> CandlestickPatternEngine:
    """Return singleton default CandlestickPatternEngine."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = CandlestickPatternEngine()
    return _DEFAULT_ENGINE


def detect_patterns(
    candles: Sequence[Any],
    pattern_ids: Sequence[str] | None = None,
) -> list[CandlestickPattern]:
    """Convenience function: detect all candlestick patterns in sequence."""
    return get_default_engine().detect_patterns(candles, pattern_ids=pattern_ids)


def detect_patterns_at(
    candles: Sequence[Any],
    index: int,
    pattern_ids: Sequence[str] | None = None,
) -> list[CandlestickPattern]:
    """Convenience function: detect candlestick patterns concluding at index."""
    return get_default_engine().detect_patterns_at(candles, index, pattern_ids=pattern_ids)
