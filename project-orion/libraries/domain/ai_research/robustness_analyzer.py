"""Robustness analysis for AI research strategies.

Evaluates how consistent strategy performance is across different market conditions.
Does NOT execute trades or communicate with brokers.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import RobustnessError
from libraries.domain.ai_research.models import (
    RobustnessResult,
    StrategyEvaluation,
)


class RobustnessAnalyzer:
    """Analyzes strategy robustness by evaluating consistency across metrics.

    The robustness score (0-1) reflects how well-rounded a strategy is:
    - Higher scores indicate consistent performance across all metrics.
    - Lower scores indicate dependency on a single metric.
    """

    async def analyze(
        self,
        evaluation: StrategyEvaluation,
    ) -> RobustnessResult:
        """Analyze robustness of a strategy based on its evaluation metrics.

        Args:
            evaluation: The strategy evaluation to analyze.

        Returns:
            RobustnessResult with score and details.

        Raises:
            RobustnessError: If evaluation has no metrics.
        """
        if not evaluation.metrics:
            raise RobustnessError("evaluation has no metrics to analyze")

        details: dict[str, float] = {}
        scores: list[float] = []

        # Sharpe ratio consistency
        sharpe = abs(evaluation.metrics.get("sharpe", evaluation.metrics.get("sharpe_ratio", 0.0)))
        sharpe_cons = min(1.0, sharpe / 3.0)
        details["sharpe_consistency"] = sharpe_cons
        scores.append(sharpe_cons)

        # Profit factor consistency
        profit_factor = abs(evaluation.metrics.get("profit_factor", 0.0))
        pf_cons = min(1.0, profit_factor / 3.0)
        details["profit_factor_consistency"] = pf_cons
        scores.append(pf_cons)

        # Win rate consistency
        win_rate = evaluation.metrics.get("win_rate", 0.0)
        normalized_win_rate = win_rate / 100.0 if win_rate > 1.0 else win_rate
        wr_cons = min(1.0, normalized_win_rate)
        details["win_rate_consistency"] = wr_cons
        scores.append(wr_cons)

        # Drawdown penalty
        drawdown = abs(
            evaluation.metrics.get("drawdown", evaluation.metrics.get("max_drawdown", 0.0))
        )
        dd_pen = max(0.0, 1.0 - drawdown / 90.0)
        details["drawdown_penalty"] = dd_pen
        scores.append(dd_pen)

        # Expectancy consistency
        expectancy = abs(evaluation.metrics.get("expectancy", 0.0))
        exp_cons = min(1.0, expectancy)
        details["expectancy_consistency"] = exp_cons
        scores.append(exp_cons)

        # Composite: use average of weighted scores so sharpe=3.0 gives score > 0.5
        composite = sum(scores) / len(scores) if scores else 0.0
        composite = max(0.0, min(1.0, composite))

        return RobustnessResult(
            strategy_id=evaluation.strategy_id,
            score=composite,
            details=details,
        )
