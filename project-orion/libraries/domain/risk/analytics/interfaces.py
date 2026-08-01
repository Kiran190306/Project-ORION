"""Protocol definitions for the Risk Analytics sub-package.

Every analytics engine is exposed through a runtime-checkable Protocol.
Implementations stay pure domain code — no I/O, no infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Protocol, runtime_checkable

from libraries.domain.risk.analytics.models import (
    ConcentrationMetrics,
    CorrelationResult,
    CvaRResult,
    DrawdownResult,
    ExposureMetrics,
    KellyResult,
    PerformanceMetrics,
    PositionExposure,
    VaRMethod,
    VaRResult,
    VolatilityMethod,
    VolatilityMetrics,
)


@runtime_checkable
class ValueAtRiskPort(Protocol):
    """Port for computing Value at Risk."""

    async def calculate(
        self,
        returns: Sequence[float],
        confidence_level: float = 0.95,
        horizon_days: int = 1,
        portfolio_value: Decimal | None = None,
        method: VaRMethod = VaRMethod.HISTORICAL,
    ) -> VaRResult:
        """Compute Value at Risk for a returns series.

        Args:
            returns: Historical period returns.
            confidence_level: Confidence level in (0, 1).
            horizon_days: Holding period in days.
            portfolio_value: Optional portfolio value for currency VaR.
            method: VaR method (historical / parametric / Monte Carlo).

        Returns:
            A VaRResult.
        """
        ...


@runtime_checkable
class ConditionalVarPort(Protocol):
    """Port for computing Conditional Value at Risk."""

    async def calculate(
        self,
        returns: Sequence[float],
        confidence_level: float = 0.95,
        horizon_days: int = 1,
        portfolio_value: Decimal | None = None,
        method: VaRMethod = VaRMethod.HISTORICAL,
    ) -> CvaRResult:
        """Compute Conditional Value at Risk (expected shortfall)."""
        ...


@runtime_checkable
class KellyCriterionPort(Protocol):
    """Port for computing the Kelly criterion."""

    async def calculate(
        self,
        win_probability: float,
        win_loss_ratio: float,
    ) -> KellyResult:
        """Compute the optimal Kelly fraction.

        Args:
            win_probability: Probability of a winning trade in [0, 1].
            win_loss_ratio: Average win / average loss (positive).

        Returns:
            A KellyResult.
        """
        ...


@runtime_checkable
class PerformanceMetricsPort(Protocol):
    """Port for computing risk-adjusted performance ratios."""

    async def calculate(
        self,
        returns: Sequence[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> PerformanceMetrics:
        """Compute Sharpe, Sortino, and Calmar ratios.

        Args:
            returns: Period returns.
            risk_free_rate: Annualized risk-free rate.
            periods_per_year: Number of periods per year (e.g. 252).

        Returns:
            A PerformanceMetrics result.
        """
        ...


@runtime_checkable
class DrawdownPort(Protocol):
    """Port for computing drawdown analytics."""

    async def calculate(
        self,
        values: Sequence[float],
        window: int | None = None,
    ) -> DrawdownResult:
        """Compute maximum and rolling drawdowns.

        Args:
            values: Equity / price series.
            window: Optional rolling window for rolling max drawdowns.

        Returns:
            A DrawdownResult.
        """
        ...


@runtime_checkable
class VolatilityPort(Protocol):
    """Port for computing volatility analytics."""

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
        ...


@runtime_checkable
class CorrelationPort(Protocol):
    """Port for computing correlation and beta analytics."""

    async def calculate(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        benchmark_returns: Sequence[float] | None = None,
        window: int | None = None,
    ) -> CorrelationResult:
        """Compute a correlation matrix and optional betas.

        Args:
            returns_by_symbol: Map of symbol to its returns series.
            benchmark_returns: Optional benchmark returns for betas.
            window: Optional rolling correlation window.

        Returns:
            A CorrelationResult.
        """
        ...


@runtime_checkable
class ExposurePort(Protocol):
    """Port for computing portfolio exposure analytics."""

    async def calculate(
        self,
        positions: Sequence[PositionExposure],
        portfolio_equity: Decimal,
    ) -> ExposureMetrics:
        """Compute gross/net exposure and allocation metrics.

        Args:
            positions: Portfolio positions.
            portfolio_equity: Current portfolio equity.

        Returns:
            An ExposureMetrics result.
        """
        ...


@runtime_checkable
class ConcentrationPort(Protocol):
    """Port for computing concentration metrics."""

    async def calculate(
        self,
        weights: Sequence[float],
        top_n: int = 3,
    ) -> ConcentrationMetrics:
        """Compute HHI and concentration metrics.

        Args:
            weights: Fractional weights summing to approximately 1.
            top_n: Number of top holdings to aggregate.

        Returns:
            A ConcentrationMetrics result.
        """
        ...

