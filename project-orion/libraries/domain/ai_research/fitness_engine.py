"""Composite fitness scoring engine using configurable weighting."""

from __future__ import annotations

from math import isfinite

from libraries.domain.ai_research.exceptions import FitnessError
from libraries.domain.ai_research.models import FitnessResult, FitnessWeights, StrategyEvaluation


class CompositeFitnessEngine:
    """Computes composite fitness from strategy evaluation metrics.

    Combines Sharpe, Sortino, Calmar, Profit Factor, Expectancy,
    Max Drawdown, Recovery Factor, Win Rate, and Risk/Reward
    using configurable weighting.

    No strategy execution. No broker communication.
    """

    def __init__(self, weights: FitnessWeights | None = None) -> None:
        self._weights = weights or FitnessWeights()

    @property
    def weights(self) -> FitnessWeights:
        return self._weights

    def calculate(self, evaluation: StrategyEvaluation) -> FitnessResult:
        """Compute composite fitness for a single evaluation.

        Args:
            evaluation: Strategy evaluation with metrics.

        Returns:
            Fitness result with composite and component scores.
        """
        metrics = evaluation.metrics
        if not metrics:
            raise FitnessError("evaluation has no metrics")

        w = self._weights

        components: dict[str, float] = {}

        # Metric extraction with fallbacks
        sharpe = metrics.get("sharpe", metrics.get("sharpe_ratio", 0.0))
        sortino = metrics.get("sortino", metrics.get("sortino_ratio", 0.0))
        calmar = metrics.get("calmar", metrics.get("calmar_ratio", 0.0))
        profit_factor = metrics.get("profit_factor", 0.0)
        expectancy = metrics.get("expectancy", 0.0)
        max_dd = abs(metrics.get("max_drawdown", metrics.get("drawdown", 0.0)))
        recovery_factor = metrics.get("recovery_factor", 0.0)
        win_rate = metrics.get("win_rate", 0.0)
        risk_reward = metrics.get("risk_reward", metrics.get("avg_win_avg_loss", 0.0))

        # Compute component scores
        components["sharpe"] = self._clamp(sharpe) * w.sharpe
        components["sortino"] = self._clamp(sortino) * w.sortino
        components["calmar"] = self._clamp(calmar) * w.calmar
        components["profit_factor"] = self._cap(profit_factor - 1.0, 5.0) * w.profit_factor
        components["expectancy"] = self._clamp(expectancy) * w.expectancy
        components["max_drawdown"] = self._cap(max_dd, 50.0) * w.max_drawdown
        components["recovery_factor"] = self._clamp(recovery_factor) * w.recovery_factor
        components["win_rate"] = self._normalize_win_rate(win_rate) * w.win_rate
        components["risk_reward"] = self._clamp(risk_reward) * w.risk_reward

        # Validate intermediate values
        for name, value in components.items():
            if not isfinite(value):
                raise FitnessError(f"non-finite component score for '{name}'")

        composite = sum(components.values())
        if not isfinite(composite):
            raise FitnessError("non-finite composite score")

        return FitnessResult(
            strategy_id=evaluation.strategy_id,
            composite_score=round(composite, 6),
            component_scores={k: round(v, 6) for k, v in components.items()},
        )

    def calculate_batch(
        self, evaluations: tuple[StrategyEvaluation, ...]
    ) -> tuple[FitnessResult, ...]:
        """Compute fitness for multiple evaluations.

        Args:
            evaluations: Strategy evaluations to score.

        Returns:
            Tuple of fitness results.
        """
        results = []
        for evaluation in evaluations:
            result = self.calculate(evaluation)
            results.append(result)
        return tuple(results)

    @staticmethod
    def _clamp(value: float, max_val: float = 10.0) -> float:
        """Clamp a metric to a reasonable range."""
        if not isfinite(value):
            return 0.0
        return max(min(value, max_val), -max_val)

    @staticmethod
    def _cap(value: float, max_val: float) -> float:
        """Cap a positive value."""
        if not isfinite(value):
            return 0.0
        return min(max(value, 0.0), max_val)

    @staticmethod
    def _normalize_win_rate(win_rate: float) -> float:
        """Normalize win rate to 0.0-1.0 range."""
        if not isfinite(win_rate):
            return 0.0
        if win_rate > 1.0:
            return win_rate / 100.0
        return max(min(win_rate, 1.0), 0.0)


FitnessEngine = CompositeFitnessEngine
