"""Tests for EPIC-011 CompositeStrategyRanker."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import RankingError
from libraries.domain.ai_research.models import LeaderboardEntry, StrategyEvaluation
from libraries.domain.ai_research.strategy_ranker import CompositeStrategyRanker


class TestCompositeStrategyRanker:
    """Test CompositeStrategyRanker."""

    @pytest.fixture
    def ranker(self):
        return CompositeStrategyRanker()

    @pytest.mark.asyncio
    async def test_rank_empty_evaluations(self, ranker):
        result = await ranker.rank([])
        assert result == ()

    @pytest.mark.asyncio
    async def test_rank_single_evaluation(self, ranker):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={"sharpe": 1.5, "win_rate": 60.0, "profit_factor": 2.0, "expectancy": 0.5},
        )
        result = await ranker.rank([evaluation])
        assert len(result) == 1
        assert result[0].rank == 1
        assert result[0].evaluation.strategy_id == "s1"

    @pytest.mark.asyncio
    async def test_rank_multiple_evaluations(self, ranker):
        evals = [
            StrategyEvaluation(
                strategy_id="s1",
                dataset_id="ds1",
                metrics={"sharpe": 2.0, "win_rate": 70.0, "profit_factor": 3.0, "expectancy": 1.0},
            ),
            StrategyEvaluation(
                strategy_id="s2",
                dataset_id="ds1",
                metrics={"sharpe": 1.0, "win_rate": 50.0, "profit_factor": 1.5, "expectancy": 0.3},
            ),
        ]
        result = await ranker.rank(evals)
        assert len(result) == 2
        # s1 has higher composite score, should be rank 1
        assert result[0].rank == 1
        assert result[0].evaluation.strategy_id == "s1"
        assert result[1].rank == 2

    @pytest.mark.asyncio
    async def test_rank_duplicate_strategy_ids_raises_error(self, ranker):
        evals = [
            StrategyEvaluation(
                strategy_id="s1",
                dataset_id="ds1",
                metrics={"sharpe": 1.0, "win_rate": 50.0, "profit_factor": 1.5, "expectancy": 0.3},
            ),
            StrategyEvaluation(
                strategy_id="s1",
                dataset_id="ds1",
                metrics={"sharpe": 2.0, "win_rate": 60.0, "profit_factor": 2.0, "expectancy": 0.5},
            ),
        ]
        with pytest.raises(RankingError, match="one evaluation per strategy"):
            await ranker.rank(evals)

    def test_composite_score_formula(self, ranker):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={
                "sharpe": 2.0,
                "profit_factor": 3.0,
                "win_rate": 60.0,
                "expectancy": 0.5,
                "drawdown": -0.1,
            },
        )
        # Expected: (2.0 * 0.35) + (3.0 * 0.25) + (0.6 * 0.15) + (0.5 * 0.15) - (0.1 * 0.10)
        # = 0.7 + 0.75 + 0.09 + 0.075 - 0.01 = 1.605
        score = ranker.composite_score(evaluation)
        assert score == pytest.approx(1.605)

    def test_composite_score_with_max_drawdown_alias(self, ranker):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={
                "sharpe_ratio": 1.5,
                "profit_factor": 2.0,
                "win_rate": 0.6,
                "expectancy": 0.4,
                "max_drawdown": 0.15,
            },
        )
        score = ranker.composite_score(evaluation)
        # (1.5 * 0.35) + (2.0 * 0.25) + (0.6 * 0.15) + (0.4 * 0.15) - (0.15 * 0.10)
        # = 0.525 + 0.5 + 0.09 + 0.06 - 0.015 = 1.16
        assert score == pytest.approx(1.16)

    def test_composite_score_normalizes_win_rate_greater_than_1(self, ranker):
        evaluation = StrategyEvaluation(
            strategy_id="s1",
            dataset_id="ds1",
            metrics={
                "sharpe": 1.0,
                "profit_factor": 1.0,
                "win_rate": 80.0,  # > 1, should be normalized to 0.8
                "expectancy": 0.0,
            },
        )
        score = ranker.composite_score(evaluation)
        expected = (1.0 * 0.35) + (1.0 * 0.25) + (0.8 * 0.15) + (0.0 * 0.15) - (0.0 * 0.10)
        assert score == pytest.approx(expected)

    @pytest.mark.asyncio
    async def test_rank_with_tie_breaker(self, ranker):
        """When scores are equal, tie-break by strategy_id alphabetical."""
        evals = [
            StrategyEvaluation(
                strategy_id="b",
                dataset_id="ds1",
                metrics={"sharpe": 1.0, "win_rate": 50.0, "profit_factor": 1.0, "expectancy": 0.0},
            ),
            StrategyEvaluation(
                strategy_id="a",
                dataset_id="ds1",
                metrics={"sharpe": 1.0, "win_rate": 50.0, "profit_factor": 1.0, "expectancy": 0.0},
            ),
        ]
        result = await ranker.rank(evals)
        # Both have same score, s1 < s2 alphabetically, so s1 is rank 1
        assert result[0].evaluation.strategy_id == "a"
        assert result[1].evaluation.strategy_id == "b"
