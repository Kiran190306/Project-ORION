"""On-Balance Volume (OBV) indicator.

O(1) incremental update using cumulative volume flow.
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


class OnBalanceVolume(BaseIndicator):
    """On-Balance Volume.

    OBV = cumulative volume where:
    - If close > prev_close: OBV += volume
    - If close < prev_close: OBV -= volume
    - If close == prev_close: OBV unchanged
    """

    def __init__(self, period: int = 0) -> None:
        metadata = IndicatorMetadata(
            name="obv",
            indicator_type=IndicatorType.VOLUME,
            display_name="On-Balance Volume",
            version="1.0.0",
            description="On-Balance Volume - momentum indicator using volume flow",
            min_period=1,
            default_period=1,
            params=(),
        )
        super().__init__(metadata)
        self._obv: float = 0.0
        self._prev_close: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._obv = 0.0
        self._prev_close = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        self._obv = 0.0
        self._prev_close = None
        for bar in bars:
            self._update_obv(bar)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        self._update_obv(bar)
        return self._create_result(bar, value=self._obv)

    def _update_obv(self, bar: Bar) -> None:
        if self._prev_close is not None:
            if bar.close > self._prev_close:
                self._obv += bar.volume
            elif bar.close < self._prev_close:
                self._obv -= bar.volume
        self._prev_close = bar.close

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["obv"] = self._obv
        data["state"]["prev_close"] = self._prev_close
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "OnBalanceVolume":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._obv = state.get("obv", 0.0)
        instance._prev_close = state.get("prev_close")
        return instance
