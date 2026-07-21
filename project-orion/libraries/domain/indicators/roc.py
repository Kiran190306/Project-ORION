"""Rate of Change (ROC) indicator.

Measures percentage price change over a period.
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


class ROC(BaseIndicator):
    """Rate of Change.

    ROC = ((close - close_n_periods_ago) / close_n_periods_ago) * 100
    """

    def __init__(self, period: int = 12) -> None:
        metadata = IndicatorMetadata(
            name="roc",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="Rate of Change",
            version="1.0.0",
            description="Rate of Change - momentum indicator measuring percentage price change",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="roc",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"ROC ({period})",
            version="1.0.0",
            description=f"Rate of Change (period={period})",
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
        roc = self._safe_div((bar.close - n_periods_ago), n_periods_ago) * 100
        return self._create_result(bar, value=roc)
