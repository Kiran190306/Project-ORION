"""Benchmark comparison for backtesting.

Provides production-grade benchmark-relative performance analysis
including alpha, beta, correlation, tracking error, information ratio,
Treynor ratio, Jensen's alpha, up/down capture ratios, benchmark-relative
drawdown, and excess return statistics.

All calculations are stateless and thread-safe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BenchmarkComparisonConfig:
    """Configuration for benchmark comparison.

    Attributes:
        risk_free_rate: Annual risk-free rate (e.g., 0.02 for 2%).
        periods_per_year: Number of periods in a year (252 for daily).
        benchmark_label: Human-readable label for the benchmark.
    """

    risk_free_rate: float = 0.02
    periods_per_year: int = 252
    benchmark_label: str = "benchmark"


@dataclass(frozen=True, slots=True)
class BenchmarkStatistics:
    """Benchmark-relative performance statistics.

    Attributes:
        alpha: Excess return over CAPM-expected return.
        beta: Systematic risk relative to benchmark.
        correlation: Pearson correlation with benchmark returns.
        tracking_error: Standard deviation of excess returns.
        information_ratio: Excess return per unit of tracking error.
        treynor_ratio: Excess return per unit of beta.
        jensen_alpha: Same as alpha (CAPM-based abnormal return).
        up_capture_ratio: Performance in up markets vs benchmark.
        down_capture_ratio: Performance in down markets vs benchmark.
        up_down_capture_ratio: Up capture divided by down capture.
        max_relative_drawdown: Maximum peak-to-trough vs benchmark.
        excess_return: Total portfolio return minus benchmark return.
        excess_return_pct: Percentage excess return.
        excess_volatility: Volatility of excess returns.
        num_periods: Number of periods analyzed.
        is_statistically_significant: True if enough data points.
    """

    alpha: float = 0.0
    beta: float = 1.0
    correlation: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    treynor_ratio: float = 0.0
    jensen_alpha: float = 0.0
    up_capture_ratio: float = 1.0
    down_capture_ratio: float = 1.0
    up_down_capture_ratio: float = 1.0
    max_relative_drawdown: float = 0.0
    max_relative_drawdown_pct: float = 0.0
    excess_return: float = 0.0
    excess_return_pct: float = 0.0
    excess_volatility: float = 0.0
    num_periods: int = 0
    is_statistically_significant: bool = False


class BenchmarkComparator:
    """Compares portfolio performance against a benchmark.

    Provides comprehensive benchmark-relative statistics for
    performance evaluation and risk assessment.

    Usage:
        comparator = BenchmarkComparator()
        stats = comparator.calculate(portfolio_returns, benchmark_returns)
    """

    def __init__(self, config: BenchmarkComparisonConfig | None = None) -> None:
        """Initialize benchmark comparator.

        Args:
            config: Benchmark comparison configuration.
        """
        self._config = config or BenchmarkComparisonConfig()

    @property
    def config(self) -> BenchmarkComparisonConfig:
        """Return the current configuration."""
        return self._config

    def calculate(
        self,
        portfolio_returns: list[float],
        benchmark_returns: list[float],
    ) -> BenchmarkStatistics:
        """Calculate benchmark-relative statistics.

        Args:
            portfolio_returns: Portfolio period returns (e.g., daily).
            benchmark_returns: Benchmark period returns (same periods).

        Returns:
            Benchmark statistics with all calculated metrics.
        """
        if not portfolio_returns or not benchmark_returns:
            return BenchmarkStatistics()

        # Align lengths
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        if min_len < 2:
            return BenchmarkStatistics()

        p_returns = portfolio_returns[:min_len]
        b_returns = benchmark_returns[:min_len]
        excess_returns = [p - b for p, b in zip(p_returns, b_returns)]

        cfg = self._config

        # Basic statistics
        p_mean = sum(p_returns) / min_len
        b_mean = sum(b_returns) / min_len
        excess_mean = sum(excess_returns) / min_len

        # Portfolio variance
        p_variance = (
            sum((r - p_mean) ** 2 for r in p_returns) / min_len
            if min_len > 0
            else 0.0
        )
        p_std = math.sqrt(p_variance) if p_variance > 0 else 0.0

        # Benchmark variance
        b_variance = (
            sum((r - b_mean) ** 2 for r in b_returns) / min_len
            if min_len > 0
            else 0.0
        )
        b_std = math.sqrt(b_variance) if b_variance > 0 else 0.0

        # Excess variance
        excess_variance = (
            sum((r - excess_mean) ** 2 for r in excess_returns) / min_len
            if min_len > 0
            else 0.0
        )
        excess_std = math.sqrt(excess_variance) if excess_variance > 0 else 0.0

        # Covariance and beta
        covariance = sum(
            (p - p_mean) * (b - b_mean)
            for p, b in zip(p_returns, b_returns)
        ) / min_len if min_len > 0 else 0.0

        beta = covariance / b_variance if b_variance > 0 else 1.0

        # Correlation
        correlation = (
            covariance / (p_std * b_std)
            if p_std > 0 and b_std > 0
            else 0.0
        )

        # Alpha (CAPM-based)
        annual_factor = cfg.periods_per_year
        rf_per_period = cfg.risk_free_rate / annual_factor
        alpha = p_mean - (rf_per_period + beta * (b_mean - rf_per_period))

        # Tracking error and information ratio
        tracking_error = excess_std * math.sqrt(annual_factor)
        information_ratio = (
            (excess_mean * annual_factor) / tracking_error
            if tracking_error > 0
            else 0.0
        )

        # Treynor ratio
        excess_portfolio_annual = (p_mean - rf_per_period) * annual_factor
        treynor_ratio = (
            excess_portfolio_annual / beta
            if beta != 0
            else 0.0
        )

        # Up/down capture ratios
        up_portfolio = sum(
            r for r, b in zip(p_returns, b_returns) if b > 0
        )
        up_benchmark = sum(
            b for b in b_returns if b > 0
        )
        down_portfolio = sum(
            abs(r) for r, b in zip(p_returns, b_returns) if b < 0
        )
        down_benchmark = sum(
            abs(b) for b in b_returns if b < 0
        )

        up_capture = up_portfolio / up_benchmark if up_benchmark != 0 else 1.0
        down_capture = down_portfolio / down_benchmark if down_benchmark != 0 else 1.0
        up_down_ratio = up_capture / down_capture if down_capture != 0 else 1.0

        # Excess return
        total_p_return = sum(p_returns)
        total_b_return = sum(b_returns)
        excess_return = total_p_return - total_b_return
        excess_return_pct = (
            (total_p_return - total_b_return) / abs(total_b_return) * 100
            if total_b_return != 0
            else 0.0
        )

        # Maximum relative drawdown
        max_rel_dd = self._calculate_max_relative_drawdown(
            p_returns, b_returns
        )

        # Statistical significance
        is_significant = min_len >= 30

        return BenchmarkStatistics(
            alpha=round(alpha, 6),
            beta=round(beta, 4),
            correlation=round(correlation, 4),
            tracking_error=round(tracking_error, 4),
            information_ratio=round(information_ratio, 4),
            treynor_ratio=round(treynor_ratio, 4),
            jensen_alpha=round(alpha, 6),
            up_capture_ratio=round(up_capture, 4),
            down_capture_ratio=round(down_capture, 4),
            up_down_capture_ratio=round(up_down_ratio, 4),
            max_relative_drawdown=round(max_rel_dd, 2),
            max_relative_drawdown_pct=round(
                max_rel_dd / (sum(p_returns) / min_len) * 100 if min_len > 0 and sum(p_returns) != 0 else 0.0,
                2,
            ),
            excess_return=round(excess_return, 4),
            excess_return_pct=round(excess_return_pct, 4),
            excess_volatility=round(excess_std, 4),
            num_periods=min_len,
            is_statistically_significant=is_significant,
        )

    @staticmethod
    def _calculate_max_relative_drawdown(
        portfolio_returns: list[float],
        benchmark_returns: list[float],
    ) -> float:
        """Calculate maximum relative drawdown.

        Computes the maximum peak-to-trough decline of the
        portfolio relative to the benchmark.

        Args:
            portfolio_returns: Portfolio period returns.
            benchmark_returns: Benchmark period returns.

        Returns:
            Maximum relative drawdown as a float.
        """
        cumulative_p = 1.0
        cumulative_b = 1.0
        peak_ratio = 1.0
        max_dd = 0.0

        for p_ret, b_ret in zip(portfolio_returns, benchmark_returns):
            cumulative_p *= 1.0 + p_ret
            cumulative_b *= 1.0 + b_ret
            ratio = cumulative_p / cumulative_b if cumulative_b != 0 else 1.0
            if ratio > peak_ratio:
                peak_ratio = ratio
            dd = peak_ratio - ratio
            if dd > max_dd:
                max_dd = dd

        return max_dd

