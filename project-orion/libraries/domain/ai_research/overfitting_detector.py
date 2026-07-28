"""Overfitting detection for AI research strategies.

Analyzes evaluation metrics to detect potential overfitting indicators.
Does NOT execute trades or communicate with brokers.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import OverfittingError
from libraries.domain.ai_research.models import (
    OverfittingReport,
    StrategyEvaluation,
    WalkForwardResult,
)


class OverfittingDetector:
    """Detects potential overfitting in strategy evaluations.

    Uses multiple indicators:
    - Unusually high Sharpe ratio (>3.0)
    - Perfect or near-perfect win rate
    - Extremely high profit factor
    - Large gap between in-sample and out-of-sample performance
    """

    async def detect(
        self,
        evaluation: StrategyEvaluation,
        walk_forward_result: WalkForwardResult | None = None,
    ) -> OverfittingReport:
        """Detect overfitting indicators in a strategy evaluation.

        Args:
            evaluation: The strategy evaluation to analyze.
            walk_forward_result: Optional walk-forward result for in/out-of-sample comparison.

        Returns:
            OverfittingReport with indicators and reasons.

        Raises:
            OverfittingError: If evaluation has no metrics.
        """
        if not evaluation.metrics:
            raise OverfittingError("evaluation has no metrics to analyze")

        indicators: dict[str, float] = {}
        reasons: list[str] = []

        # Indicator 1: Sharpe ratio too high
        sharpe = evaluation.metrics.get("sharpe", evaluation.metrics.get("sharpe_ratio", 0.0))
        indicators["sharpe_ratio"] = sharpe
        if sharpe > 3.0:
            reasons.append(f"unusually high Sharpe ratio: {sharpe:.2f}")

        # Indicator 2: Win rate too high
        win_rate = evaluation.metrics.get("win_rate", 0.0)
        normalized_win_rate = win_rate / 100.0 if win_rate > 1.0 else win_rate
        indicators["win_rate"] = normalized_win_rate
        if normalized_win_rate > 0.95:
            reasons.append(f"unusually high win rate: {normalized_win_rate:.2%}")

        # Indicator 3: Profit factor too high
        profit_factor = evaluation.metrics.get("profit_factor", 0.0)
        indicators["profit_factor"] = profit_factor
        if profit_factor > 10.0:
            reasons.append(f"unusually high profit factor: {profit_factor:.2f}")

        # Indicator 4: Walk-forward robustness gap
        if walk_forward_result is not None:
            robustness = walk_forward_result.robustness_score
            indicators["robustness_score"] = robustness
            if robustness < 0.5:
                reasons.append(
                    f"low walk-forward robustness: {robustness:.2f} (possible overfitting)"
                )

        # Determine if overfit
        is_overfit = len(reasons) >= 1

        return OverfittingReport(
            strategy_id=evaluation.strategy_id,
            is_overfit=is_overfit,
            indicators=indicators,
            reasons=tuple(reasons),
        )
