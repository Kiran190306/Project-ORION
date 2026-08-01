"""Value at Risk analytics engine.

Implements three VaR methodologies:

- **Historical VaR**: percentile of historical returns.
- **Parametric VaR**: assumes normally distributed returns, using the
  Gaussian quantile and sample volatility.
- **Monte Carlo VaR**: simulates return paths under a geometric Brownian
  motion assumption using a seeded RNG for reproducibility.

All calculations are pure domain logic — no I/O, no infrastructure.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Sequence
from decimal import Decimal

from libraries.domain.risk.analytics.models import VaRMethod, VaRResult
from libraries.domain.risk.analytics.validation import (
    InvalidConfidenceLevelError,
    validate_confidence_level,
    validate_horizon,
    validate_returns,
)

# Standard normal quantiles at common confidence levels (tail probabilities).
_QUANTILES: dict[float, float] = {
    0.90: 1.2816,
    0.95: 1.6449,
    0.975: 1.9599,
    0.99: 2.3263,
    0.995: 2.5758,
}


def _gaussian_quantile(confidence_level: float) -> float:
    """Return the standard normal quantile for a confidence level.

    Uses a lookup table for common levels and a rational approximation
    (Acklam algorithm) otherwise.
    """
    for level, q in _QUANTILES.items():
        if abs(level - confidence_level) < 1e-6:
            return q

    # Acklam's algorithm for the inverse normal CDF (tail probability p).
    # We need z such that P(Z <= -z) = 1 - confidence_level, i.e.
    # the quantile q = -Phi^-1(1 - confidence_level).
    p = 1.0 - confidence_level
    if p <= 0.0 or p >= 1.0:
        raise InvalidConfidenceLevelError(
            f"confidence_level must be in (0, 1), got {confidence_level}"
        )

    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        num = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
        den = ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        return num / den
    if p > p_high:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        num = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
        den = ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        return -num / den
    q = p - 0.5
    r = q * q
    num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    den = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    return num / den


class ValueAtRiskEngine:
    """Computes Value at Risk using historical, parametric, or MC methods.

    Pure domain engine. The Monte Carlo implementation uses a seeded RNG
    so results are reproducible for a given seed.
    """

    def __init__(self, random_seed: int | None = 42) -> None:
        self._random_seed = random_seed

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
            method: VaR method.

        Returns:
            A VaRResult with ``var_pct`` expressed as a positive percentage.
        """
        validated = validate_returns(returns)
        level = validate_confidence_level(confidence_level)
        horizon = validate_horizon(horizon_days)

        if method == VaRMethod.HISTORICAL:
            var_pct, expected_return, vol = self._historical_var(
                validated, level, horizon
            )
            simulations = 0
        elif method == VaRMethod.PARAMETRIC:
            var_pct, expected_return, vol = self._parametric_var(
                validated, level, horizon
            )
            simulations = 0
        elif method == VaRMethod.MONTE_CARLO:
            var_pct, expected_return, vol, simulations = self._monte_carlo_var(
                validated, level, horizon
            )
        else:
            raise ValueError(f"Unsupported VaR method: {method}")

        var_amount: Decimal | None = None
        if portfolio_value is not None and portfolio_value > 0:
            var_amount = portfolio_value * (Decimal(str(var_pct)) / Decimal(100))

        return VaRResult(
            method=method,
            confidence_level=level,
            horizon_days=horizon,
            var_pct=round(var_pct, 6),
            var_amount=var_amount,
            expected_return=expected_return,
            volatility=vol,
            simulations=simulations,
        )

    # ─── Historical ─────────────────────────────────────────────

    def _historical_var(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, float]:
        """Historical VaR = percentile of the loss distribution."""
        # Sort returns ascending; the loss is the negative of the return.
        sorted_returns = sorted(returns)
        tail_probability = 1.0 - confidence_level
        index = int(tail_probability * len(sorted_returns))
        index = max(0, min(index, len(sorted_returns) - 1))
        one_day_var = -sorted_returns[index]

        # Scale by sqrt of horizon (i.i.d. returns assumption).
        scale = math.sqrt(horizon_days)
        var_pct = one_day_var * scale * 100.0

        mean_return = statistics.mean(returns)
        vol = statistics.pstdev(returns)
        expected_return = mean_return * horizon_days * 100.0
        return var_pct, expected_return, vol

    # ─── Parametric ─────────────────────────────────────────────

    def _parametric_var(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, float]:
        """Parametric VaR under a normal distribution assumption."""
        mean_return = statistics.mean(returns)
        vol = statistics.pstdev(returns)
        if vol <= 0.0:
            return 0.0, mean_return * horizon_days * 100.0, 0.0

        quantile = _gaussian_quantile(confidence_level)
        scale = math.sqrt(horizon_days)
        # VaR% = -(mu * horizon + quantile * sigma * sqrt(horizon))
        var_pct = -(mean_return * horizon_days + quantile * vol * scale) * 100.0
        var_pct = max(0.0, var_pct)
        expected_return = mean_return * horizon_days * 100.0
        return var_pct, expected_return, vol

    # ─── Monte Carlo ────────────────────────────────────────────

    def _monte_carlo_var(
        self,
        returns: list[float],
        confidence_level: float,
        horizon_days: int,
    ) -> tuple[float, float, float, int]:
        """Monte Carlo VaR via geometric Brownian motion simulation."""
        mean_return = statistics.mean(returns)
        vol = statistics.pstdev(returns)
        simulations = 10_000

        if vol <= 0.0:
            return 0.0, mean_return * horizon_days * 100.0, 0.0, simulations

        rng = random.Random(self._random_seed)
        # Daily drift and diffusion.
        mu = mean_return
        sigma = vol

        terminal_returns: list[float] = []
        for _ in range(simulations):
            log_ret = 0.0
            for _ in range(horizon_days):
                z = rng.gauss(0.0, 1.0)
                log_ret += (mu - 0.5 * sigma * sigma) + sigma * z
            # Approximate simple return from log return.
            simple_ret = math.exp(log_ret) - 1.0
            terminal_returns.append(simple_ret)

        terminal_returns.sort()
        tail_probability = 1.0 - confidence_level
        index = int(tail_probability * len(terminal_returns))
        index = max(0, min(index, len(terminal_returns) - 1))
        var_pct = -terminal_returns[index] * 100.0
        expected_return = mean_return * horizon_days * 100.0
        return var_pct, expected_return, vol, simulations

