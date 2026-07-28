"""Tests for fitness_engine module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import FitnessError
from libraries.domain.ai_research.fitness_engine import FitnessEngine
from libraries.domain.ai_research.models import (
    FitnessWeights,
    StrategyEvaluation,
)


def _make_evaluation(
    strategy_id: str = "strat-1",
    sharpe: float = 1.5,
    sortino: float = 1.2,
    calmar: float = 0.8,
    profit_factor: float = 2.0,
    expectancy: float = 0.3,
    max_drawdown: float = 15.0,
    recovery_factor: float = 1.5,
    win_rate: float = 0.6,
    risk_reward: float = 2.0,
) -> StrategyEvaluation:
    return StrategyEvaluation(
        strategy_id=strategy_id,
        dataset_id="ds-1",
        metrics={
            "sharpe": sharpe,
            "sortino": sortino,
            "calmar": calmar,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "max_drawdown": max_drawdown,
            "recovery_factor": recovery_factor,
            "win_rate": win_rate,
            "risk_reward": risk_reward,
        },
        evaluated_at=datetime.now(timezone.utc),
    )


class TestFitnessEngine:
    def test_calculate_default_weights(self):
        engine = FitnessEngine()
        evaluation = _make_evaluation()
        result = engine.calculate(evaluation)
        assert result.strategy_id == "strat-1"
        assert result.composite_score != 0.0
        assert len(result.component_scores) > 0

    def test_calculate_custom_weights(self):
        weights = FitnessWeights(sharpe=0.5, profit_factor=0.5)
        engine = FitnessEngine(weights=weights)
        evaluation = _make_evaluation()
        result = engine.calculate(evaluation)
        assert result.composite_score != 0.0

    def test_calculate_missing_metrics_uses_zero(self):
        engine = FitnessEngine()
        evaluation = StrategyEvaluation(
            strategy_id="strat-1",
            dataset_id="ds-1",
            metrics={"sharpe": 1.0},
            evaluated_at=datetime.now(timezone.utc),
        )
        result = engine.calculate(evaluation)
        assert result.composite_score != 0.0
        assert "sharpe" in result.component_scores

    def test_calculate_empty_metrics_raises_error(self):
        engine = FitnessEngine()
        with pytest.raises(ValueError, match="metrics must not be empty"):
            StrategyEvaluation(
                strategy_id="strat-1",
                dataset_id="ds-1",
                metrics={},
                evaluated_at=datetime.now(timezone.utc),
            )

    def test_calculate_with_sharpe_alias(self):
        engine = FitnessEngine()
        evaluation = StrategyEvaluation(
            strategy_id="strat-1",
            dataset_id="ds-1",
            metrics={"sharpe_ratio": 1.5, "profit_factor": 2.0},
            evaluated_at=datetime.now(timezone.utc),
        )
        result = engine.calculate(evaluation)
        assert result.composite_score != 0.0

    def test_calculate_with_max_drawdown_alias(self):
        engine = FitnessEngine()
        evaluation = StrategyEvaluation(
            strategy_id="strat-1",
            dataset_id="ds-1",
            metrics={"sharpe": 1.5, "drawdown": 10.0, "profit_factor": 2.0},
            evaluated_at=datetime.now(timezone.utc),
        )
        result = engine.calculate(evaluation)
        assert result.composite_score != 0.0

    def test_default_weights_values(self):
        weights = FitnessWeights()
        assert weights.sharpe == 0.25
        assert weights.sortino == 0.15
        assert weights.calmar == 0.10
        assert weights.profit_factor == 0.15
        assert weights.expectancy == 0.10
        assert weights.max_drawdown == -0.10
        assert weights.recovery_factor == 0.10
        assert weights.win_rate == 0.05
        assert weights.risk_reward == 0.10

    def test_custom_weights(self):
        weights = FitnessWeights(sharpe=0.5, profit_factor=0.5, win_rate=0.0, expectancy=0.0)
        assert weights.sharpe == 0.5
        assert weights.profit_factor == 0.5
        assert weights.win_rate == 0.0

    def test_fitness_result_validation(self):
        engine = FitnessEngine()
        evaluation = _make_evaluation()
        result = engine.calculate(evaluation)
        assert isinstance(result.composite_score, float)
        assert isinstance(result.component_scores, dict)

    def test_higher_metrics_give_higher_fitness(self):
        engine = FitnessEngine()
        low = engine.calculate(_make_evaluation(sharpe=0.5, profit_factor=1.2))
        high = engine.calculate(_make_evaluation(sharpe=2.5, profit_factor=4.0))
        assert high.composite_score > low.composite_score

    def test_drawdown_penalty(self):
        engine = FitnessEngine()
        low_dd = engine.calculate(_make_evaluation(max_drawdown=5.0))
        high_dd = engine.calculate(_make_evaluation(max_drawdown=40.0))
        assert low_dd.composite_score > high_dd.composite_score

    def test_fitness_results_immutable(self):
        engine = FitnessEngine()
        result = engine.calculate(_make_evaluation())
        with pytest.raises(AttributeError):
            result.composite_score = 0.0  # type: ignore[misc]

    def test_init_with_none_weights(self):
        engine = FitnessEngine(weights=None)
        assert engine.weights is not None
        assert engine.weights.sharpe == 0.25

    def test_calculate_batch(self):
        engine = FitnessEngine()
        evals = (
            _make_evaluation(strategy_id="s1", sharpe=1.0),
            _make_evaluation(strategy_id="s2", sharpe=2.0),
        )
        results = engine.calculate_batch(evals)
        assert len(results) == 2
        assert results[0].strategy_id == "s1"
        assert results[1].strategy_id == "s2"

    def test_calculate_batch_single(self):
        engine = FitnessEngine()
        results = engine.calculate_batch((_make_evaluation(),))
        assert len(results) == 1

    def test_calculate_with_risk_reward_alias(self):
        engine = FitnessEngine()
        evaluation = StrategyEvaluation(
            strategy_id="strat-1",
            dataset_id="ds-1",
            metrics={"sharpe": 1.5, "profit_factor": 2.0, "avg_win_avg_loss": 1.5},
            evaluated_at=datetime.now(timezone.utc),
        )
        result = engine.calculate(evaluation)
        assert result.composite_score != 0.0

    def test_win_rate_above_1_normalized(self):
        engine = FitnessEngine()
        evaluation = _make_evaluation(win_rate=75.0)
        result = engine.calculate(evaluation)
        assert result.composite_score is not None

    def test_negative_win_rate(self):
        engine = FitnessEngine()
        result = engine.calculate(_make_evaluation(win_rate=-0.5))
        assert result.composite_score is not None

    def test_calculate_batch_with_empty(self):
        engine = FitnessEngine()
        results = engine.calculate_batch(())
        assert len(results) == 0
