"""Tests for walk_forward_validator module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import WalkForwardError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
)
from libraries.domain.ai_research.walk_forward_validator import WalkForwardValidator


def _make_dataset(rows: int = 500) -> ResearchDataset:
    return ResearchDataset(
        dataset_id="ds-1",
        schema=("timestamp", "close", "high", "low"),
        rows=tuple(
            {
                "timestamp": datetime.now(timezone.utc),
                "close": 100.0 + i,
                "high": 101.0 + i,
                "low": 99.0 + i,
            }
            for i in range(rows)
        ),
    )


def _make_strategy() -> StrategyCandidate:
    return StrategyCandidate(strategy_id="s-1", name="Test Strategy", version="1.0.0")


def _make_evaluation() -> StrategyEvaluation:
    return StrategyEvaluation(
        strategy_id="s-1",
        dataset_id="ds-1",
        metrics={"sharpe": 1.5, "profit_factor": 2.0},
        evaluated_at=datetime.now(timezone.utc),
    )


class TestWalkForwardValidator:
    def test_validate_valid(self):
        validator = WalkForwardValidator()
        result = pytest.mark.asyncio
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(500),
                evaluation=_make_evaluation(),
                train_size=200,
                test_size=50,
            )
        )
        assert result.num_windows > 0
        assert result.robustness_score >= 0.0

    def test_too_small_dataset(self):
        validator = WalkForwardValidator()
        import asyncio

        with pytest.raises(WalkForwardError, match="dataset has"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(50),
                    evaluation=_make_evaluation(),
                    train_size=200,
                    test_size=50,
                )
            )

    def test_invalid_train_size(self):
        validator = WalkForwardValidator(min_train_size=100)
        import asyncio

        with pytest.raises(WalkForwardError, match="train_size must be at least"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(500),
                    evaluation=_make_evaluation(),
                    train_size=10,
                    test_size=50,
                )
            )

    def test_invalid_test_size(self):
        validator = WalkForwardValidator(min_test_size=20)
        import asyncio

        with pytest.raises(WalkForwardError, match="test_size must be at least"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(500),
                    evaluation=_make_evaluation(),
                    train_size=200,
                    test_size=5,
                )
            )

    def test_negative_step_size(self):
        validator = WalkForwardValidator()
        import asyncio

        with pytest.raises(WalkForwardError, match="step_size must be positive"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(500),
                    evaluation=_make_evaluation(),
                    train_size=200,
                    test_size=50,
                    step_size=-1,
                )
            )

    def test_invalid_min_train_size(self):
        with pytest.raises(WalkForwardError, match="min_train_size must be positive"):
            WalkForwardValidator(min_train_size=0)

    def test_invalid_min_test_size(self):
        with pytest.raises(WalkForwardError, match="min_test_size must be positive"):
            WalkForwardValidator(min_test_size=0)

    def test_custom_step_size(self):
        validator = WalkForwardValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(500),
                evaluation=_make_evaluation(),
                train_size=200,
                test_size=50,
                step_size=100,
            )
        )
        assert result.num_windows > 0

    def test_robustness_score_range(self):
        validator = WalkForwardValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(500),
                evaluation=_make_evaluation(),
                train_size=200,
                test_size=50,
            )
        )
        assert 0.0 <= result.robustness_score <= 1.0

    def test_walk_forward_result_immutable(self):
        validator = WalkForwardValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(500),
                evaluation=_make_evaluation(),
                train_size=200,
                test_size=50,
            )
        )
        with pytest.raises(AttributeError):
            result.robustness_score = 0.5  # type: ignore[misc]
