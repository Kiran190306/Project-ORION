"""Stress Analysis engine for the Risk Analytics sub-package.

Implements deterministic portfolio stress testing:

- **Scenario Analysis**: apply named user-defined shocks to a portfolio.
- **Historical Stress Testing**: replay worst historical drawdown windows.
- **Portfolio Shock Analysis**: apply a simultaneous uniform shock to all
  symbols.
- **Market Crash Simulation**: simulate a crash followed by a recovery
  path.
- **Volatility Shock**: scale the historical volatility of a return
  series.

All calculations are pure domain logic — no I/O, no infrastructure.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from decimal import Decimal

from libraries.domain.risk.analytics.models import (
    Scenario,
    StressTestResult,
    StressTestSummary,
    StressTestType,
)
from libraries.domain.risk.analytics.validation import (
    InvalidValueError,
    validate_positive_float,
    validate_returns,
)


class StressTestEngine:
    """Runs deterministic portfolio stress tests.

    Pure domain engine. All methods are async to conform to the
    ``StressTestPort`` protocol, but perform no I/O.
    """

    async def apply_scenario(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        scenario: Scenario,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Apply a named scenario to a set of symbols.

        Each symbol's shocked return is the scenario's shock factor for
        that symbol. Symbols not present in the scenario are unshocked.

        Args:
            returns_by_symbol: Map of symbol to its historical returns.
            scenario: The scenario to apply.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestResult.
        """
        if not scenario.shock_factors:
            raise InvalidValueError("scenario must define at least one shock factor")

        symbol_returns: dict[str, float] = {}
        for symbol in returns_by_symbol:
            factor = scenario.shock_factors.get(symbol, 0.0)
            symbol_returns[symbol] = factor

        portfolio_return = sum(symbol_returns.values()) / max(len(symbol_returns), 1)
        shocked_value = portfolio_value * (Decimal(1) + Decimal(str(portfolio_return)))

        return StressTestResult(
            test_type=StressTestType.SCENARIO,
            name=scenario.name,
            portfolio_value=shocked_value,
            portfolio_return=portfolio_return,
            symbol_returns=symbol_returns,
            description=scenario.description,
            volatility_multiplier=scenario.volatility_multiplier,
        )

    async def run_historical_stress(
        self,
        returns_by_symbol: Mapping[str, Mapping[str, Sequence[float]]],
        portfolio_weights: Mapping[str, float],
        portfolio_value: Decimal,
    ) -> StressTestSummary:
        """Run historical stress testing across named windows.

        Each window defines a set of returns per symbol. The portfolio
        return for a window is the weighted sum of each symbol's
        worst-case return (the minimum return in that window).

        Args:
            returns_by_symbol: Map of window name to symbol returns.
            portfolio_weights: Map of symbol to portfolio weight.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestSummary aggregating all windows.
        """
        if not returns_by_symbol:
            raise InvalidValueError("returns_by_symbol must not be empty")
        if not portfolio_weights:
            raise InvalidValueError("portfolio_weights must not be empty")

        results: list[StressTestResult] = []
        for window_name, symbol_returns in returns_by_symbol.items():
            symbol_impacts: dict[str, float] = {}
            for symbol, returns in symbol_returns.items():
                validated = validate_returns(returns)
                weight = portfolio_weights.get(symbol, 0.0)
                worst = min(validated)
                symbol_impacts[symbol] = worst * weight

            portfolio_return = sum(symbol_impacts.values())
            shocked_value = portfolio_value * (
                Decimal(1) + Decimal(str(portfolio_return))
            )
            results.append(
                StressTestResult(
                    test_type=StressTestType.HISTORICAL,
                    name=window_name,
                    portfolio_value=shocked_value,
                    portfolio_return=portfolio_return,
                    symbol_returns=dict(symbol_impacts),
                )
            )

        return self._build_summary(
            test_type=StressTestType.HISTORICAL,
            name="historical_stress",
            results=results,
        )

    async def apply_portfolio_shock(
        self,
        returns_by_symbol: Mapping[str, Sequence[float]],
        portfolio_weights: Mapping[str, float],
        shock_pct: float,
        portfolio_value: Decimal,
    ) -> StressTestSummary:
        """Apply a simultaneous uniform shock to all portfolio symbols.

        The shocked return for each symbol is the shock magnitude scaled
        by the ratio of the symbol's historical volatility to the average
        volatility across all symbols.

        Args:
            returns_by_symbol: Map of symbol to its historical returns.
            portfolio_weights: Map of symbol to portfolio weight.
            shock_pct: Uniform shock to apply (e.g. 0.10 = 10%).
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestSummary.
        """
        shock = validate_positive_float(shock_pct, "shock_pct")
        if not returns_by_symbol:
            raise InvalidValueError("returns_by_symbol must not be empty")
        if not portfolio_weights:
            raise InvalidValueError("portfolio_weights must not be empty")

        # Compute per-symbol volatility to scale the shock.
        vols: dict[str, float] = {}
        for symbol, returns in returns_by_symbol.items():
            validated = validate_returns(returns)
            vols[symbol] = self._stddev(validated)

        avg_vol = sum(vols.values()) / max(len(vols), 1) if vols else 1.0

        symbol_impacts: dict[str, float] = {}
        for symbol, vol in vols.items():
            weight = portfolio_weights.get(symbol, 0.0)
            scale = (vol / avg_vol) if avg_vol > 0.0 else 1.0
            symbol_impacts[symbol] = -shock * scale * weight

        portfolio_return = sum(symbol_impacts.values())
        result = StressTestResult(
            test_type=StressTestType.PORTFOLIO_SHOCK,
            name=f"portfolio_shock_{shock:.4f}",
            portfolio_value=portfolio_value
            * (Decimal(1) + Decimal(str(portfolio_return))),
            portfolio_return=portfolio_return,
            symbol_returns=symbol_impacts,
        )
        return self._build_summary(
            test_type=StressTestType.PORTFOLIO_SHOCK,
            name="portfolio_shock",
            results=[result],
        )

    async def simulate_market_crash(
        self,
        returns: Sequence[float],
        crash_pct: float,
        recovery_days: int,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Simulate a market crash followed by a recovery path.

        The crash is applied as an immediate shock, then a mean-reverting
        recovery path is simulated over ``recovery_days`` using the
        historical mean return.

        Args:
            returns: Historical returns for the symbol.
            crash_pct: Crash magnitude as a fraction (e.g. 0.30 = 30%).
            recovery_days: Number of recovery days to simulate.
            portfolio_value: Current portfolio value.

        Returns:
            A StressTestResult.
        """
        crash = validate_positive_float(crash_pct, "crash_pct")
        if not isinstance(recovery_days, int) or recovery_days < 0:
            raise InvalidValueError("recovery_days must be a non-negative integer")

        validated = validate_returns(returns)
        mean_return = sum(validated) / len(validated)
        crash_return = -crash
        recovery_return = mean_return * recovery_days
        total_return = crash_return + recovery_return

        shocked_value = portfolio_value * (Decimal(1) + Decimal(str(total_return)))

        return StressTestResult(
            test_type=StressTestType.MARKET_CRASH,
            name=f"market_crash_{crash:.4f}",
            portfolio_value=shocked_value,
            portfolio_return=total_return,
            symbol_returns={"portfolio": total_return},
            description=(
                f"Immediate {crash * 100.0:.2f}% crash followed by "
                f"{recovery_days} recovery days"
            ),
        )

    async def apply_volatility_shock(
        self,
        returns: Sequence[float],
        volatility_multiplier: float,
        portfolio_value: Decimal,
    ) -> StressTestResult:
        """Apply a volatility multiplier to a returns series.

        The shocked return is the product of the historical mean return
        and the volatility multiplier times the standard deviation of the
        series.

        Args:
            returns: Historical returns for the symbol.
            volatility_multiplier: Multiplier applied to the price shocks.
            portfolio_value: Current portfolio value.

            Returns:
                A StressTestResult.
        """
        multiplier = validate_positive_float(
            volatility_multiplier, "volatility_multiplier"
        )
        validated = validate_returns(returns)

        mean_return = sum(validated) / len(validated)
        stddev = self._stddev(validated)
        shocked_return = mean_return - stddev * multiplier

        shocked_value = portfolio_value * (Decimal(1) + Decimal(str(shocked_return)))

        return StressTestResult(
            test_type=StressTestType.VOLATILITY_SHOCK,
            name=f"volatility_shock_{multiplier:.2f}x",
            portfolio_value=shocked_value,
            portfolio_return=shocked_return,
            symbol_returns={"portfolio": shocked_return},
            volatility_multiplier=multiplier,
        )

    # ─── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _stddev(values: list[float]) -> float:
        """Compute the population standard deviation of a list."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    @staticmethod
    def _build_summary(
        *,
        test_type: StressTestType,
        name: str,
        results: list[StressTestResult],
    ) -> StressTestSummary:
        """Aggregate a list of stress test results into a summary."""
        if not results:
            raise InvalidValueError("at least one stress result is required")

        returns = [r.portfolio_return for r in results]
        worst = min(returns)
        best = max(returns)
        average = sum(returns) / len(returns)
        shock_pct = max(0.0, -worst) * 100.0

        return StressTestSummary(
            test_type=test_type,
            name=name,
            worst_case_return=worst,
            best_case_return=best,
            average_return=average,
            portfolio_shock_pct=shock_pct,
            results=tuple(results),
        )
