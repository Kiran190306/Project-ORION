"""Money Flow Index (MFI) indicator.

Volume-weighted RSI equivalent with O(1) incremental update.
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


class MoneyFlowIndex(BaseIndicator):
    """Money Flow Index.

    MFI = 100 - (100 / (1 + Money Flow Ratio))
    where:
    - Typical Price = (high + low + close) / 3
    - Raw Money Flow = Typical Price * Volume
    - Money Flow Ratio = Positive Money Flow / Negative Money Flow
    """

    def __init__(self, period: int = 14) -> None:
        metadata = IndicatorMetadata(
            name="mfi",
            indicator_type=IndicatorType.VOLUME,
            display_name="Money Flow Index",
            version="1.0.0",
            description="Money Flow Index - volume-weighted RSI",
            min_period=period + 1,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)
        self._pos_flow: float = 0.0
        self._neg_flow: float = 0.0
        self._prev_tp: float | None = None

    def _typical_price(self, bar: Bar) -> float:
        return (bar.high + bar.low + bar.close) / 3.0

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="mfi",
            indicator_type=IndicatorType.VOLUME,
            display_name=f"MFI ({period})",
            version="1.0.0",
            description=f"Money Flow Index (period={period})",
            min_period=period + 1,
            default_period=period,
            params=("period",),
        )
        self._pos_flow = 0.0
        self._neg_flow = 0.0
        self._prev_tp = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        self._prev_tp = self._typical_price(bars[0])
        for bar in bars[1:]:
            tp = self._typical_price(bar)
            rmf = tp * bar.volume
            if tp > self._prev_tp:
                self._pos_flow += rmf
            else:
                self._neg_flow += rmf
            self._prev_tp = tp

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        tp = self._typical_price(bar)
        rmf = tp * bar.volume

        if self._prev_tp is not None and tp > self._prev_tp:
            self._pos_flow += rmf
        elif self._prev_tp is not None:
            self._neg_flow += rmf

        self._prev_tp = tp

        mfr = self._safe_div(self._pos_flow, self._neg_flow, default=0.0)
        mfi = 100.0 - (100.0 / (1.0 + mfr)) if mfr > 0 else 50.0

        return self._create_result(bar, value=mfi)
