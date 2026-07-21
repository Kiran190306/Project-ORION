"""Relative Strength Index (RSI) indicator.

Uses Wilder's smoothing method for the average gain/loss calculation.
O(1) incremental update.
"""

from __future__ import annotations

from typing import Any

from libraries.domain.indicators.base import BaseIndicator
from libraries.domain.indicators.interfaces import IndicatorConfig
from libraries.domain.indicators.models import (
    Bar,
    IndicatorMetadata,
    IndicatorResult,
    IndicatorType,
)


class RSI(BaseIndicator):
    """Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    where RS = avg_gain / avg_loss over the period.
    Uses Wilder's smoothed averages for incremental updates.
    """

    def __init__(self, period: int = 14) -> None:
        metadata = IndicatorMetadata(
            name="rsi",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="Relative Strength Index",
            version="1.0.0",
            description="Relative Strength Index - measures speed and change of price movements",
            min_period=period + 1,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._avg_gain: float = 0.0
        self._avg_loss: float = 0.0
        self._prev_close: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="rsi",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"RSI ({period})",
            version="1.0.0",
            description=f"Relative Strength Index (period={period})",
            min_period=period + 1,
            default_period=period,
            params=("period",),
        )
        self._avg_gain = 0.0
        self._avg_loss = 0.0
        self._prev_close = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if len(bars) < 2:
            return

        closes = [b.close for b in bars]
        period = self.required_period() - 1
        gains: list[float] = []
        losses: list[float] = []

        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0.0))
            losses.append(max(-diff, 0.0))

        if len(gains) >= period:
            self._avg_gain = sum(gains[:period]) / period
            self._avg_loss = sum(losses[:period]) / period
            for i in range(period, len(gains)):
                self._avg_gain = (self._avg_gain * (period - 1) + gains[i]) / period
                self._avg_loss = (self._avg_loss * (period - 1) + losses[i]) / period
        elif gains:
            self._avg_gain = sum(gains) / len(gains)
            self._avg_loss = sum(losses) / len(losses)

        self._prev_close = closes[-1] if closes else None

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period() - 1

        if self._prev_close is not None:
            diff = bar.close - self._prev_close
            gain = max(diff, 0.0)
            loss = max(-diff, 0.0)

            if self._avg_gain == 0.0 and self._avg_loss == 0.0:
                self._avg_gain = gain
                self._avg_loss = loss
            else:
                self._avg_gain = (self._avg_gain * (period - 1) + gain) / period
                self._avg_loss = (self._avg_loss * (period - 1) + loss) / period

        self._prev_close = bar.close

        rsi_value = 100.0
        if self._avg_loss > 0:
            rs = self._safe_div(self._avg_gain, self._avg_loss)
            rsi_value = 100.0 - (100.0 / (1.0 + rs))
        elif self._avg_gain > 0:
            rsi_value = 100.0

        return self._create_result(bar, value=rsi_value)

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["avg_gain"] = self._avg_gain
        data["state"]["avg_loss"] = self._avg_loss
        data["state"]["prev_close"] = self._prev_close
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "RSI":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._avg_gain = state.get("avg_gain", 0.0)
        instance._avg_loss = state.get("avg_loss", 0.0)
        instance._prev_close = state.get("prev_close")
        return instance
