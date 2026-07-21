"""Donchian Channel indicator.

Tracks the highest high and lowest low over a lookback period.
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


class DonchianChannel(BaseIndicator):
    """Donchian Channel.

    Upper Channel = Highest high over period
    Lower Channel = Lowest low over period
    Middle Channel = (Upper + Lower) / 2
    """

    def __init__(self, period: int = 20) -> None:
        metadata = IndicatorMetadata(
            name="donchian",
            indicator_type=IndicatorType.BREAKOUT,
            display_name="Donchian Channel",
            version="1.0.0",
            description="Donchian Channel - highest high and lowest low channel",
            min_period=period,
            default_period=period,
            params=("period",),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._metadata = IndicatorMetadata(
            name="donchian",
            indicator_type=IndicatorType.BREAKOUT,
            display_name=f"Donchian ({period})",
            version="1.0.0",
            description=f"Donchian Channel (period={period})",
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
            return self._create_result(
                bar,
                value=bar.close,
                values={"upper": bar.close, "lower": bar.close},
            )

        upper = max(b.high for b in window)
        lower = min(b.low for b in window)
        middle = (upper + lower) / 2.0

        return self._create_result(
            bar,
            value=middle,
            values={"upper": upper, "lower": lower},
        )
