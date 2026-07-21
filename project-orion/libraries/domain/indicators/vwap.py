"""Volume Weighted Average Price (VWAP) indicator.

O(1) incremental update using cumulative sums.
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


class VWAP(BaseIndicator):
    """Volume Weighted Average Price.

    VWAP = cumulative(price * volume) / cumulative(volume)
    Supports O(1) incremental updates and daily resets.
    """

    def __init__(self, period: int = 0) -> None:
        metadata = IndicatorMetadata(
            name="vwap",
            indicator_type=IndicatorType.VOLUME,
            display_name="Volume Weighted Average Price",
            version="1.0.0",
            description="Volume Weighted Average Price - average price weighted by volume",
            min_period=1,
            default_period=1,
            params=("period",),
        )
        super().__init__(metadata)
        self._cumulative_pv: float = 0.0
        self._cumulative_volume: float = 0.0

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._cumulative_pv = 0.0
        self._cumulative_volume = 0.0

    async def _on_warmup(self, bars: list[Bar]) -> None:
        self._cumulative_pv = sum(b.close * b.volume for b in bars)
        self._cumulative_volume = sum(b.volume for b in bars)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        self._cumulative_pv += bar.close * bar.volume
        self._cumulative_volume += bar.volume

        vwap = self._safe_div(self._cumulative_pv, self._cumulative_volume)
        return self._create_result(bar, value=vwap)

    async def reset_daily(self) -> None:
        """Reset VWAP calculation for a new trading day."""
        self._cumulative_pv = 0.0
        self._cumulative_volume = 0.0
        self._warmed_up = False

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["cumulative_pv"] = self._cumulative_pv
        data["state"]["cumulative_volume"] = self._cumulative_volume
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "VWAP":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._cumulative_pv = state.get("cumulative_pv", 0.0)
        instance._cumulative_volume = state.get("cumulative_volume", 0.0)
        return instance
