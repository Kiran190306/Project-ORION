"""Pure, deterministic mathematical rules for candlestick pattern detection.

All calculations use Decimal precision, strictly prohibit division by zero,
and enforce causal, zero-lookahead semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .models import (
    CandlestickPattern,
    PatternDirection,
    PatternStrength,
)


@dataclass(frozen=True, slots=True)
class CanonicalCandle:
    """Normalized candle representation with precomputed metrics."""

    index: int
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    range: Decimal
    body: Decimal
    upper_shadow: Decimal
    lower_shadow: Decimal
    is_bullish: bool
    is_bearish: bool
    is_flat: bool


def normalize_candle(raw: Any, index: int = 0) -> CanonicalCandle:
    """Normalize any candle-like object (OHLCV, Bar, dict, etc.) into CanonicalCandle."""
    if isinstance(raw, dict):
        ts = raw.get("timestamp")
        open_val = Decimal(str(raw["open"]))
        high_val = Decimal(str(raw["high"]))
        low_val = Decimal(str(raw["low"]))
        close_val = Decimal(str(raw["close"]))
        vol_val = Decimal(str(raw.get("volume", "0") or "0"))
    else:
        ts = getattr(raw, "timestamp", None)
        open_val = Decimal(str(getattr(raw, "open")))
        high_val = Decimal(str(getattr(raw, "high")))
        low_val = Decimal(str(getattr(raw, "low")))
        close_val = Decimal(str(getattr(raw, "close")))
        vol_val = Decimal(str(getattr(raw, "volume", 0) or 0))

    if ts is None:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(ts, datetime):
        timestamp = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    elif isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(ts, str):
        timestamp = datetime.fromisoformat(ts)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    if high_val < low_val:
        raise ValueError(f"High ({high_val}) cannot be strictly less than Low ({low_val})")

    c_range = high_val - low_val
    c_body = abs(close_val - open_val)
    upper_shadow = high_val - max(open_val, close_val)
    lower_shadow = min(open_val, close_val) - low_val

    return CanonicalCandle(
        index=index,
        timestamp=timestamp,
        open=open_val,
        high=high_val,
        low=low_val,
        close=close_val,
        volume=vol_val,
        range=c_range,
        body=c_body,
        upper_shadow=upper_shadow,
        lower_shadow=lower_shadow,
        is_bullish=close_val > open_val,
        is_bearish=close_val < open_val,
        is_flat=close_val == open_val,
    )


# ─── 1. DOJI ─────────────────────────────────────────────────────────────────


def detect_doji(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Doji: Small real body relative to total range with bilateral shadows."""
    if not window:
        return None
    c = window[-1]
    if c.range <= Decimal("0"):
        return None

    body_ratio = c.body / c.range
    # Body is <= 10% of total range, with non-zero upper and lower shadows
    if (
        body_ratio <= Decimal("0.10")
        and c.upper_shadow >= Decimal("0.05") * c.range
        and c.lower_shadow >= Decimal("0.05") * c.range
    ):
        confidence = (Decimal("1.00") - body_ratio * Decimal("5.0")).quantize(Decimal("0.01"))
        confidence = max(Decimal("0.50"), min(Decimal("1.00"), confidence))
        return CandlestickPattern(
            pattern_id="doji",
            name="Doji",
            direction=PatternDirection.NEUTRAL,
            strength=PatternStrength.MODERATE,
            candle_index=c.index,
            timestamp=c.timestamp,
            description="Indecision candle with tiny body and bilateral shadows",
            confidence=confidence,
            metadata={"body_ratio": str(body_ratio)},
        )
    return None


# ─── 2. HAMMER ───────────────────────────────────────────────────────────────


