"""Momentum indicator.

Simple price change over a period.
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


class Momentum(BaseIndicator):
    """Momentum.

    Momentum = close - close_n_periods_ago
    """

    def __init__(self, period: int = 12) -> None:
        metadata = IndicatorMetadata(
            name="momentum",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="Momentum",
            version="1.0.0",
            description="Momentum - simple price difference over period",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="momentum",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"Momentum ({period})",
            version="1.0.0",
            description=f"Momentum (period={period})",
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

        n_periods_ago = window[0].close if window else bar.close
        momentum = bar.close - n_periods_ago
        return self._create_result(bar, value=momentum)
