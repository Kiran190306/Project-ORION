"""Trend Following Strategy - reference implementation.

A deterministic strategy that generates buy signals when price
is above a moving average and sell signals when below.
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


class TrendFollowingStrategy(BaseStrategy):
    """A simple trend-following strategy using moving average crossover logic.

    This is a deterministic reference implementation for demonstration
    and testing purposes only.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        fast_period: int = 10,
        slow_period: int = 30,
        **kwargs: object,
    ) -> None:
        parameters = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            **kwargs,
        }
        super().__init__(metadata, parameters)
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._prices: list[Decimal] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a trend-following signal based on price action.

        Uses a simplified moving average comparison:
        - If fast > slow: BUY (uptrend)
        - If fast < slow: SELL (downtrend)
        - Otherwise: HOLD

        Args:
            context: Current market and account context.

        Returns:
            A Signal or None.
        """
        self._prices.append(context.current_price)

        # Need enough data for both periods
        if len(self._prices) < self._slow_period:
            return None

        fast_ma = self._calculate_ma(self._fast_period)
        slow_ma = self._calculate_ma(self._slow_period)

        if fast_ma > slow_ma:
            direction = SignalDirection.BUY
            strength = SignalStrength.STRONG
            confidence = 0.8
            reason = f"Trend up: fast MA ({fast_ma}) > slow MA ({slow_ma})"
        elif fast_ma < slow_ma:
            direction = SignalDirection.SELL
            strength = SignalStrength.STRONG
            confidence = 0.8
            reason = f"Trend down: fast MA ({fast_ma}) < slow MA ({slow_ma})"
        else:
            return None

        return Signal(
            strategy_id=self.strategy_id,
            symbol=context.symbol,
            direction=direction,
            strength=strength,
            price=context.current_price,
            confidence=confidence,
            reason=reason,
        )

    def _calculate_ma(self, period: int) -> Decimal:
        """Calculate simple moving average for the given period."""
        if len(self._prices) < period:
            return Decimal(0)
        recent = self._prices[-period:]
        total = sum(recent, Decimal(0))
        return total / Decimal(str(period))