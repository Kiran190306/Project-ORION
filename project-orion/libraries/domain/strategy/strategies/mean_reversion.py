"""Mean Reversion Strategy - reference implementation.

A deterministic strategy that generates buy signals when price
is below its mean and sell signals when above.
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


class MeanReversionStrategy(BaseStrategy):
    """A simple mean reversion strategy using z-score logic.

    This is a deterministic reference implementation for demonstration
    and testing purposes only.
    """

    def __init__(
        self,
        metadata: StrategyMetadata,
        lookback_period: int = 20,
        entry_threshold: float = 2.0,
        **kwargs: object,
    ) -> None:
        parameters = {
            "lookback_period": lookback_period,
            "entry_threshold": entry_threshold,
            **kwargs,
        }
        super().__init__(metadata, parameters)
        self._lookback_period = lookback_period
        self._entry_threshold = Decimal(str(entry_threshold))
        self._prices: list[Decimal] = []

    async def generate_signal(self, context: StrategyContext) -> Signal | None:
        """Generate a mean reversion signal.

        Buys when price is below mean by threshold standard deviations.
        Sells when price is above mean by threshold standard deviations.

        Args:
            context: Current market and account context.

        Returns:
            A Signal or None.
        """
        self._prices.append(context.current_price)

        if len(self._prices) < self._lookback_period:
            return None

        mean = self._calculate_mean()
        std = self._calculate_std(mean)

        if std == Decimal(0):
            return None

        z_score = (context.current_price - mean) / std

        if z_score <= -self._entry_threshold:
            direction = SignalDirection.BUY
            confidence = min(float(abs(z_score) / Decimal(3)), 0.95)
            reason = f"Price below mean by {z_score:.2f} std devs"
        elif z_score >= self._entry_threshold:
            direction = SignalDirection.SELL
            confidence = min(float(abs(z_score) / Decimal(3)), 0.95)
            reason = f"Price above mean by {z_score:.2f} std devs"
        else:
            return None

        return Signal(
            strategy_id=self.strategy_id,
            symbol=context.symbol,
            direction=direction,
            strength=SignalStrength.MODERATE,
            price=context.current_price,
            confidence=confidence,
            reason=reason,
        )

    def _calculate_mean(self) -> Decimal:
        """Calculate the mean of recent prices."""
        recent = self._prices[-self._lookback_period:]
        total = sum(recent, Decimal(0))
        return total / Decimal(str(self._lookback_period))

    def _calculate_std(self, mean: Decimal) -> Decimal:
        """Calculate the population standard deviation."""
        recent = self._prices[-self._lookback_period:]
        period = Decimal(str(self._lookback_period))
        variance = sum((p - mean) ** 2 for p in recent) / period
        return variance.sqrt()
