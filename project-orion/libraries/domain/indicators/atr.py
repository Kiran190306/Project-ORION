"""Average True Range (ATR) indicator.

O(1) incremental update using Wilder's smoothing.
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


class ATR(BaseIndicator):
    """Average True Range.

    Measures market volatility by decomposing the entire range of a
    price movement. Uses Wilder's smoothed ATR for incremental updates.
    """

    def __init__(self, period: int = 14) -> None:
        metadata = IndicatorMetadata(
            name="atr",
            indicator_type=IndicatorType.VOLATILITY,
            display_name="Average True Range",
            version="1.0.0",
            description="Average True Range - measures market volatility",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._current_atr: float | None = None
        self._prev_close: float | None = None
        self._tr_values: list[float] = []

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="atr",
            indicator_type=IndicatorType.VOLATILITY,
            display_name=f"ATR ({period})",
            version="1.0.0",
            description=f"Average True Range (period={period})",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        self._current_atr = None
        self._prev_close = None
        self._tr_values.clear()

    def _true_range(self, bar: Bar, prev_close: float | None) -> float:
        """Calculate True Range."""
        high_low = bar.high - bar.low
        if prev_close is not None:
            high_close = abs(bar.high - prev_close)
            low_close = abs(bar.low - prev_close)
            return max(high_low, high_close, low_close)
        return high_low

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        self._tr_values.clear()

        for i, bar in enumerate(bars):
            prev_close = bars[i - 1].close if i > 0 else None
            tr = self._true_range(bar, prev_close)
            self._tr_values.append(tr)

        period = self.required_period()
        if len(self._tr_values) >= period:
            self._current_atr = sum(self._tr_values[:period]) / period
            for tr in self._tr_values[period:]:
                self._current_atr = (self._current_atr * (period - 1) + tr) / period

        self._prev_close = bars[-1].close if bars else None

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        tr = self._true_range(bar, self._prev_close)
        self._prev_close = bar.close

        if self._current_atr is None:
            self._current_atr = tr
        else:
            self._current_atr = (self._current_atr * (period - 1) + tr) / period

        return self._create_result(
            bar,
            value=self._current_atr,
            values={"tr": tr},
        )

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["current_atr"] = self._current_atr
        data["state"]["prev_close"] = self._prev_close
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "ATR":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._current_atr = state.get("current_atr")
        instance._prev_close = state.get("prev_close")
        return instance
