"""Deterministic ranking based on the Sprint-1 evaluation metrics."""

from __future__ import annotations

from collections.abc import Sequence

from libraries.domain.ai_research.exceptions import RankingError
from libraries.domain.ai_research.models import LeaderboardEntry, StrategyEvaluation


class CompositeStrategyRanker:
    """Ranks Sharpe, drawdown, profit factor, win rate, and expectancy."""

    async def rank(self, evaluations: Sequence[StrategyEvaluation]) -> tuple[LeaderboardEntry, ...]:
        if not evaluations:
            return ()
        if len({item.strategy_id for item in evaluations}) != len(evaluations):
            raise RankingError("only one evaluation per strategy may be ranked")
        ordered = sorted(
            evaluations, key=lambda item: (-self.composite_score(item), item.strategy_id)
        )
        return tuple(
            LeaderboardEntry(
                rank=index, evaluation=evaluation, composite_score=self.composite_score(evaluation)
            )
            for index, evaluation in enumerate(ordered, start=1)
        )

    @staticmethod
    def composite_score(evaluation: StrategyEvaluation) -> float:
        metrics = evaluation.metrics
        win_rate = metrics.get("win_rate", 0.0)
        normalized_win_rate = win_rate / 100.0 if win_rate > 1.0 else win_rate
        return (
            (metrics.get("sharpe", metrics.get("sharpe_ratio", 0.0)) * 0.35)
            + (metrics.get("profit_factor", 0.0) * 0.25)
            + (normalized_win_rate * 0.15)
            + (metrics.get("expectancy", 0.0) * 0.15)
            - (abs(metrics.get("drawdown", metrics.get("max_drawdown", 0.0))) * 0.10)
        )


StrategyRanker = CompositeStrategyRanker
