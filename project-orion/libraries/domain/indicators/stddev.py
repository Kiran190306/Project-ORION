"""Standard Deviation indicator.

Measures price dispersion from the mean.
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


class StandardDeviation(BaseIndicator):
    """Standard Deviation.

    Measures price volatility by computing the standard deviation
    of closing prices over a rolling window.
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="stddev",
            indicator_type=IndicatorType.VOLATILITY,
            display_name="Standard Deviation",
            version="1.0.0",
            description="Standard Deviation - measures price dispersion",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="stddev",
            indicator_type=IndicatorType.VOLATILITY,
            display_name=f"StdDev ({period})",
            version="1.0.0",
            description=f"Standard Deviation (period={period})",
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

        closes = [b.close for b in window]
        stddev = self._stddev(closes, period)
        return self._create_result(bar, value=stddev)
