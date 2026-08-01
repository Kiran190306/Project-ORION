"""Conditional Value at Risk (expected shortfall) analytics engine.

CVaR measures the average loss beyond the VaR threshold. It is more
sensitive to the shape of the loss tail than VaR alone.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Sequence
from decimal import Decimal

from libraries.domain.risk.analytics.models import CvaRResult, VaRMethod
from libraries.domain.risk.analytics.validation import (
    validate_confidence_level,
    validate_horizon,
    validate_returns,
)


class ConditionalVarEngine:
    """Computes CVaR for historical, parametric, and Monte Carlo methods."""

    def __init__(self, random_seed: int | None = 42) -> None:
        self._random_seed = random_seed

    async def calculate(
        self,
        returns: Sequence[float],
        confidence_level: float = 0.95,
        horizon_days: int = 1,
        portfolio_value: Decimal | None = None,
        method: VaRMethod = VaRMethod.HISTORICAL,
    ) -> CvaRResult:
        """Compute Conditional Value at Risk.

        Args:
            returns: Historical period returns.
            confidence_level: Confidence level in (0, 1).
            horizon_days: Holding period in days.
            portfolio_value: Optional portfolio value for currency CVaR.
            method: VaR method.

        Returns:
            A CvaRResult with ``cvar_pct`` as a positive percentage.
        """
        validated = validate_returns(returns)
        level = validate_confidence_level(confidence_level)
        horizon = validate_horizon(horizon_days)

        if method == VaRMethod.HISTORICAL:
            cvar_pct, var_pct, simulations = self._historical_cvar(
                validated, level, horizon
            )
        elif method == VaRMethod.PARAMETRIC:
            cvar_pct, var_pct, simulations = self._parametric_cvar(
                validated, level, horizon
            )
        elif method == VaRMethod.MONTE_CARLO:
            cvar_pct, var_pct, simulations = self._monte_carlo_cvar(
                validated, level, horizon
            )
        else:
            raise ValueError(f"Unsupported CVaR method: {method}")

        cvar_amount: Decimal | None = None
        if portfolio_value is not None and portfolio_value > 0:
            cvar_amount = portfolio_value * (Decimal(str(cvar_pct)) / Decimal(100))

        return CvaRResult(
            method=method,
            confidence_level=level,
            horizon_days=horizon,
            cvar_pct=round(cvar_pct, 6),
            var_pct=round(var_pct, 6),
            cvar_amount=cvar_amount,
            simulations=simulations,
        )

    # ─── Historical ─────────────────────────────────────────────

    def _historical_cvar(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, int]:
        """Historical CVaR = average of the worst (1 - c) losses."""
        sorted_returns = sorted(returns)
        tail_probability = 1.0 - confidence_level
        tail_count = max(1, math.ceil(tail_probability * len(sorted_returns)))
        tail = sorted_returns[:tail_count]
        average_tail_return = statistics.mean(tail)
        var_pct = -tail[-1]  # Worst accepted (boundary) loss.
        scale = math.sqrt(horizon_days)
        cvar_pct = -average_tail_return * scale * 100.0
        var_pct = var_pct * scale * 100.0
        return cvar_pct, var_pct, 0

    # ─── Parametric ─────────────────────────────────────────────

    def _parametric_cvar(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, int]:
        """Parametric CVaR for a normal distribution.

        CVaR = mu + sigma * phi(z) / (1 - c) where z = Phi^-1(c)
        and phi is the standard normal PDF.
        """
        mean_return = statistics.mean(returns)
        vol = statistics.pstdev(returns)
        if vol <= 0.0:
            return 0.0, 0.0, 0

        from libraries.domain.risk.analytics.var import _gaussian_quantile

        quantile = _gaussian_quantile(confidence_level)
        # Standard normal PDF at quantile.
        phi = math.exp(-0.5 * quantile * quantile) / math.sqrt(2.0 * math.pi)
        tail_probability = 1.0 - confidence_level

        one_day_cvar = mean_return - vol * phi / tail_probability
        one_day_var = mean_return + quantile * vol

        scale = math.sqrt(horizon_days)
        cvar_pct = max(0.0, -one_day_cvar * scale * 100.0)
        var_pct = max(0.0, -one_day_var * scale * 100.0)
        return cvar_pct, var_pct, 0

    # ─── Monte Carlo ────────────────────────────────────────────

    def _monte_carlo_cvar(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, int]:
        """Monte Carlo CVaR using simulated terminal returns."""
        mean_return = statistics.mean(returns)
        vol = statistics.pstdev(returns)
        simulations = 10_000

        if vol <= 0.0:
            return 0.0, 0.0, simulations

        rng = random.Random(self._random_seed)
        mu = mean_return
        sigma = vol

        terminal_returns: list[float] = []
        for _ in range(simulations):
            log_ret = 0.0
            for _ in range(horizon_days):
                z = rng.gauss(0.0, 1.0)
                log_ret += (mu - 0.5 * sigma * sigma) + sigma * z
            terminal_returns.append(math.exp(log_ret) - 1.0)

        terminal_returns.sort()
        tail_probability = 1.0 - confidence_level
        tail_count = max(1, math.ceil(tail_probability * len(terminal_returns)))
        tail = terminal_returns[:tail_count]
        var_pct = -terminal_returns[tail_count - 1] * 100.0
        cvar_pct = -statistics.mean(tail) * 100.0
        return cvar_pct, var_pct, simulations
