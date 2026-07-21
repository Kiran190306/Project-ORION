"""Weighted Moving Average (WMA) indicator.

O(n) update where n = period. Linear weighting puts more weight on recent prices.
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


class WMA(BaseIndicator):
    """Weighted Moving Average.

    Assigns linearly increasing weights with the most recent price
    getting the highest weight.
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="wma",
            indicator_type=IndicatorType.TREND,
            display_name="Weighted Moving Average",
            version="1.0.0",
            description="Weighted Moving Average - linear weighting of recent prices",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="wma",
            indicator_type=IndicatorType.TREND,
            display_name=f"WMA ({period})",
            version="1.0.0",
            description=f"Weighted Moving Average (period={period})",
            min_period=period,
            default_period=period,
            params=("period",),
        )

    async def _on_warmup(self, bars: list[Bar]) -> None:
        pass

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        window = self.get_rolling_window(period)
        if len(window) < period:
            wma_value = sum(b.close for b in window) / len(window)
        else:
            wma_value = self._wma([b.close for b in window], period)

        return self._create_result(bar, value=wma_value)
