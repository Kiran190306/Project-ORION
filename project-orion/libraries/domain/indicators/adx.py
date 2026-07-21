"""Average Directional Index (ADX) indicator.

O(1) incremental update using Wilder's smoothing. Includes DI+ and DI- lines.
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


class ADX(BaseIndicator):
    """Average Directional Index.

    Measures trend strength (non-directional).
    Includes DI+ and DI- for directional analysis.
    ADX > 25 suggests strong trend. ADX < 20 suggests weak/choppy market.
    """

    def __init__(self, period: int = 14) -> None:
        metadata = IndicatorMetadata(
            name="adx",
            indicator_type=IndicatorType.MARKET_STRENGTH,
            display_name="Average Directional Index",
            version="1.0.0",
            description="Average Directional Index - measures trend strength with DI+ and DI-",
            min_period=period * 2,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._period = period
        self._tr_values: list[float] = []
        self._up_values: list[float] = []
        self._down_values: list[float] = []
        self._smoothed_tr: float = 0.0
        self._smoothed_up: float = 0.0
        self._smoothed_down: float = 0.0
        self._adx: float | None = None
        self._prev_close: float | None = None
        self._prev_high: float | None = None
        self._prev_low: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._period = config.period
        self._metadata = IndicatorMetadata(
            name="adx",
            indicator_type=IndicatorType.MARKET_STRENGTH,
            display_name=f"ADX ({self._period})",
            version="1.0.0",
            description=f"Average Directional Index (period={self._period})",
            min_period=self._period * 2,
            default_period=self._period,
            params=("period",),
        )
        self._tr_values.clear()
        self._up_values.clear()
        self._down_values.clear()
        self._smoothed_tr = 0.0
        self._smoothed_up = 0.0
        self._smoothed_down = 0.0
        self._adx = None
        self._prev_close = None
        self._prev_high = None
        self._prev_low = None

    def _directional_movement(self, bar: Bar) -> tuple[float, float]:
        """Calculate directional movement up and down."""
        if self._prev_high is None or self._prev_low is None:
            return 0.0, 0.0

        up_move = bar.high - self._prev_high
        down_move = self._prev_low - bar.low

        up = max(up_move, 0.0) if up_move > down_move else 0.0
        down = max(down_move, 0.0) if down_move > up_move else 0.0
        return up, down

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if len(bars) < 2:
            return

        for i, bar in enumerate(bars):
            if i == 0:
                self._prev_high = bar.high
                self._prev_low = bar.low
                self._prev_close = bar.close
                continue

            tr = bar.high - bar.low
            up, down = self._directional_movement(bar)
            self._tr_values.append(tr)
            self._up_values.append(up)
            self._down_values.append(down)

            self._prev_high = bar.high
            self._prev_low = bar.low
            self._prev_close = bar.close

        if len(self._tr_values) >= self._period:
            self._smoothed_tr = sum(self._tr_values[: self._period]) / self._period
            self._smoothed_up = sum(self._up_values[: self._period]) / self._period
            self._smoothed_down = sum(self._down_values[: self._period]) / self._period

            for i in range(self._period, len(self._tr_values)):
                self._smoothed_tr = (
                    self._smoothed_tr * (self._period - 1) + self._tr_values[i]
                ) / self._period
                self._smoothed_up = (
                    self._smoothed_up * (self._period - 1) + self._up_values[i]
                ) / self._period
                self._smoothed_down = (
                    self._smoothed_down * (self._period - 1) + self._down_values[i]
                ) / self._period

                di_plus = self._safe_div(self._smoothed_up, self._smoothed_tr) * 100
                di_minus = self._safe_div(self._smoothed_down, self._smoothed_tr) * 100

                if self._adx is None:
                    self._adx = (
                        abs(di_plus - di_minus) / (di_plus + di_minus) * 100
                        if (di_plus + di_minus) > 0
                        else 0.0
                    )
                else:
                    dx = (
                        abs(di_plus - di_minus) / (di_plus + di_minus) * 100
                        if (di_plus + di_minus) > 0
                        else 0.0
                    )
                    self._adx = (self._adx * (self._period - 1) + dx) / self._period

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        tr = bar.high - bar.low
        up, down = self._directional_movement(bar)

        if self._smoothed_tr == 0.0:
            self._smoothed_tr = tr
            self._smoothed_up = up
            self._smoothed_down = down
        else:
            self._smoothed_tr = (self._smoothed_tr * (self._period - 1) + tr) / self._period
            self._smoothed_up = (self._smoothed_up * (self._period - 1) + up) / self._period
            self._smoothed_down = (self._smoothed_down * (self._period - 1) + down) / self._period

        self._prev_high = bar.high
        self._prev_low = bar.low
        self._prev_close = bar.close

        di_plus = self._safe_div(self._smoothed_up, self._smoothed_tr) * 100
        di_minus = self._safe_div(self._smoothed_down, self._smoothed_tr) * 100
        dx_sum = di_plus + di_minus

        if self._adx is None:
            self._adx = self._safe_div(abs(di_plus - di_minus), dx_sum) * 100
        else:
            dx = self._safe_div(abs(di_plus - di_minus), dx_sum) * 100
            self._adx = (self._adx * (self._period - 1) + dx) / self._period

        return self._create_result(
            bar,
            value=self._adx,
            values={
                "di_plus": di_plus,
                "di_minus": di_minus,
            },
        )

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        state = data["state"]
        state["smoothed_tr"] = self._smoothed_tr
        state["smoothed_up"] = self._smoothed_up
        state["smoothed_down"] = self._smoothed_down
        state["adx"] = self._adx
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "ADX":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._smoothed_tr = state.get("smoothed_tr", 0.0)
        instance._smoothed_up = state.get("smoothed_up", 0.0)
        instance._smoothed_down = state.get("smoothed_down", 0.0)
        instance._adx = state.get("adx")
        return instance
