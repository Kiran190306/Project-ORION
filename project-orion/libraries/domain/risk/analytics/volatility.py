"""Volatility analytics engine.

Computes annualized volatility using either:

- **Historical volatility**: sample standard deviation of returns.
- **EWMA volatility**: exponentially weighted moving average with a
  configurable decay factor (RiskMetrics-style, default lambda 0.94).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from libraries.domain.risk.analytics.models import VolatilityMethod, VolatilityMetrics
from libraries.domain.risk.analytics.validation import (
    validate_positive_float,
    validate_returns,
)


class VolatilityEngine:
    """Computes historical and EWMA volatility analytics."""

    async def calculate(
        self,
        returns: Sequence[float],
        periods_per_year: int = 252,
        window: int | None = None,
        method: VolatilityMethod = VolatilityMethod.HISTORICAL,
        lambda_factor: float = 0.94,
    ) -> VolatilityMetrics:
        """Compute annualized and rolling volatility.

        Args:
            returns: Period returns.
            periods_per_year: Number of periods per year.
            window: Optional rolling window.
            method: Historical or EWMA volatility.
            lambda_factor: Decay factor for EWMA (0 < lambda < 1).

        Returns:
            A VolatilityMetrics result.
        """
        validated = validate_returns(returns)
        periods = validate_positive_float(float(periods_per_year), "periods_per_year")

        mean_return = statistics.mean(validated)

        if method == VolatilityMethod.HISTORICAL:
            vol = statistics.pstdev(validated)
        elif method == VolatilityMethod.EWMA:
            lam = validate_positive_float(lambda_factor, "lambda_factor")
            if not 0.0 < lam < 1.0:
                raise ValueError("lambda_factor must be in (0, 1)")
            vol = self._ewma_volatility(validated, lam)
        else:
            raise ValueError(f"Unsupported volatility method: {method}")

        annualized_vol = vol * math.sqrt(periods)
        annualized_return = (1.0 + mean_return) ** periods - 1.0

        rolling: tuple[float, ...] = ()
        if window is not None:
            if not isinstance(window, int) or window < 1:
                raise ValueError("window must be a positive integer")
            if window > len(validated):
                raise ValueError(
                    f"window ({window}) exceeds data length ({len(validated)})"
                )
            rolling = self._rolling_volatility(validated, window, method, lambda_factor)

        return VolatilityMetrics(
            volatility=round(vol, 8),
            annualized_volatility=round(annualized_vol, 8),
            annualized_return=round(annualized_return, 8),
            mean_return=round(mean_return, 8),
            method=method,
            periods_per_year=int(periods),
            rolling_volatility=rolling,
        )

    @staticmethod
    def _ewma_volatility(returns: list[float], lam: float) -> float:
        """Compute EWMA volatility using the RiskMetrics recursion."""
        variance = returns[0] ** 2
        for r in returns[1:]:
            variance = lam * variance + (1.0 - lam) * (r**2)
        return math.sqrt(variance)

    @staticmethod
    def _rolling_volatility(
        returns: list[float],
        window: int,
        method: VolatilityMethod,
        lambda_factor: float,
    ) -> tuple[float, ...]:
        """Compute rolling volatility for a fixed window."""
        result: list[float] = []
        for start in range(len(returns) - window + 1):
            chunk = returns[start : start + window]
            if method == VolatilityMethod.EWMA:
                lam = lambda_factor
                variance = chunk[0] ** 2
                for r in chunk[1:]:
                    variance = lam * variance + (1.0 - lam) * (r**2)
                vol = math.sqrt(variance)
            else:
                vol = statistics.pstdev(chunk)
            result.append(round(vol, 8))
        return tuple(result)

