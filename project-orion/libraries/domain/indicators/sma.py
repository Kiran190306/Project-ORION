"""Simple Moving Average (SMA) indicator.

O(1) incremental update using sliding window sum.
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


class SMA(BaseIndicator):
    """Simple Moving Average.

    Maintains a rolling sum for O(1) incremental updates.
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="sma",
            indicator_type=IndicatorType.TREND,
            display_name="Simple Moving Average",
            version="1.0.0",
            description="Simple Moving Average - arithmetic mean of recent prices",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._rolling_sum: float = 0.0
        self._rolling_closes: list[float] = []

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="sma",
            indicator_type=IndicatorType.TREND,
            display_name=f"SMA ({period})",
            version="1.0.0",
            description=f"Simple Moving Average (period={period})",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        self._rolling_sum = 0.0
        self._rolling_closes.clear()

    async def _on_warmup(self, bars: list[Bar]) -> None:
        closes = [b.close for b in bars]
        period = self.required_period()
        self._rolling_closes = closes[-period:] if len(closes) >= period else closes
        self._rolling_sum = sum(self._rolling_closes)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        self._rolling_closes.append(bar.close)
        self._rolling_sum += bar.close

        if len(self._rolling_closes) > period:
            removed = self._rolling_closes.pop(0)
            self._rolling_sum -= removed

        sma_value = self._rolling_sum / min(period, len(self._rolling_closes))
        return self._create_result(bar, value=sma_value)

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["rolling_sum"] = self._rolling_sum
        data["state"]["rolling_closes"] = list(self._rolling_closes)
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "SMA":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._rolling_sum = state.get("rolling_sum", 0.0)
        instance._rolling_closes = list(state.get("rolling_closes", []))
        return instance
