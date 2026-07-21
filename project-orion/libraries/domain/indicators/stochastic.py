"""Stochastic Oscillator indicator.

O(1) incremental update using rolling min/max tracking.
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


class Stochastic(BaseIndicator):
    """Stochastic Oscillator.

    %K = (close - lowest_low) / (highest_high - lowest_low) * 100
    %D = SMA(%K, signal_period)

    Uses rolling window for high/low tracking.
    """

    def __init__(self, k_period: int = 14, d_period: int = 3) -> None:
        metadata = IndicatorMetadata(
            name="stochastic",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="Stochastic Oscillator",
            version="1.0.0",
            description="Stochastic Oscillator - compares close to price range",
            min_period=k_period + d_period,
            default_period=14,
            params=("k_period", "d_period"),
        )
        super().__init__(metadata)
        self._k_period = k_period
        self._d_period = d_period
        self._k_values: list[float] = []

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._k_period = int(config.get("k_period", 14))
        self._d_period = int(config.get("d_period", 3))
        self._metadata = IndicatorMetadata(
            name="stochastic",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"Stochastic ({self._k_period},{self._d_period})",
            version="1.0.0",
            description=f"Stochastic Oscillator (K={self._k_period}, D={self._d_period})",
            min_period=self._k_period + self._d_period,
            default_period=self._k_period,
            params=("k_period", "d_period"),
        )
        self._k_values.clear()

    async def _on_warmup(self, bars: list[Bar]) -> None:
        self._k_values.clear()

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        window = self.get_rolling_window(self._k_period)

        if len(window) < self._k_period:
            return self._create_result(bar, value=50.0)

        highest_high = max(b.high for b in window)
        lowest_low = min(b.low for b in window)
        range_diff = highest_high - lowest_low

        k = self._safe_div((bar.close - lowest_low), range_diff) * 100
        self._k_values.append(k)

        d = (
            self._sma(self._k_values, self._d_period)
            if len(self._k_values) >= self._d_period
            else k
        )

        return self._create_result(
            bar,
            value=k,
            values={"d": d},
        )
