"""Momentum Strategy - reference implementation.

A deterministic strategy that generates signals based on
price momentum (rate of change).
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


class MomentumStrategy(BaseStrategy):
    """A simple momentum strategy using rate of change.

    This is a deterministic reference implementation for demonstration
    and testing purposes only.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        momentum_period: int = 14,
        momentum_threshold: float = 0.02,
        **kwargs: object,
    ) -> None:
        parameters = {
            "momentum_period": momentum_period,
            "momentum_threshold": momentum_threshold,
            **kwargs,
        }
        super().__init__(metadata, parameters)
        self._momentum_period = momentum_period
        self._momentum_threshold = Decimal(str(momentum_threshold))
        self._prices: list[Decimal] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a momentum signal based on rate of change.

        Args:
            context: Current market and account context.

        Returns:
            A Signal or None.
        """
        self._prices.append(context.current_price)

        if len(self._prices) <= self._momentum_period:
            return None

        past_price = self._prices[-(self._momentum_period + 1)]
        current_price = context.current_price

        if past_price == Decimal(0):
            return None

        momentum = (current_price - past_price) / past_price

        if momentum > self._momentum_threshold:
            direction = SignalDirection.BUY
            strength = SignalStrength.STRONG
            confidence = min(float(momentum * 10), 0.95)
            reason = f"Positive momentum: {momentum:.4f}"
        elif momentum < -self._momentum_threshold:
            direction = SignalDirection.SELL
            strength = SignalStrength.STRONG
            confidence = min(float(abs(momentum) * 10), 0.95)
            reason = f"Negative momentum: {momentum:.4f}"
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