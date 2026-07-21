"""Commodity Channel Index (CCI) indicator.

Measures deviation of typical price from its moving average.
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


class CCI(BaseIndicator):
    """Commodity Channel Index.

    CCI = (Typical Price - SMA of TP) / (0.015 * Mean Deviation)
    Values above +100 suggest overbought. Values below -100 suggest oversold.
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="cci",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="Commodity Channel Index",
            version="1.0.0",
            description="Commodity Channel Index - identifies cyclical trends",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    def _typical_price(self, bar: Bar) -> float:
        return (bar.high + bar.low + bar.close) / 3.0

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="cci",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"CCI ({period})",
            version="1.0.0",
            description=f"Commodity Channel Index (period={period})",
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
            return self._create_result(bar, value=0.0)

        typical_prices = [self._typical_price(b) for b in window]
        tp = self._typical_price(bar)
        sma_tp = sum(typical_prices) / period

        mean_deviation = sum(abs(p - sma_tp) for p in typical_prices) / period
        cci = self._safe_div((tp - sma_tp), (0.015 * mean_deviation))

        return self._create_result(bar, value=cci)
