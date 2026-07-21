"""Exponential Moving Average (EMA) indicator.

O(1) incremental update using the standard EMA formula.
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


class EMA(BaseIndicator):
    """Exponential Moving Average.

    Uses the standard formula: EMA = (close - prev_ema) * multiplier + prev_ema
    where multiplier = 2 / (period + 1)
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="ema",
            indicator_type=IndicatorType.TREND,
            display_name="Exponential Moving Average",
            version="1.0.0",
            description="Exponential Moving Average - places more weight on recent prices",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._current_ema: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="ema",
            indicator_type=IndicatorType.TREND,
            display_name=f"EMA ({period})",
            version="1.0.0",
            description=f"Exponential Moving Average (period={period})",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        self._current_ema = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        closes = [b.close for b in bars]
        period = self.required_period()
        if len(closes) >= period:
            self._current_ema = sum(closes[:period]) / period
            for close in closes[period:]:
                self._current_ema = self._ema(self._current_ema, close, period)
        else:
            self._current_ema = sum(closes) / len(closes)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        if self._current_ema is None:
            self._current_ema = bar.close
        else:
            self._current_ema = self._ema(self._current_ema, bar.close, period)

        return self._create_result(bar, value=self._current_ema)

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["current_ema"] = self._current_ema
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "EMA":
        instance = await super().deserialize(data)
        instance._current_ema = data.get("state", {}).get("current_ema")
        return instance
