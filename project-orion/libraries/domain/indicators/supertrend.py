"""SuperTrend indicator.

Uses ATR-based bands to determine trend direction and reversals.
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


class SuperTrend(BaseIndicator):
    """SuperTrend Indicator.

    Basic bands:
      Upper = (high + low) / 2 + multiplier * ATR
      Lower = (high + low) / 2 - multiplier * ATR

    Flipped when price crosses the band.
    """

    def __init__(self, period: int = 10, multiplier: float = 3.0) -> None:
        metadata = IndicatorMetadata(
            name="supertrend",
            indicator_type=IndicatorType.TREND,
            display_name="SuperTrend",
            version="1.0.0",
            description="SuperTrend - ATR-based trend following indicator",
            min_period=period,
            default_period=period,
            params=("period", "multiplier"),
        )
        super().__init__(metadata)
        self._multiplier = multiplier
        self._atr_values: list[float] = []
        self._upper_band: float | None = None
        self._lower_band: float | None = None
        self._trend_up: bool = True
        self._prev_close: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._multiplier = float(config.get("multiplier", 3.0))
        self._metadata = IndicatorMetadata(
            name="supertrend",
            indicator_type=IndicatorType.TREND,
            display_name=f"SuperTrend ({period},{self._multiplier})",
            version="1.0.0",
            description=f"SuperTrend (period={period}, multiplier={self._multiplier})",
            min_period=period,
            default_period=period,
            params=("period", "multiplier"),
        )
        self._atr_values.clear()
        self._upper_band = None
        self._lower_band = None
        self._trend_up = True
        self._prev_close = None

    def _basic_atr(self, bar: Bar) -> float:
        hl = bar.high - bar.low
        if self._prev_close is not None:
            return max(hl, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        return hl

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        self._prev_close = bars[0].close
        for bar in bars[1:]:
            tr = self._basic_atr(bar)
            self._atr_values.append(tr)
            self._prev_close = bar.close
        self._prev_close = bars[-1].close if bars else None

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        tr = self._basic_atr(bar)
        self._atr_values.append(tr)
        self._prev_close = bar.close

        atr = (
            sum(self._atr_values[-period:]) / min(period, len(self._atr_values))
            if self._atr_values
            else 0.0
        )
        hl2 = (bar.high + bar.low) / 2.0

        upper = hl2 + self._multiplier * atr
        lower = hl2 - self._multiplier * atr

        if self._upper_band is None:
            self._upper_band = upper
            self._lower_band = lower
        else:
            if bar.close <= self._upper_band:
                self._upper_band = upper

            if bar.close >= self._lower_band:
                self._lower_band = lower

        if bar.close > self._upper_band if self._upper_band is not None else False:
            self._trend_up = True
        elif bar.close < self._lower_band if self._lower_band is not None else False:
            self._trend_up = False

        band = self._lower_band if self._trend_up else self._upper_band

        return self._create_result(
            bar,
            value=band,
            values={
                "upper": self._upper_band,
                "lower": self._lower_band,
                "trend_up": float(self._trend_up),
            },
            metadata={"trend_up": self._trend_up},
        )
