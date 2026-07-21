"""Bollinger Bands indicator.

O(1) incremental update using SMA and standard deviation.
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


class BollingerBands(BaseIndicator):
    """Bollinger Bands.

    Middle Band: SMA (period)
    Upper Band: SMA + (stddev * num_std)
    Lower Band: SMA - (stddev * num_std)

    Uses rolling window for O(1) incremental SMA and StdDev updates.
    """

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        metadata = IndicatorMetadata(
            name="bollinger",
            indicator_type=IndicatorType.VOLATILITY,
            display_name="Bollinger Bands",
            version="1.0.0",
            description="Bollinger Bands - volatility bands around SMA",
            min_period=period,
            default_period=period,
            params=("period", "num_std"),
        )
        super().__init__(metadata)
        self._num_std = num_std

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._num_std = float(config.get("num_std", 2.0))
        self._metadata = IndicatorMetadata(
            name="bollinger",
            indicator_type=IndicatorType.VOLATILITY,
            display_name=f"Bollinger ({period},{self._num_std})",
            version="1.0.0",
            description=f"Bollinger Bands (period={period}, num_std={self._num_std})",
            min_period=period,
            default_period=period,
            params=("period", "num_std"),
        )

    async def _on_warmup(self, bars: list[Bar]) -> None:
        pass

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        window = self.get_rolling_window(period)

        if len(window) < period:
            return self._create_result(bar, value=bar.close)

        closes = [b.close for b in window]
        sma = sum(closes) / period
        stddev = self._stddev(closes, period)

        upper = sma + (stddev * self._num_std)
        lower = sma - (stddev * self._num_std)
        bandwidth = self._safe_div((upper - lower), sma)
        percent_b = self._safe_div((bar.close - lower), (upper - lower))

        return self._create_result(
            bar,
            value=sma,
            values={
                "upper": upper,
                "lower": lower,
                "bandwidth": bandwidth,
                "percent_b": percent_b,
            },
        )
