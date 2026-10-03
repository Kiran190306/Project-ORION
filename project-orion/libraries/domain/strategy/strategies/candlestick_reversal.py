"""Candlestick Reversal Strategy - deterministic price action implementation.

Executes trades based on precomputed candlestick reversal patterns injected
into StrategyContext metadata, using confirming candle extremes for stop-loss
placement and strict invalid-stop filtering.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from libraries.domain.patterns.models import (
    CandlestickPattern,
    PatternDirection,
    PatternStrength,
)
from libraries.domain.patterns.registry import get_default_pattern_registry
from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    PositionIntent,
    PositionSide,
    Signal,
    SignalDirection,
    SignalStrength,
    StrategyContext,
    StrategyMetadata,
)

VALID_PATTERN_IDS: tuple[str, ...] = (
    "any_reversal",
    "hammer",
    "inverted_hammer",
    "bullish_engulfing",
    "bearish_engulfing",
    "morning_star",
    "evening_star",
    "shooting_star",
    "hanging_man",
    "bullish_harami",
    "bearish_harami",
    "doji",
    "inside_bar",
    "three_white_soldiers",
    "three_black_crows",
)

VALID_PATTERN_DIRECTIONS: tuple[str, ...] = (
    "all",
    "bullish_only",
    "bearish_only",
)

VALID_MIN_STRENGTHS: tuple[str, ...] = (
    "any",
    "moderate",
    "strong",
)

_STRENGTH_RANKS: dict[PatternStrength | str, int] = {
    PatternStrength.WEAK: 1,
    PatternStrength.MODERATE: 2,
    PatternStrength.STRONG: 3,
    "weak": 1,
    "moderate": 2,
    "strong": 3,
}

_MIN_STRENGTH_THRESHOLDS: dict[str, int] = {
    "any": 1,
    "moderate": 2,
    "strong": 3,
}


def get_pip_size(symbol: str) -> Decimal:
    """Return pip size for instrument: 0.01 for JPY pairs, 0.0001 for all others."""
    return Decimal("0.01") if "JPY" in symbol.upper() else Decimal("0.0001")


def _extract_candle_high_low(
    context: StrategyContext, pattern: CandlestickPattern
) -> tuple[Decimal | None, Decimal | None]:
    """Extract confirming candle high and low from context or pattern metadata."""
    # 1. Direct high/low in pattern metadata
    if "high" in pattern.metadata and "low" in pattern.metadata:
        return Decimal(str(pattern.metadata["high"])), Decimal(str(pattern.metadata["low"]))
    if "candle_high" in pattern.metadata and "candle_low" in pattern.metadata:
        return Decimal(str(pattern.metadata["candle_high"])), Decimal(str(pattern.metadata["candle_low"]))

    # 2. From context current_candle
    current_candle = context.metadata.get("current_candle")
    if current_candle is not None:
        high = getattr(current_candle, "high", None) if not isinstance(current_candle, dict) else current_candle.get("high")
        low = getattr(current_candle, "low", None) if not isinstance(current_candle, dict) else current_candle.get("low")
        if high is not None and low is not None:
            return Decimal(str(high)), Decimal(str(low))

    # 3. From context historical_candles (last bar)
    hist = context.metadata.get("historical_candles")
    if hist and len(hist) > 0:
        last_c = hist[-1]
        high = getattr(last_c, "high", None) if not isinstance(last_c, dict) else last_c.get("high")
        low = getattr(last_c, "low", None) if not isinstance(last_c, dict) else last_c.get("low")
        if high is not None and low is not None:
            return Decimal(str(high)), Decimal(str(low))

    return None, None


class CandlestickReversalStrategy(BaseStrategy):
    """Deterministic price action strategy trading candlestick reversal patterns with confirmation.

    Consumes precomputed patterns from context.metadata["patterns"].
    Adheres strictly to the frozen contract:
    - Independent archetype (category="price_action", version="1.0.0")
    - Pattern filtering (any_reversal tag check, direction, min_strength, min_confidence)
    - Rejection of neutral patterns
    - Conflict rejection when both bullish and bearish patterns qualify
    - Deterministic arbitration tuple: (confidence, strength_rank, required_candles, pattern_id)
    - Strict SL calculation and invalid SL rejection (no clamping, no widening)
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        pattern_id: str = "any_reversal",
        pattern_direction: str = "all",
        min_strength: str = "moderate",
        min_confidence: float = 0.70,
        **kwargs: object,
    ) -> None:
        parameters = {
            "pattern_id": pattern_id,
            "pattern_direction": pattern_direction,
            "min_strength": min_strength,
            "min_confidence": min_confidence,
            **kwargs,
        }
        super().__init__(metadata, parameters)
        self._pattern_id = str(pattern_id)
        self._pattern_direction = str(pattern_direction)
        self._min_strength = str(min_strength)
        self._min_confidence = float(min_confidence)
        self._pattern_registry = get_default_pattern_registry()

    @property
    def pattern_id(self) -> str:
        return self._pattern_id

    @property
    def pattern_direction(self) -> str:
        return self._pattern_direction

    @property
    def min_strength(self) -> str:
        return self._min_strength

    @property
    def min_confidence(self) -> float:
        return self._min_confidence

    def _get_required_candles(self, pattern: CandlestickPattern) -> int:
        if "required_candles" in pattern.metadata:
            return int(pattern.metadata["required_candles"])
        defn = self._pattern_registry.get_definition(pattern.pattern_id)
        if defn is not None:
            return defn.required_candles
        return 1

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Evaluate candlestick patterns from context metadata and generate directional signals."""
        raw_patterns = context.metadata.get("patterns")
        if not raw_patterns:
            return None

        # 1. Filter qualifying patterns
        min_rank = _MIN_STRENGTH_THRESHOLDS.get(self._min_strength, 2)
        qualifying: list[CandlestickPattern] = []

        for p in raw_patterns:
            # Reject neutral patterns immediately (Doji, Inside Bar, etc. must never trade)
            if p.direction not in (PatternDirection.BULLISH, PatternDirection.BEARISH):
                continue

            # Check pattern_id match
            if self._pattern_id == "any_reversal":
                defn = self._pattern_registry.get_definition(p.pattern_id)
                if not defn or "reversal" not in defn.tags:
                    continue
            else:
                if p.pattern_id != self._pattern_id:
                    continue

            # Check direction filter
            if self._pattern_direction == "bullish_only" and p.direction != PatternDirection.BULLISH:
                continue
            if self._pattern_direction == "bearish_only" and p.direction != PatternDirection.BEARISH:
                continue

            # Check minimum strength
            p_rank = _STRENGTH_RANKS.get(p.strength, 1)
            if p_rank < min_rank:
                continue

            # Check minimum confidence
            if float(p.confidence) < self._min_confidence:
                continue

            qualifying.append(p)

        if not qualifying:
            return None

        # 2. Check for directional conflict (both bullish and bearish patterns on same bar)
        has_bullish = any(p.direction == PatternDirection.BULLISH for p in qualifying)
        has_bearish = any(p.direction == PatternDirection.BEARISH for p in qualifying)
        if has_bullish and has_bearish:
            return None

        # 3. Deterministic arbitration for same-direction patterns
        dominant_pattern = max(
            qualifying,
            key=lambda p: (
                float(p.confidence),
                _STRENGTH_RANKS.get(p.strength, 1),
                self._get_required_candles(p),
                p.pattern_id,
            ),
        )

        # 4. Stop loss calculation from confirming candle
        pip_size = get_pip_size(context.symbol)
        c_high, c_low = _extract_candle_high_low(context, dominant_pattern)
        if c_high is None or c_low is None:
            # Cannot determine confirming candle high/low -> reject entry
            return None

        current_price = context.current_price

        if dominant_pattern.direction == PatternDirection.BULLISH:
            stop_loss = c_low - pip_size
            # Frozen rule: if calculated SL >= current_price -> reject entry (return None)
            if stop_loss >= current_price:
                return None
            stop_distance = current_price - stop_loss
            if stop_distance < Decimal(5) * pip_size:
                return None
            direction = SignalDirection.BUY
        else:
            stop_loss = c_high + pip_size
            # Frozen rule: if calculated SL <= current_price -> reject entry (return None)
            if stop_loss <= current_price:
                return None
            stop_distance = stop_loss - current_price
            if stop_distance < Decimal(5) * pip_size:
                return None
            direction = SignalDirection.SELL

        strength = (
            SignalStrength.STRONG
            if dominant_pattern.strength == PatternStrength.STRONG
            else SignalStrength.MODERATE
        )

        return Signal(
            strategy_id=self.strategy_id,
            symbol=context.symbol,
            direction=direction,
            strength=strength,
            price=current_price,
            confidence=float(dominant_pattern.confidence),
            reason=f"Candlestick reversal: {dominant_pattern.pattern_id} ({dominant_pattern.strength.value}) with confidence {dominant_pattern.confidence}",
            metadata={
                "pattern_id": dominant_pattern.pattern_id,
                "pattern_confidence": float(dominant_pattern.confidence),
                "pattern_strength": dominant_pattern.strength.value if hasattr(dominant_pattern.strength, "value") else str(dominant_pattern.strength),
                "pattern_timestamp": dominant_pattern.timestamp.isoformat() if hasattr(dominant_pattern.timestamp, "isoformat") else str(dominant_pattern.timestamp),
                "stop_loss": str(stop_loss),
                "pip_size": str(pip_size),
            },
        )

    async def _size_position(
        self,
        signal: Signal,
        context: StrategyContext,
    ) -> PositionIntent:
        """Size position and set stop_loss on PositionIntent from signal metadata."""
        intent = await super()._size_position(signal, context)
        sl_val = signal.metadata.get("stop_loss")
        if sl_val is not None:
            return PositionIntent(
                strategy_id=intent.strategy_id,
                symbol=intent.symbol,
                side=intent.side,
                target_quantity=intent.target_quantity,
                stop_loss=Decimal(str(sl_val)),
                take_profit=intent.take_profit,
                max_risk=intent.max_risk,
                timestamp=intent.timestamp,
                reason=intent.reason,
                metadata=dict(intent.metadata),
            )
        return intent
