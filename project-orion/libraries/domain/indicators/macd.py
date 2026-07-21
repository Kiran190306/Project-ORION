"""MACD (Moving Average Convergence Divergence) indicator.

O(1) incremental update using EMA for all three lines.
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


class MACD(BaseIndicator):
    """MACD Indicator.

    MACD Line: 12-period EMA - 26-period EMA
    Signal Line: 9-period EMA of MACD Line
    Histogram: MACD Line - Signal Line

    All EMAs support O(1) incremental updates.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        metadata = IndicatorMetadata(
            name="macd",
            indicator_type=IndicatorType.MOMENTUM,
            display_name="MACD",
            version="1.0.0",
            description="Moving Average Convergence Divergence - trend following momentum indicator",
            min_period=slow_period + signal_period,
            default_period=26,
            params=("fast_period", "slow_period", "signal_period"),
        )
        super().__init__(metadata)
        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
        self._fast_ema: float | None = None
        self._slow_ema: float | None = None
        self._signal_ema: float | None = None
        self._macd_line: float | None = None

    async def _on_initialize(self, config: IndicatorConfig) -> None:
        self._fast_period = int(config.get("fast_period", 12))
        self._slow_period = int(config.get("slow_period", 26))
        self._signal_period = int(config.get("signal_period", 9))
        self._metadata = IndicatorMetadata(
            name="macd",
            indicator_type=IndicatorType.MOMENTUM,
            display_name=f"MACD ({self._fast_period},{self._slow_period},{self._signal_period})",
            version="1.0.0",
            description=f"MACD (fast={self._fast_period}, slow={self._slow_period}, signal={self._signal_period})",
            min_period=self._slow_period + self._signal_period,
            default_period=self._slow_period,
            params=("fast_period", "slow_period", "signal_period"),
        )
        self._fast_ema = None
        self._slow_ema = None
        self._signal_ema = None
        self._macd_line = None

    async def _on_warmup(self, bars: list[Bar]) -> None:
        if not bars:
            return
        closes = [b.close for b in bars]

        if len(closes) >= self._slow_period:
            self._fast_ema = sum(closes[: self._fast_period]) / self._fast_period
            self._slow_ema = sum(closes[: self._slow_period]) / self._slow_period

            for close in closes[self._fast_period :]:
                self._fast_ema = self._ema(self._fast_ema, close, self._fast_period)

            for close in closes[self._slow_period :]:
                self._slow_ema = self._ema(self._slow_ema, close, self._slow_period)

            self._macd_line = self._fast_ema - self._slow_ema
            self._signal_ema = self._macd_line
        elif closes:
            avg = sum(closes) / len(closes)
            self._fast_ema = avg
            self._slow_ema = avg
            self._macd_line = 0.0
            self._signal_ema = 0.0

    async def _on_update(self, bar: Bar) -> IndicatorResult:
        if self._fast_ema is None:
            self._fast_ema = bar.close
            self._slow_ema = bar.close
        else:
            self._fast_ema = self._ema(self._fast_ema, bar.close, self._fast_period)
            self._slow_ema = self._ema(self._slow_ema, bar.close, self._slow_period)

        new_macd = self._fast_ema - self._slow_ema
        if self._signal_ema is None:
            self._signal_ema = new_macd
        else:
            self._signal_ema = self._ema(self._signal_ema, new_macd, self._signal_period)

        self._macd_line = new_macd
        histogram = self._macd_line - self._signal_ema

        return self._create_result(
            bar,
            value=self._macd_line,
            values={
                "signal": self._signal_ema,
                "histogram": histogram,
                "fast_ema": self._fast_ema,
                "slow_ema": self._slow_ema,
            },
        )

    async def serialize(self) -> dict[str, Any]:
        data = await super().serialize()
        data["state"]["fast_ema"] = self._fast_ema
        data["state"]["slow_ema"] = self._slow_ema
        data["state"]["signal_ema"] = self._signal_ema
        data["state"]["macd_line"] = self._macd_line
        data["config"]["fast_period"] = self._fast_period
        data["config"]["slow_period"] = self._slow_period
        data["config"]["signal_period"] = self._signal_period
        return data

    @classmethod
    async def deserialize(cls, data: dict[str, Any]) -> "MACD":
        instance = await super().deserialize(data)
        state = data.get("state", {})
        instance._fast_ema = state.get("fast_ema")
        instance._slow_ema = state.get("slow_ema")
        instance._signal_ema = state.get("signal_ema")
        instance._macd_line = state.get("macd_line")
        config = data.get("config", {})
        instance._fast_period = config.get("fast_period", 12)
        instance._slow_period = config.get("slow_period", 26)
        instance._signal_period = config.get("signal_period", 9)
        return instance
