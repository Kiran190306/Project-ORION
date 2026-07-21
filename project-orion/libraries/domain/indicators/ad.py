"""Accumulation/Distribution (A/D) indicator.

O(1) incremental update using volume-weighted flow.
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


class AccumulationDistribution(BaseIndicator):
    """Accumulation/Distribution Line.

    A/D = cumulative(Money Flow Volume)
    where Money Flow Volume = MFM * Volume
    and MFM = ((close - low) - (high - close)) / (high - low)
    """

    def __init__(self, period: int = 0) -> None:
        metadata = IndicatorMetadata(
            name="ad",
            indicator_type=IndicatorType.VOLUME,
            display_name="Accumulation/Distribution",
            version="1.0.0",
            description="Accumulation/Distribution - volume-weighted cumulative indicator",
            min_period=1,
            default_period=1,
            params=(),
        )
        super().__init__(metadata)
        self._ad_line: float = 0.0

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._ad_line = 0.0

    async def _on_warmup(self, bars: list[Bar]) -> None:
        self._ad_line = 0.0
        for bar in bars:
            self._update_ad(bar)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        self._update_ad(bar)
        return self._create_result(bar, value=self._ad_line)

    def _update_ad(self, bar: Bar) -> None:
        high_low = bar.high - bar.low
        if high_low > 0:
            mfm = ((bar.close - bar.low) - (bar.high - bar.close)) / high_low
            self._ad_line += mfm * bar.volume

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["ad_line"] = self._ad_line
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "AccumulationDistribution":
        instance = await super().deserialize(data)
        instance._ad_line = data.get("state", {}).get("ad_line", 0.0)
        return instance
