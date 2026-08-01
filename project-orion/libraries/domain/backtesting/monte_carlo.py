"""Monte Carlo simulation for backtesting.

Supports random trade ordering, trade removal, spread variation,
slippage variation, and execution delay randomization to assess
strategy robustness under uncertainty.
"""

from __future__ import annotations

import math
import random
from typing import Any

from libraries.domain.backtesting.models import MonteCarloConfig, MonteCarloResult


class MonteCarloSimulator:
    """Executes Monte Carlo simulations to assess strategy robustness.

    Randomizes trade outcomes, ordering, spreads, slippage, and execution
    delays to generate a distribution of possible outcomes.
    """

    def __init__(self, config: MonteCarloConfig | None = None) -> None:
        """Initialize Monte Carlo simulator.

        Args:
            config: Monte Carlo configuration.
        """
        self._config = config or MonteCarloConfig(
            num_simulations=1000,
            random_seed=42,
        )
        self._random = random.Random(self._config.random_seed)

    @property
    def config(self) -> MonteCarloConfig:
        return self._config

    async def simulate_trade_ordering(
        self,
        trades: list[dict[str, Any]],
        num_simulations: int | None = None,
    ) -> MonteCarloResult:
        """Simulate random reordering of trades.

        Args:
            trades: List of trade records.
            num_simulations: Number of simulations (default from config).

        Returns:
            Monte Carlo result with distribution of outcomes.
        """
        n = num_simulations or self._config.num_simulations
        outcomes = []

        for _ in range(n):
            shuffled = list(trades)
            self._random.shuffle(shuffled)
            total_pnl = sum(t.get("pnl", 0) for t in shuffled)
            outcomes.append(total_pnl)

        return self._compute_result(outcomes, "trade_ordering", n)

    async def simulate_trade_removal(
        self,
        trades: list[dict[str, Any]],
        removal_fraction: float = 0.1,
        num_simulations: int | None = None,
    ) -> MonteCarloResult:
        """Simulate random trade removal (skip fraction of trades).

        Args:
            trades: List of trade records.
            removal_fraction: Fraction of trades to remove (0-1).
            num_simulations: Number of simulations.

        Returns:
            Monte Carlo result.
        """
        n = num_simulations or self._config.num_simulations
        outcomes = []

        for _ in range(n):
            remaining = [t for t in trades if self._random.random() > removal_fraction]
            total_pnl = sum(t.get("pnl", 0) for t in remaining)
            outcomes.append(total_pnl)

        return self._compute_result(outcomes, "trade_removal", n)

    async def simulate_spread_variation(
        self,
        base_pnl: float,
        spread_cost_per_trade: float,
        num_simulations: int | None = None,
    ) -> MonteCarloResult:
        """Simulate spread variation impact on PnL.

        Args:
            base_pnl: Base strategy PnL.
            spread_cost_per_trade: Spread cost per trade.
            num_simulations: Number of simulations.

        Returns:
            Monte Carlo result.
        """
        n = num_simulations or self._config.num_simulations
        outcomes = []

        for _ in range(n):
            spread_multiplier = self._random.uniform(0.5, 3.0)
            adjusted_pnl = base_pnl - (spread_cost_per_trade * (spread_multiplier - 1.0))
            outcomes.append(adjusted_pnl)

        return self._compute_result(outcomes, "spread_variation", n)

    async def simulate_slippage_variation(
        self,
        base_pnl: float,
        slippage_cost_per_trade: float,
        num_simulations: int | None = None,
    ) -> MonteCarloResult:
        """Simulate slippage variation impact on PnL.

        Args:
            base_pnl: Base strategy PnL.
            slippage_cost_per_trade: Slippage cost per trade.
            num_simulations: Number of simulations.

        Returns:
            Monte Carlo result.
        """
        n = num_simulations or self._config.num_simulations
        outcomes = []

        for _ in range(n):
            slippage_multiplier = self._random.uniform(0.0, 5.0)
            adjusted_pnl = base_pnl - (slippage_cost_per_trade * slippage_multiplier)
            outcomes.append(adjusted_pnl)

        return self._compute_result(outcomes, "slippage_variation", n)

    async def simulate_execution_delay(
        self,
        trades: list[dict[str, Any]],
        price_impact_per_bar: float = 0.001,
        num_simulations: int | None = None,
    ) -> MonteCarloResult:
        """Simulate execution delay impact on trade prices.

        Args:
            trades: List of trade records with 'price' key.
            price_impact_per_bar: Price impact per bar of delay.
            num_simulations: Number of simulations.

        Returns:
            Monte Carlo result.
        """
        n = num_simulations or self._config.num_simulations
        outcomes = []

        for _ in range(n):
            total_pnl = 0.0
            for trade in trades:
                delay_bars = self._random.randint(0, 5)
                price_impact = 1.0 + (delay_bars * price_impact_per_bar)
                pnl = trade.get("pnl", 0) * (1.0 - abs(price_impact - 1.0))
                total_pnl += pnl
            outcomes.append(total_pnl)

        return self._compute_result(outcomes, "execution_delay", n)

    async def run_all(
        self,
        trades: list[dict[str, Any]],
        spread_cost_per_trade: float = 0.0,
        slippage_cost_per_trade: float = 0.0,
    ) -> dict[str, MonteCarloResult]:
        """Run all Monte Carlo simulations.

        Args:
            trades: List of trade records.
            spread_cost_per_trade: Spread cost per trade.
            slippage_cost_per_trade: Slippage cost per trade.

        Returns:
            Dict mapping simulation name to result.
        """
        return {
            "trade_ordering": await self.simulate_trade_ordering(trades),
            "trade_removal": await self.simulate_trade_removal(trades),
            "spread_variation": await self.simulate_spread_variation(
                sum(t.get("pnl", 0) for t in trades) if trades else 0.0,
                spread_cost_per_trade,
            ),
            "slippage_variation": await self.simulate_slippage_variation(
                sum(t.get("pnl", 0) for t in trades) if trades else 0.0,
                slippage_cost_per_trade,
            ),
            "execution_delay": await self.simulate_execution_delay(trades),
        }

    def _compute_result(
        self,
        outcomes: list[float],
        simulation_type: str,
        num_simulations: int,
    ) -> MonteCarloResult:
        """Compute Monte Carlo result from outcomes.

        Args:
            outcomes: List of simulation outcomes.
            simulation_type: Type of simulation.
            num_simulations: Number of simulations.

        Returns:
            MonteCarloResult with descriptive statistics.
        """
        if not outcomes:
            return MonteCarloResult(
                simulation_type=simulation_type,
                num_simulations=num_simulations,
                median=0.0,
                mean=0.0,
                std=0.0,
                min_val=0.0,
                max_val=0.0,
                percentile_5=0.0,
                percentile_25=0.0,
                percentile_75=0.0,
                percentile_95=0.0,
                pct_positive=0.0,
                median_final_equity=0.0,
                mean_final_equity=0.0,
                std_final_equity=0.0,
                min_final_equity=0.0,
                max_final_equity=0.0,
                prob_profit=0.0,
                prob_ruin=0.0,
                median_max_drawdown=0.0,
                mean_max_drawdown=0.0,
                ci_lower_95=0.0,
                ci_upper_95=0.0,
                ci_lower_99=0.0,
                ci_upper_99=0.0,
                random_seed=self._config.random_seed,
            )

        sorted_outcomes = sorted(outcomes)
        n = len(sorted_outcomes)

        mean_val = sum(sorted_outcomes) / n
        variance = sum((x - mean_val) ** 2 for x in sorted_outcomes) / n
        std_val = math.sqrt(variance) if variance > 0 else 0.0
        pct_positive = sum(1 for x in sorted_outcomes if x > 0) / n

        def percentile(sorted_data: list[float], p: float) -> float:
            idx = int(len(sorted_data) * p / 100)
            return sorted_data[min(idx, len(sorted_data) - 1)]

        median_val = sorted_outcomes[n // 2] if n > 0 else 0.0
        mean_val_rounded = round(mean_val, 2)

        return MonteCarloResult(
            simulation_type=simulation_type,
            num_simulations=num_simulations,
            median=median_val,
            mean=mean_val_rounded,
            std=round(std_val, 2),
            min_val=round(sorted_outcomes[0], 2),
            max_val=round(sorted_outcomes[-1], 2),
            percentile_5=round(percentile(sorted_outcomes, 5), 2),
            percentile_25=round(percentile(sorted_outcomes, 25), 2),
            percentile_75=round(percentile(sorted_outcomes, 75), 2),
            percentile_95=round(percentile(sorted_outcomes, 95), 2),
            pct_positive=round(pct_positive, 4),
            median_final_equity=median_val,
            mean_final_equity=mean_val_rounded,
            std_final_equity=round(std_val, 2),
            min_final_equity=round(sorted_outcomes[0], 2),
            max_final_equity=round(sorted_outcomes[-1], 2),
            prob_profit=round(pct_positive, 4),
            prob_ruin=round(sum(1 for x in sorted_outcomes if x <= 0) / n, 4),
            median_max_drawdown=0.0,
            mean_max_drawdown=0.0,
            ci_lower_95=round(percentile(sorted_outcomes, 2.5), 2),
            ci_upper_95=round(percentile(sorted_outcomes, 97.5), 2),
            ci_lower_99=round(percentile(sorted_outcomes, 0.5), 2),
            ci_upper_99=round(percentile(sorted_outcomes, 99.5), 2),
            random_seed=self._config.random_seed,
        )