def detect_hammer(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Hammer: Bullish reversal with small body at upper end and long lower shadow (>= 2x body)."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c0.range <= Decimal("0") or c0.body <= Decimal("0"):
        return None

    lower_ratio = c0.lower_shadow / c0.body
    upper_ratio = c0.upper_shadow / c0.range
    body_ratio = c0.body / c0.range

    # Long lower shadow (>= 2x body), tiny upper shadow (<= 15% range), small body (<= 35% range)
    if lower_ratio >= Decimal("2.0") and upper_ratio <= Decimal("0.15") and body_ratio <= Decimal("0.35"):
        # Context: prior downward movement / bearish candle
        if c_prev.is_bearish or c_prev.close < c_prev.open or c0.close < c_prev.open:
            confidence = min(Decimal("1.00"), Decimal("0.70") + (lower_ratio - Decimal("2.0")) * Decimal("0.10"))
            return CandlestickPattern(
                pattern_id="hammer",
                name="Hammer",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bullish reversal with long lower shadow rejecting session lows",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"lower_shadow_to_body_ratio": str(lower_ratio)},
            )
    return None


# ─── 3. INVERTED HAMMER ──────────────────────────────────────────────────────


def detect_inverted_hammer(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Inverted Hammer: Bullish reversal with long upper shadow (>= 2x body) and small lower shadow."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c0.range <= Decimal("0") or c0.body <= Decimal("0"):
        return None

    upper_ratio = c0.upper_shadow / c0.body
    lower_ratio = c0.lower_shadow / c0.range
    body_ratio = c0.body / c0.range

    if upper_ratio >= Decimal("2.0") and lower_ratio <= Decimal("0.15") and body_ratio <= Decimal("0.35"):
        # Context: prior bearish pressure
        if c_prev.is_bearish or c_prev.close < c_prev.open:
            confidence = min(Decimal("1.00"), Decimal("0.65") + (upper_ratio - Decimal("2.0")) * Decimal("0.08"))
            return CandlestickPattern(
                pattern_id="inverted_hammer",
                name="Inverted Hammer",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.MODERATE,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bullish bottom reversal characterized by upper shadow buying probe",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"upper_shadow_to_body_ratio": str(upper_ratio)},
            )
    return None


# ─── 4. SHOOTING STAR ────────────────────────────────────────────────────────


def detect_shooting_star(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Shooting Star: Bearish reversal with long upper shadow (>= 2x body) following an upward move."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c0.range <= Decimal("0") or c0.body <= Decimal("0"):
        return None

    upper_ratio = c0.upper_shadow / c0.body
    lower_ratio = c0.lower_shadow / c0.range
    body_ratio = c0.body / c0.range

    if upper_ratio >= Decimal("2.0") and lower_ratio <= Decimal("0.15") and body_ratio <= Decimal("0.35"):
        # Context: prior bullish candle
        if c_prev.is_bullish or c_prev.close > c_prev.open:
            confidence = min(Decimal("1.00"), Decimal("0.75") + (upper_ratio - Decimal("2.0")) * Decimal("0.10"))
            return CandlestickPattern(
                pattern_id="shooting_star",
                name="Shooting Star",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bearish top reversal with extended upper shadow rejecting session highs",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"upper_shadow_to_body_ratio": str(upper_ratio)},
            )
    return None


# ─── 5. HANGING MAN ──────────────────────────────────────────────────────────


def detect_hanging_man(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Hanging Man: Bearish reversal with long lower shadow (>= 2x body) occurring after an advance."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c0.range <= Decimal("0") or c0.body <= Decimal("0"):
        return None

    lower_ratio = c0.lower_shadow / c0.body
    upper_ratio = c0.upper_shadow / c0.range
    body_ratio = c0.body / c0.range

    if lower_ratio >= Decimal("2.0") and upper_ratio <= Decimal("0.15") and body_ratio <= Decimal("0.35"):
        # Context: occurs at peak after bullish candle
        if c_prev.is_bullish or c0.close > c_prev.open:
            confidence = min(Decimal("1.00"), Decimal("0.65") + (lower_ratio - Decimal("2.0")) * Decimal("0.08"))
            return CandlestickPattern(
                pattern_id="hanging_man",
                name="Hanging Man",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.MODERATE,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bearish top warning signal with long lower shadow indicating emerging seller interest",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"lower_shadow_to_body_ratio": str(lower_ratio)},
            )
    return None


# ─── 6. BULLISH ENGULFING ────────────────────────────────────────────────────


def detect_bullish_engulfing(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Bullish Engulfing: Bullish candle body fully engulfs preceding bearish candle body."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c_prev.range <= Decimal("0") or c0.range <= Decimal("0"):
        return None

    if c_prev.is_bearish and c0.is_bullish and c_prev.body > Decimal("0") and c0.body > Decimal("0"):
        # FX 24h continuous market rules: open <= prev close, close >= prev open, with strict body engulfing
        is_engulfing = (
            c0.open <= c_prev.close
            and c0.close >= c_prev.open
            and (c0.open < c_prev.close or c0.close > c_prev.open)
            and c0.body > c_prev.body
        )
        if is_engulfing:
            ratio = c0.body / c_prev.body
            confidence = min(Decimal("1.00"), Decimal("0.75") + (ratio - Decimal("1.0")) * Decimal("0.15"))
            return CandlestickPattern(
                pattern_id="bullish_engulfing",
                name="Bullish Engulfing",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.STRONG,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bullish reversal: buyers decisively overwhelmed prior bearish session",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"engulfing_ratio": str(ratio)},
            )
    return None


# ─── 7. BEARISH ENGULFING ────────────────────────────────────────────────────


def detect_bearish_engulfing(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Bearish Engulfing: Bearish candle body fully engulfs preceding bullish candle body."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c_prev.range <= Decimal("0") or c0.range <= Decimal("0"):
        return None

    if c_prev.is_bullish and c0.is_bearish and c_prev.body > Decimal("0") and c0.body > Decimal("0"):
        is_engulfing = (
            c0.open >= c_prev.close
            and c0.close <= c_prev.open
            and (c0.open > c_prev.close or c0.close < c_prev.open)
            and c0.body > c_prev.body
        )
        if is_engulfing:
            ratio = c0.body / c_prev.body
            confidence = min(Decimal("1.00"), Decimal("0.75") + (ratio - Decimal("1.0")) * Decimal("0.15"))
            return CandlestickPattern(
                pattern_id="bearish_engulfing",
                name="Bearish Engulfing",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.STRONG,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bearish reversal: sellers decisively overwhelmed prior bullish session",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"engulfing_ratio": str(ratio)},
            )
    return None


# ─── 8. BULLISH HARAMI ───────────────────────────────────────────────────────


def detect_bullish_harami(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Bullish Harami: Small bullish candle body completely contained inside prior large bearish body."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c_prev.range <= Decimal("0") or c0.range <= Decimal("0"):
        return None

    if c_prev.is_bearish and c0.is_bullish and c_prev.body > Decimal("0"):
        if c0.open > c_prev.close and c0.close < c_prev.open and c0.body < c_prev.body:
            ratio = c0.body / c_prev.body
            confidence = max(Decimal("0.60"), Decimal("0.85") - ratio * Decimal("0.25"))
            return CandlestickPattern(
                pattern_id="bullish_harami",
                name="Bullish Harami",
                direction=PatternDirection.BULLISH,
                strength=PatternStrength.MODERATE,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bullish reversal: contraction candle contained inside prior bearish body",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"body_ratio": str(ratio)},
            )
    return None


# ─── 9. BEARISH HARAMI ───────────────────────────────────────────────────────


def detect_bearish_harami(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Bearish Harami: Small bearish candle body completely contained inside prior large bullish body."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c_prev.range <= Decimal("0") or c0.range <= Decimal("0"):
        return None

    if c_prev.is_bullish and c0.is_bearish and c_prev.body > Decimal("0"):
        if c0.open < c_prev.close and c0.close > c_prev.open and c0.body < c_prev.body:
            ratio = c0.body / c_prev.body
            confidence = max(Decimal("0.60"), Decimal("0.85") - ratio * Decimal("0.25"))
            return CandlestickPattern(
                pattern_id="bearish_harami",
                name="Bearish Harami",
                direction=PatternDirection.BEARISH,
                strength=PatternStrength.MODERATE,
                candle_index=c0.index,
                timestamp=c0.timestamp,
                description="Bearish reversal: contraction candle contained inside prior bullish body",
                confidence=confidence.quantize(Decimal("0.01")),
                metadata={"body_ratio": str(ratio)},
            )
    return None


# ─── 10. INSIDE BAR ──────────────────────────────────────────────────────────


def detect_inside_bar(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Inside Bar: Entire current price range is contained within previous candle's range."""
    if len(window) < 2:
        return None
    c_prev, c0 = window[-2], window[-1]
    if c_prev.range <= Decimal("0") or c0.range <= Decimal("0"):
        return None

    if c0.high <= c_prev.high and c0.low >= c_prev.low:
        ratio = c0.range / c_prev.range
        confidence = max(Decimal("0.60"), Decimal("0.90") - ratio * Decimal("0.30"))
        return CandlestickPattern(
            pattern_id="inside_bar",
            name="Inside Bar",
            direction=PatternDirection.NEUTRAL,
            strength=PatternStrength.MODERATE,
            candle_index=c0.index,
            timestamp=c0.timestamp,
            description="Volatility contraction: price range strictly contained within previous bar",
            confidence=confidence.quantize(Decimal("0.01")),
            metadata={"range_ratio": str(ratio)},
        )
    return None


# ─── 11. MORNING STAR ────────────────────────────────────────────────────────


def detect_morning_star(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Morning Star: 3-candle bullish reversal (long bear, small star, strong bull closing > 50% midpoint)."""
    if len(window) < 3:
        return None
    c1, c2, c3 = window[-3], window[-2], window[-1]
    if c1.range <= Decimal("0") or c3.range <= Decimal("0"):
        return None

    if c1.is_bearish and c3.is_bullish:
        if c1.body >= Decimal("0.50") * c1.range and c1.body > Decimal("0"):
            # Star candle (c2) has small body and low close
            if c2.body <= Decimal("0.35") * c1.body and min(c2.open, c2.close) <= c1.close:
                # Reversal candle (c3) penetrates above 50% midpoint of c1 body
                midpoint = (c1.open + c1.close) / Decimal("2.0")
                if c3.close >= midpoint:
                    penetration = (c3.close - midpoint) / (c1.open - midpoint) if c1.open > midpoint else Decimal("1.0")
                    confidence = min(Decimal("1.00"), Decimal("0.80") + penetration * Decimal("0.15"))
                    return CandlestickPattern(
                        pattern_id="morning_star",
                        name="Morning Star",
                        direction=PatternDirection.BULLISH,
                        strength=PatternStrength.STRONG,
                        candle_index=c3.index,
                        timestamp=c3.timestamp,
                        description="3-bar bullish bottom reversal with central star and deep bullish recovery",
                        confidence=confidence.quantize(Decimal("0.01")),
                        metadata={"midpoint": str(midpoint)},
                    )
    return None


# ─── 12. EVENING STAR ────────────────────────────────────────────────────────


def detect_evening_star(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Evening Star: 3-candle bearish reversal (long bull, small star, strong bear closing < 50% midpoint)."""
    if len(window) < 3:
        return None
    c1, c2, c3 = window[-3], window[-2], window[-1]
    if c1.range <= Decimal("0") or c3.range <= Decimal("0"):
        return None

    if c1.is_bullish and c3.is_bearish:
        if c1.body >= Decimal("0.50") * c1.range and c1.body > Decimal("0"):
            # Star candle (c2) has small body and high close
            if c2.body <= Decimal("0.35") * c1.body and max(c2.open, c2.close) >= c1.close:
                # Reversal candle (c3) penetrates below 50% midpoint of c1 body
                midpoint = (c1.open + c1.close) / Decimal("2.0")
                if c3.close <= midpoint:
                    penetration = (midpoint - c3.close) / (midpoint - c1.open) if midpoint > c1.open else Decimal("1.0")
                    confidence = min(Decimal("1.00"), Decimal("0.80") + penetration * Decimal("0.15"))
                    return CandlestickPattern(
                        pattern_id="evening_star",
                        name="Evening Star",
                        direction=PatternDirection.BEARISH,
                        strength=PatternStrength.STRONG,
                        candle_index=c3.index,
                        timestamp=c3.timestamp,
                        description="3-bar bearish top reversal with central star and deep bearish close",
                        confidence=confidence.quantize(Decimal("0.01")),
                        metadata={"midpoint": str(midpoint)},
                    )
    return None


# ─── 13. THREE WHITE SOLDIERS ────────────────────────────────────────────────


def detect_three_white_soldiers(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Three White Soldiers: Three consecutive long bullish bars with advancing opens and closes."""
    if len(window) < 3:
        return None
    c1, c2, c3 = window[-3], window[-2], window[-1]

    if c1.is_bullish and c2.is_bullish and c3.is_bullish:
        # Higher closes and higher opens
        if c1.close < c2.close < c3.close and c1.open < c2.open < c3.open:
            # Each bar opens within or near the previous bar's body
            if c2.open >= c1.open and c2.open <= c1.close and c3.open >= c2.open and c3.open <= c2.close:
                # Controlled upper shadows (<= 30% range) and meaningful bodies (>= 50% range)
                if (
                    c1.upper_shadow <= Decimal("0.30") * c1.range
                    and c2.upper_shadow <= Decimal("0.30") * c2.range
                    and c3.upper_shadow <= Decimal("0.30") * c3.range
                    and c1.body >= Decimal("0.50") * c1.range
                    and c2.body >= Decimal("0.50") * c2.range
                    and c3.body >= Decimal("0.50") * c3.range
                ):
                    return CandlestickPattern(
                        pattern_id="three_white_soldiers",
                        name="Three White Soldiers",
                        direction=PatternDirection.BULLISH,
                        strength=PatternStrength.STRONG,
                        candle_index=c3.index,
                        timestamp=c3.timestamp,
                        description="Three consecutive advancing bullish candles demonstrating sustained buying force",
                        confidence=Decimal("0.90"),
                    )
    return None


# ─── 14. THREE BLACK CROWS ───────────────────────────────────────────────────


def detect_three_black_crows(window: tuple[CanonicalCandle, ...]) -> CandlestickPattern | None:
    """Three Black Crows: Three consecutive long bearish bars with declining opens and closes."""
    if len(window) < 3:
        return None
    c1, c2, c3 = window[-3], window[-2], window[-1]

    if c1.is_bearish and c2.is_bearish and c3.is_bearish:
        # Lower closes and lower opens
        if c1.close > c2.close > c3.close and c1.open > c2.open > c3.open:
            # Each bar opens within the previous bar's body
            if c2.open <= c1.open and c2.open >= c1.close and c3.open <= c2.open and c3.open >= c2.close:
                # Controlled lower shadows (<= 30% range) and meaningful bodies (>= 50% range)
                if (
                    c1.lower_shadow <= Decimal("0.30") * c1.range
                    and c2.lower_shadow <= Decimal("0.30") * c2.range
                    and c3.lower_shadow <= Decimal("0.30") * c3.range
                    and c1.body >= Decimal("0.50") * c1.range
                    and c2.body >= Decimal("0.50") * c2.range
                    and c3.body >= Decimal("0.50") * c3.range
                ):
                    return CandlestickPattern(
                        pattern_id="three_black_crows",
                        name="Three Black Crows",
                        direction=PatternDirection.BEARISH,
                        strength=PatternStrength.STRONG,
                        candle_index=c3.index,
                        timestamp=c3.timestamp,
                        description="Three consecutive declining bearish candles demonstrating sustained selling force",
                        confidence=Decimal("0.90"),
                    )
    return None
