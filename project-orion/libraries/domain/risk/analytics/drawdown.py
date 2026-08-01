"""Drawdown analytics engine.

Computes maximum drawdown, current drawdown, peak/trough values,
drawdown duration, and an optional rolling maximum drawdown series.
"""

from __future__ import annotations

from collections.abc import Sequence

from libraries.domain.risk.analytics.models import DrawdownResult
from libraries.domain.risk.analytics.validation import (
    InvalidWindowError,
    validate_returns,
)


class DrawdownEngine:
    """Computes drawdown analytics over an equity / price series."""

    async def calculate(
        self,
        values: Sequence[float],
        window: int | None = None,
    ) -> DrawdownResult:
        """Compute drawdown analytics.

        Args:
            values: Equity or price series (strictly positive).
            window: Optional rolling window for rolling max drawdowns.

        Returns:
            A DrawdownResult.
        """
        series = validate_returns(values, min_length=1)
        if any(v <= 0.0 for v in series):
            raise InvalidWindowError("values must be strictly positive")

        peak = series[0]
        peak_index = 0
        trough = series[0]
        max_drawdown = 0.0
        max_peak_index = 0
        max_trough_index = 0
        current_drawdown = 0.0

        drawdown_series: list[float] = []

        for i, value in enumerate(series):
            if value > peak:
                peak = value
                peak_index = i
            drawdown = (peak - value) / peak * 100.0 if peak > 0 else 0.0
            drawdown_series.append(drawdown)
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_peak_index = peak_index
                max_trough_index = i
            if i == len(series) - 1:
                current_drawdown = drawdown
            if value < trough or i == 0:
                trough = value

        duration = max_trough_index - max_peak_index if max_trough_index >= max_peak_index else 0

        rolling: tuple[float, ...] = ()
        if window is not None:
            rolling = self._rolling_max_drawdown(series, window)

        return DrawdownResult(
            max_drawdown=round(max_drawdown, 6),
            current_drawdown=round(current_drawdown, 6),
            peak_value=peak,
            trough_value=trough,
            peak_index=max_peak_index,
            trough_index=max_trough_index,
            max_drawdown_duration=duration,
            series=tuple(round(d, 6) for d in drawdown_series),
            rolling_max_drawdowns=rolling,
        )

    @staticmethod
    def _rolling_max_drawdown(
        series: list[float],
        window: int,
    ) -> tuple[float, ...]:
        """Compute rolling max drawdown for a fixed window."""
        if not isinstance(window, int) or window < 1:
            raise InvalidWindowError(f"window must be a positive integer, got {window!r}")
        if window > len(series):
            raise InvalidWindowError(
                f"window ({window}) exceeds data length ({len(series)})"
            )

        result: list[float] = []
        for start in range(len(series) - window + 1):
            chunk = series[start : start + window]
            peak = chunk[0]
            max_dd = 0.0
            for v in chunk:
                peak = max(peak, v)
                dd = (peak - v) / peak * 100.0 if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
            result.append(round(max_dd, 6))
        return tuple(result)
