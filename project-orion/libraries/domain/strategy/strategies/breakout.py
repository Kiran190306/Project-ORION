"""Breakout Strategy - reference implementation.

A deterministic strategy that generates signals when price
breaks out of a defined range (high/low channel).
"""

from __future__ import annotations

from decimal import Decimal

from libraries.domain.strategy.base import BaseStrategy
from libraries.domain.strategy.models import (
    Signal,
    SignalDirection,
    SignalStrength,
    StrategyContext,
    StrategyMetadata,
)


class BreakoutStrategy(BaseStrategy):
    """A simple breakout strategy using price channel breakouts.

    This is a deterministic reference implementation for demonstration
    and testing purposes only.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        channel_period: int = 20,
        breakout_multiplier: float = 1.0,
        **kwargs: object,
    ) -> None:
        parameters = {
            "channel_period": channel_period,
            "breakout_multiplier": breakout_multiplier,
            **kwargs,
        }
        super().__init__(metadata, parameters)
        self._channel_period = channel_period
        self._breakout_multiplier = Decimal(str(breakout_multiplier))
        self._highs: list[Decimal] = []
        self._lows: list[Decimal] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a breakout signal.

        Buys when price breaks above the channel high.
        Sells when price breaks below the channel low.

        Args:
            context: Current market and account context.

        Returns:
            A Signal or None.
        """
        self._highs.append(context.current_price)
        self._lows.append(context.current_price)

        if len(self._highs) < self._channel_period:
            return None

        channel_high = max(self._highs[-self._channel_period:])
        channel_low = min(self._lows[-self._channel_period:])
        channel_range = channel_high - channel_low
        buffer = channel_range * self._breakout_multiplier

        current_price = context.current_price

        if current_price > channel_high + buffer:
            direction = SignalDirection.BUY
            strength = SignalStrength.STRONG
            confidence = 0.85
            reason = f"Bullish breakout above {channel_high}"
        elif current_price < channel_low - buffer:
            direction = SignalDirection.SELL
            strength = SignalStrength.STRONG
            confidence = 0.85
            reason = f"Bearish breakout below {channel_low}"
        else:
            return None

        return Signal(
            strategy_id=self.strategy_id,
            symbol=context.symbol,
            direction=direction,
            strength=strength,
            price=current_price,
            confidence=confidence,
            reason=reason,
        )