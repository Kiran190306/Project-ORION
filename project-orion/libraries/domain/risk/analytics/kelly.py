"""Kelly Criterion analytics engine.

Computes the optimal fraction of capital to risk per trade using the
Kelly formula::

    f* = p - (1 - p) / b

where ``p`` is the probability of a winning trade and ``b`` is the
average win/loss ratio.
"""

from __future__ import annotations

from libraries.domain.risk.analytics.models import KellyResult
from libraries.domain.risk.analytics.validation import (
    validate_positive_float,
    validate_probability,
)


class KellyCriterionEngine:
    """Computes the Kelly fraction and fractional variants."""

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
        p = validate_probability(win_probability)
        b = validate_positive_float(win_loss_ratio, "win_loss_ratio")

        # f* = p - (1 - p) / b
        fraction = p - (1.0 - p) / b

        # Edge = expected return per unit bet.
        edge = p * b - (1.0 - p)
        expected_return = edge

        half = fraction * 0.5
        quarter = fraction * 0.25

        return KellyResult(
            fraction=round(fraction, 6),
            win_probability=p,
            win_loss_ratio=b,
            expected_return_per_trade=round(expected_return, 6),
            edge=round(edge, 6),
            half_kelly_fraction=round(half, 6),
            quarter_kelly_fraction=round(quarter, 6),
        )

