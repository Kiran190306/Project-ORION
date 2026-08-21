"""Signal generator for the Trading Decision Engine.

Generates trading signals (BUY, SELL, EXIT, HOLD, SCALE_IN, SCALE_OUT)
based on market state, technical indicators, and strategy configuration.
"""

from __future__ import annotations

import asyncio
from typing import Any

from libraries.domain.trading.market_state import MarketState, MarketStateType
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection, SignalStrength


class SignalGenerator:
    """Generates trading signals based on market state and indicators.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        min_confidence_threshold: float = 20.0,
        breakout_confirmation_bars: int = 3,
    ) -> None:
        if not 0 <= min_confidence_threshold <= 100:
            raise ValueError("min_confidence_threshold must be between 0 and 100")
        self._min_confidence_threshold = min_confidence_threshold
        self._breakout_confirmation_bars = breakout_confirmation_bars
        self._lock = asyncio.Lock()

    @property
    def min_confidence_threshold(self) -> float:
        return self._min_confidence_threshold

    async def generate(
        self,
        symbol: str,
        market_state: MarketState,
        strategy: StrategyType,
        trend_strength: float = 0.0,
        rsi: float = 50.0,
        volume_ratio: float = 1.0,
        price_position: float = 0.5,  # 0.0 = low of range, 1.0 = high of range
        metadata: dict[str, Any] | None = None,
    ) -> TradingSignal | None:
        """Generate a trading signal based on current market conditions.

        Args:
            symbol: Trading symbol.
            market_state: Current detected market state.
            strategy: Target strategy type.
            trend_strength: ADX-like trend strength 0.0-1.0.
            rsi: RSI value (0-100).
            volume_ratio: Current volume / average volume ratio.
            price_position: Position within recent range 0.0-1.0.
            metadata: Optional metadata.

        Returns:
            TradingSignal if conditions are met, None if HOLD.
        """
        async with self._lock:
            direction = self._determine_direction(
                market_state, strategy, trend_strength, rsi, volume_ratio, price_position
            )
            if direction == SignalDirection.HOLD:
                return None

            strength = self._determine_strength(
                direction, market_state, trend_strength, rsi, volume_ratio
            )
            confidence = self._compute_confidence(
                direction, strength, market_state, trend_strength, rsi
            )

            if confidence < self._min_confidence_threshold:
                return None

            return TradingSignal(
                direction=direction,
                strength=strength,
                strategy=strategy,
                symbol=symbol,
                confidence_score=confidence,
                metadata={
                    "market_state": market_state.state_type.value,
                    "trend_strength": trend_strength,
                    "rsi": rsi,
                    "volume_ratio": volume_ratio,
                    "price_position": price_position,
                    **(metadata or {}),
                },
            )

    def _determine_direction(
        self,
        market_state: MarketState,
        strategy: StrategyType,
        trend_strength: float,
        rsi: float,
        volume_ratio: float,
        price_position: float,
    ) -> SignalDirection:
        """Determine signal direction based on market state and strategy."""
        # News mode: always HOLD
        if market_state.state_type == MarketStateType.NEWS_MODE:
            return SignalDirection.HOLD

        # Breakout: direction based on breakout direction
        if market_state.state_type == MarketStateType.BREAKOUT:
            if volume_ratio > 1.5 and price_position > 0.8:
                return SignalDirection.BUY
            elif volume_ratio > 1.5 and price_position < 0.2:
                return SignalDirection.SELL
            return SignalDirection.HOLD

        # Reversal: direction based on trend direction
        if market_state.state_type == MarketStateType.REVERSAL:
            if rsi < 30 and trend_strength > 0.5:
                return SignalDirection.BUY
            elif rsi > 70 and trend_strength > 0.5:
                return SignalDirection.SELL
            return SignalDirection.HOLD

        # Trending: follow the trend
        if market_state.state_type == MarketStateType.TRENDING:
            if trend_strength > 0.7 and price_position > 0.6:
                return SignalDirection.BUY
            elif trend_strength > 0.7 and price_position < 0.4:
                return SignalDirection.SELL
            return SignalDirection.HOLD

        # Ranging: mean reversion
        if market_state.state_type == MarketStateType.RANGING:
            if rsi < 30 and price_position < 0.3:
                return SignalDirection.BUY
            elif rsi > 70 and price_position > 0.7:
                return SignalDirection.SELL
            return SignalDirection.HOLD

        # High volatility: cautious
        if market_state.state_type == MarketStateType.HIGH_VOLATILITY:
            if rsi < 25 and price_position < 0.2:
                return SignalDirection.BUY
            elif rsi > 75 and price_position > 0.8:
                return SignalDirection.SELL
            return SignalDirection.HOLD

        # Low volatility: prepare for breakout
        if market_state.state_type == MarketStateType.LOW_VOLATILITY:
            if price_position > 0.8 and volume_ratio > 1.2:
                return SignalDirection.SCALE_IN
            elif price_position < 0.2 and volume_ratio > 1.2:
                return SignalDirection.SCALE_OUT
            return SignalDirection.HOLD

        return SignalDirection.HOLD

    def _determine_strength(
        self,
        direction: SignalDirection,
        market_state: MarketState,
        trend_strength: float,
        rsi: float,
        volume_ratio: float,
    ) -> SignalStrength:
        """Determine signal strength based on conviction."""
        score = 0.0

        # Market state confidence
        score += market_state.confidence * 0.3

        # Trend strength contribution
        score += trend_strength * 0.2

        # RSI extremity
        if direction == SignalDirection.BUY:
            rsi_contribution = max(0, (50 - rsi) / 50) * 0.25
        elif direction == SignalDirection.SELL:
            rsi_contribution = max(0, (rsi - 50) / 50) * 0.25
        else:
            rsi_contribution = 0.0
        score += rsi_contribution

        # Volume confirmation
        score += min(1.0, volume_ratio / 2.0) * 0.25

        if score >= 0.7:
            return SignalStrength.STRONG
        elif score >= 0.4:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def _compute_confidence(
        self,
        direction: SignalDirection,
        strength: SignalStrength,
        market_state: MarketState,
        trend_strength: float,
        rsi: float,
    ) -> float:
        """Compute confidence score 0-100 for the signal."""
        base = {
            SignalStrength.STRONG: 75.0,
            SignalStrength.MODERATE: 50.0,
            SignalStrength.WEAK: 25.0,
        }.get(strength, 0.0)

        adjustments = 0.0
        adjustments += market_state.confidence * 15.0
        adjustments += trend_strength * 10.0

        if direction == SignalDirection.BUY and rsi < 30 or direction == SignalDirection.SELL and rsi > 70:
            adjustments += 10.0

        return max(0.0, min(100.0, base + adjustments))
