"""Market state detection for the Trading Decision Engine.

Determines the current market regime: TRENDING, RANGING, BREAKOUT,
REVERSAL, HIGH_VOLATILITY, LOW_VOLATILITY, NEWS_MODE.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class MarketStateType(StrEnum):
    """Types of market states that can be detected."""

    TRENDING = "trending"
    RANGING = "ranging"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    NEWS_MODE = "news_mode"


@dataclass(frozen=True, slots=True)
class MarketState:
    """Immutable market state detection result."""

    state_type: MarketStateType
    symbol: str
    confidence: float  # 0.0 to 1.0
    trend_strength: float = 0.0  # 0.0 to 1.0
    volatility_percentile: float = 0.5  # 0.0 to 1.0
    is_breaking_out: bool = False
    is_reversing: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MarketStateDetector:
    """Detects market states from price, volatility, and volume data.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        trending_threshold: float = 0.6,
        breakout_threshold: float = 2.0,
        reversal_threshold: float = 0.7,
        high_volatility_percentile: float = 0.8,
        low_volatility_percentile: float = 0.2,
    ) -> None:
        if not 0 < trending_threshold < 1:
            raise ValueError("trending_threshold must be between 0 and 1")
        if breakout_threshold <= 0:
            raise ValueError("breakout_threshold must be positive")
        if not 0 < reversal_threshold < 1:
            raise ValueError("reversal_threshold must be between 0 and 1")

        self._trending_threshold = trending_threshold
        self._breakout_threshold = breakout_threshold
        self._reversal_threshold = reversal_threshold
        self._high_volatility_percentile = high_volatility_percentile
        self._low_volatility_percentile = low_volatility_percentile
        self._lock = asyncio.Lock()

    @property
    def trending_threshold(self) -> float:
        return self._trending_threshold

    @property
    def breakout_threshold(self) -> float:
        return self._breakout_threshold

    async def detect(
        self,
        symbol: str,
        trend_strength: float,
        volatility_percentile: float,
        is_breaking_out: bool = False,
        is_reversing: bool = False,
        is_news_mode: bool = False,
    ) -> MarketState:
        """Detect the current market state based on input indicators.

        Args:
            symbol: Trading symbol.
            trend_strength: ADX-like trend strength 0.0-1.0.
            volatility_percentile: Current volatility percentile 0.0-1.0.
            is_breaking_out: Whether price is breaking out of a range.
            is_reversing: Whether a trend reversal is detected.
            is_news_mode: Whether news-mode is active.

        Returns:
            MarketState with the detected regime.
        """
        async with self._lock:
            if is_news_mode:
                state_type = MarketStateType.NEWS_MODE
            elif is_reversing and trend_strength > self._reversal_threshold:
                state_type = MarketStateType.REVERSAL
            elif is_breaking_out:
                state_type = MarketStateType.BREAKOUT
            elif volatility_percentile >= self._high_volatility_percentile:
                state_type = MarketStateType.HIGH_VOLATILITY
            elif volatility_percentile <= self._low_volatility_percentile:
                state_type = MarketStateType.LOW_VOLATILITY
            elif trend_strength >= self._trending_threshold:
                state_type = MarketStateType.TRENDING
            else:
                state_type = MarketStateType.RANGING

            confidence = self._compute_confidence(
                state_type, trend_strength, volatility_percentile, is_breaking_out, is_reversing
            )

            return MarketState(
                state_type=state_type,
                symbol=symbol,
                confidence=confidence,
                trend_strength=trend_strength,
                volatility_percentile=volatility_percentile,
                is_breaking_out=is_breaking_out,
                is_reversing=is_reversing,
                details={
                    "trending_threshold": self._trending_threshold,
                    "breakout_threshold": self._breakout_threshold,
                    "reversal_threshold": self._reversal_threshold,
                },
            )

    def _compute_confidence(
        self,
        state_type: MarketStateType,
        trend_strength: float,
        volatility_percentile: float,
        is_breaking_out: bool,
        is_reversing: bool,
    ) -> float:
        """Compute confidence in the detected market state."""
        if state_type == MarketStateType.NEWS_MODE:
            return 0.8
        if state_type == MarketStateType.BREAKOUT:
            return min(1.0, trend_strength * 1.2 + 0.2)
        if state_type == MarketStateType.REVERSAL:
            return min(1.0, trend_strength * 0.9 + 0.1)
        if state_type == MarketStateType.TRENDING:
            return min(1.0, trend_strength * 1.1)
        if state_type == MarketStateType.HIGH_VOLATILITY:
            return min(1.0, volatility_percentile * 1.1)
        if state_type == MarketStateType.LOW_VOLATILITY:
            return min(1.0, (1.0 - volatility_percentile) * 1.2)
        # RANGING
        return max(0.3, 1.0 - trend_strength)
