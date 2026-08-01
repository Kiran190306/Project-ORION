"""Risk-adjusted performance ratios analytics engine.

Implements:
- **Sharpe ratio**: (portfolio return - risk-free) / portfolio volatility.
- **Sortino ratio**: (portfolio return - risk-free) / downside deviation.
- **Calmar ratio**: annualized return / max drawdown.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from libraries.domain.risk.analytics.models import PerformanceMetrics
from libraries.domain.risk.analytics.validation import (
    validate_positive_float,
    validate_returns,
)


class PerformanceMetricsEngine:
    """Computes Sharpe, Sortino, and Calmar ratios."""

    async def calculate(
        self,
        returns: Sequence[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> PerformanceMetrics:
        """Compute risk-adjusted performance metrics.

        Args:
            returns: Period returns.
            risk_free_rate: Annualized risk-free rate (e.g. 0.03).
            periods_per_year: Number of periods per year (default 252).

        Returns:
            A PerformanceMetrics result.
        """
        validated = validate_returns(returns)
        periods = validate_positive_float(float(periods_per_year), "periods_per_year")
        rf = float(risk_free_rate)

        mean_return = statistics.mean(validated)
        vol = statistics.pstdev(validated)

        annualized_return = (1.0 + mean_return) ** periods - 1.0
        annualized_vol = vol * math.sqrt(periods)

        # Per-period risk-free rate.
        rf_period = (1.0 + rf) ** (1.0 / periods) - 1.0

        sharpe = 0.0
        if annualized_vol > 1e-12:
            sharpe = (annualized_return - rf) / annualized_vol

        # Downside deviation (only negative excess returns).
        downside_returns = [r for r in validated if r < rf_period]
        downside_deviation = 0.0
        if downside_returns:
            variance = sum((r - rf_period) ** 2 for r in downside_returns) / len(
                downside_returns
            )
            downside_deviation = math.sqrt(variance) * math.sqrt(periods)

        sortino = 0.0
        if downside_deviation > 1e-12:
            sortino = (annualized_return - rf) / downside_deviation

        # Calmar ratio needs max drawdown of the cumulative equity curve.
        max_drawdown = self._max_drawdown_from_returns(validated)
        calmar = 0.0
        if max_drawdown > 1e-12:
            calmar = annualized_return / max_drawdown

        return PerformanceMetrics(
            sharpe_ratio=round(sharpe, 6),
            sortino_ratio=round(sortino, 6),
            calmar_ratio=round(calmar, 6),
            annualized_return=round(annualized_return, 6),
            annualized_volatility=round(annualized_vol, 6),
            downside_deviation=round(downside_deviation, 6),
            max_drawdown=round(max_drawdown, 6),
            risk_free_rate=rf,
            periods_per_year=int(periods),
        )

    @staticmethod
    def _max_drawdown_from_returns(returns: list[float]) -> float:
        """Compute max drawdown (positive fraction) from a returns series."""
        equity = 1.0
        peak = 1.0
        max_drawdown = 0.0
        for r in returns:
            equity *= 1.0 + r
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak if peak > 0 else 0.0
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown
