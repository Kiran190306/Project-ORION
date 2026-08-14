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
    Scenario,
    StressTestResult,
    StressTestSummary,
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


@runtime_checkable
class StressTestPort(Protocol):
    """Port for running portfolio stress tests.

    Implementations cover scenario analysis, historical stress testing,
    portfolio shock analysis, market crash simulation, and volatility
    shocks. All methods are deterministic and pure domain logic.
    """

    async def apply_scenario(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        scenario: Scenario,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Apply a named scenario to a set of symbols.

        Args:
            returns_by_symbol: Map of symbol to its historical returns.
            scenario: The scenario to apply.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestResult.
        """
        ...

    async def run_historical_stress(
        self,
        returns_by_symbol: Mapping[str, Mapping[str, Sequence[float]]],
        portfolio_weights: Mapping[str, float],
        portfolio_value: Decimal,
    ) -> StressTestSummary:
        """Run historical stress testing across named windows.

        Args:
            returns_by_symbol: Map of window name to symbol returns.
            portfolio_weights: Map of symbol to portfolio weight.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestSummary.
        """
        ...

    async def apply_portfolio_shock(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        portfolio_weights: Mapping[str, float],
        shock_pct: float,
        portfolio_value: Decimal,
    ) -> StressTestSummary:
        """Apply a simultaneous shock to all portfolio symbols.

        Args:
            returns_by_symbol: Map of symbol to its historical returns.
            portfolio_weights: Map of symbol to portfolio weight.
            shock_pct: Uniform shock to apply (e.g. 0.10 = 10%).
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestSummary.
        """
        ...

    async def simulate_market_crash(
        self,
        returns: Sequence[float],
        crash_pct: float,
        recovery_days: int,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Simulate a market crash followed by a recovery path.

        Args:
            returns: Historical returns for the symbol.
            crash_pct: Crash magnitude as a fraction (e.g. 0.30 = 30%).
            recovery_days: Number of recovery days to simulate.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestResult.
        """
        ...

    async def apply_volatility_shock(
        self,
        returns: Sequence[float],
        volatility_multiplier: float,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Apply a volatility multiplier to a returns series.

        Args:
            returns: Historical returns for the symbol.
            volatility_multiplier: Multiplier applied to the price shocks.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestResult.
        """
        ...

