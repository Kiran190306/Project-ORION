"""Ichimoku Cloud indicator.

Multiple-component indicator providing support/resistance, trend direction,
and momentum signals.
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


class IchimokuCloud(BaseIndicator):
    """Ichimoku Cloud (Ichimoku Kinko Hyo).

    Components:
    - Tenkan-sen (Conversion Line): (highest high + lowest low) / 2 over 9 periods
    - Kijun-sen (Base Line): (highest high + lowest low) / 2 over 26 periods
    - Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted forward 26
    - Senkou Span B (Leading Span B): (highest high + lowest low) / 2 over 52 periods, shifted forward 26
    - Chikou Span (Lagging Span): Current close, shifted back 26
    """

    def __init__(self) -> None:
        metadata = IndicatorMetadata(
            name="ichimoku",
            indicator_type=IndicatorType.TREND,
            display_name="Ichimoku Cloud",
            version="1.0.0",
            description="Ichimoku Kinko Hyo - comprehensive trend indicator",
            min_period=52,
            default_period=52,
            params=(),
        )
        super().__init__(metadata)

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        pass

    async def _on_warmup(self, bars: list[Bar]) -> None:
        pass

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        window9 = self.get_rolling_window(9)
        window26 = self.get_rolling_window(26)
        window52 = self.get_rolling_window(52)

        tenkan = self._calc_line(window9, 9)
        kijun = self._calc_line(window26, 26)
        span_a = (tenkan + kijun) / 2.0 if tenkan is not None and kijun is not None else None
        span_b = self._calc_line(window52, 52)

        return self._create_result(
            bar,
            value=tenkan,
            values={
                "kijun": kijun,
                "span_a": span_a,
                "span_b": span_b,
                "chikou": bar.close,
            },
        )

    def _calc_line(self, window: list, period: int) -> float | None:
        if len(window) < period:
            return None
        highest = max(b.high for b in window)
        lowest = min(b.low for b in window)
        return (highest + lowest) / 2.0
