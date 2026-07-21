"""Hull Moving Average (HMA) indicator.

Uses weighted moving averages of weighted moving averages for
reduced lag response.
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


class HMA(BaseIndicator):
    """Hull Moving Average.

    Provides a smoother moving average with reduced lag compared to
    traditional moving averages.
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="hma",
            indicator_type=IndicatorType.TREND,
            display_name="Hull Moving Average",
            version="1.0.0",
            description="Hull Moving Average - reduced lag moving average",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="hma",
            indicator_type=IndicatorType.TREND,
            display_name=f"HMA ({period})",
            version="1.0.0",
            description=f"Hull Moving Average (period={period})",
            min_period=period,
            default_period=period,
            params=("period",),
        )

    async def _on_warmup(self, bars: list[Bar]) -> None:
        pass

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        window = self.get_rolling_window(period * 2)
        if len(window) < period:
            return self._create_result(bar, value=bar.close)

        closes = [b.close for b in window]

        half_period = max(2, period // 2)
        wma_half = self._wma(closes[-half_period:], half_period)
        wma_full = self._wma(closes[-period:], period)

        # Raw HMA = 2 * WMA(half) - WMA(full)
        raw_hma = 2 * wma_half - wma_full

        return self._create_result(bar, value=raw_hma)
