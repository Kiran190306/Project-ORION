"""Tests for robustness_analyzer module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.models import StrategyEvaluation
from libraries.domain.ai_research.robustness_analyzer import RobustnessAnalyzer


def _make_evaluation(**overrides) -> StrategyEvaluation:
    metrics = {
        "sharpe": 1.5,
        "profit_factor": 2.0,
        "win_rate": 0.6,
        "max_drawdown": 15.0,
        "expectancy": 0.3,
    }
    metrics.update(overrides)
    return StrategyEvaluation(
        strategy_id="s-1",
        dataset_id="ds-1",
        metrics=metrics,
        evaluated_at=datetime.now(timezone.utc),
    )


class TestRobustnessAnalyzer:
    def test_analyze_valid(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation()))
        assert result.strategy_id == "s-1"
        assert 0.0 <= result.score <= 1.0
        assert len(result.details) > 0

    def test_empty_metrics_raises_error(self):
        analyzer = RobustnessAnalyzer()
        with pytest.raises(ValueError, match="metrics must not be empty"):
            StrategyEvaluation(
                strategy_id="s-1",
                dataset_id="ds-1",
                metrics={},
                evaluated_at=datetime.now(timezone.utc),
            )

    def test_high_sharpe_gives_high_robustness(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation(sharpe=3.0)))
        assert result.score > 0.5

    def test_low_sharpe_gives_lower_robustness(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation(sharpe=0.1)))
        assert result.score < 0.5

    def test_high_drawdown_penalizes(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation(max_drawdown=50.0)))
        assert result.details["drawdown_penalty"] < 0.5

    def test_low_drawdown_no_penalty(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation(max_drawdown=5.0)))
        assert result.details["drawdown_penalty"] > 0.9

    def test_robustness_result_immutable(self):
        analyzer = RobustnessAnalyzer()
        import asyncio

        result = asyncio.run(analyzer.analyze(_make_evaluation()))
        with pytest.raises(AttributeError):
            result.score = 0.5  # type: ignore[misc]

    def test_analyze_with_sharpe_alias(self):
        analyzer = RobustnessAnalyzer()
        evaluation = StrategyEvaluation(
            strategy_id="s-1",
            dataset_id="ds-1",
            metrics={"sharpe_ratio": 2.0, "profit_factor": 3.0, "win_rate": 0.7, "expectancy": 0.5},
            evaluated_at=datetime.now(timezone.utc),
        )
        import asyncio

        result = asyncio.run(analyzer.analyze(evaluation))
        assert 0.0 <= result.score <= 1.0
