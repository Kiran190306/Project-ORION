"""Pivot Points indicator.

Calculates support/resistance levels based on high/low/close.
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


class PivotPoints(BaseIndicator):
    """Pivot Points.

    PP = (high + low + close) / 3
    R1 = 2 * PP - low
    R2 = PP + (high - low)
    S1 = 2 * PP - high
    S2 = PP - (high - low)
    """

    def __init__(self, period: int = 1) -> None:
        metadata = IndicatorMetadata(
            name="pivot",
            indicator_type=IndicatorType.BREAKOUT,
            display_name="Pivot Points",
            version="1.0.0",
            description="Pivot Points - support and resistance levels",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        pass

    async def _on_warmup(self, bars: list[Bar]) -> None:
        pass

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        window = self.get_rolling_window(1)
        if not window:
            return self._create_result(
                bar,
                value=bar.close,
                values={"pp": bar.close, "r1": bar.close, "s1": bar.close},
            )

        prev = window[-1]
        pp = (prev.high + prev.low + prev.close) / 3.0
        r1 = 2 * pp - prev.low
        r2 = pp + (prev.high - prev.low)
        s1 = 2 * pp - prev.high
        s2 = pp - (prev.high - prev.low)

        return self._create_result(
            bar,
            value=pp,
            values={
                "r1": r1,
                "r2": r2,
                "s1": s1,
                "s2": s2,
            },
        )
