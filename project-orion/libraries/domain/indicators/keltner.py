"""Keltner Channels indicator.

ATR-based volatility bands around an EMA.
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


class KeltnerChannels(BaseIndicator):
    """Keltner Channels.

    Middle Line: EMA (period)
    Upper Channel: EMA + (ATR * multiplier)
    Lower Channel: EMA - (ATR * multiplier)
    """

    def __init__(self, period: int = 20, multiplier: float = 2.0) -> None:
        metadata = IndicatorMetadata(
            name="keltner",
            indicator_type=IndicatorType.VOLATILITY,
            display_name="Keltner Channels",
            version="1.0.0",
            description="Keltner Channels - volatility bands around EMA",
            min_period=period,
            default_period=period,
            params=("period", "multiplier"),
        )
        super().__init__(metadata)
        self._multiplier = multiplier
        self._ema_val: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        period = config.period
        self._multiplier = float(config.get("multiplier", 2.0))
        self._metadata = IndicatorMetadata(
            name="keltner",
            indicator_type=IndicatorType.VOLATILITY,
            display_name=f"Keltner ({period},{self._multiplier})",
            version="1.0.0",
            description=f"Keltner Channels (period={period}, mult={self._multiplier})",
            min_period=period,
            default_period=period,
            params=("period", "multiplier"),
        )
        self._ema_val = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        closes = [b.close for b in bars]
        period = self.required_period()
        if len(closes) >= period:
            self._ema_val = sum(closes[:period]) / period
            for close in closes[period:]:
                self._ema_val = self._ema(self._ema_val, close, period)
        else:
            self._ema_val = sum(closes) / len(closes)

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        period = self.required_period()
        if self._ema_val is None:
            self._ema_val = bar.close
        else:
            self._ema_val = self._ema(self._ema_val, bar.close, period)

        window = self.get_rolling_window(period)
        if len(window) >= period:
            tr_values = []
            prev_close = window[0].close
            for b in window[1:]:
                tr = b.high - b.low
                if prev_close is not None:
                    tr = max(tr, abs(b.high - prev_close), abs(b.low - prev_close))
                tr_values.append(tr)
                prev_close = b.close
            atr = sum(tr_values) / len(tr_values) if tr_values else 0.0
        else:
            atr = bar.high - bar.low

        upper = self._ema_val + (atr * self._multiplier)
        lower = self._ema_val - (atr * self._multiplier)

        return self._create_result(
            bar,
            value=self._ema_val,
            values={"upper": upper, "lower": lower},
        )
