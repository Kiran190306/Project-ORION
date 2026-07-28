"""Tests for cross_validation module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.cross_validation import CrossValidator
from libraries.domain.ai_research.exceptions import CrossValidationError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
)


def _make_dataset(rows: int = 100) -> ResearchDataset:
    return ResearchDataset(
        dataset_id="ds-1",
        schema=("value",),
        rows=tuple({"value": float(i)} for i in range(rows)),
    )


def _make_strategy() -> StrategyCandidate:
    return StrategyCandidate(strategy_id="s-1", name="Test")


def _make_evaluation() -> StrategyEvaluation:
    return StrategyEvaluation(strategy_id="s-1", dataset_id="ds-1", metrics={"sharpe": 1.5})


class TestCrossValidator:
    def test_validate_valid(self):
        validator = CrossValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(100),
                evaluation=_make_evaluation(),
                num_folds=5,
            )
        )
        assert result.num_folds == 5
        assert result.mean_score != 0.0

    def test_too_few_folds(self):
        validator = CrossValidator(min_folds=3)
        import asyncio

        with pytest.raises(CrossValidationError, match="num_folds must be at least"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(100),
                    evaluation=_make_evaluation(),
                    num_folds=2,
                )
            )

    def test_too_many_folds(self):
        validator = CrossValidator(max_folds=10)
        import asyncio

        with pytest.raises(CrossValidationError, match="num_folds must be at most"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(100),
                    evaluation=_make_evaluation(),
                    num_folds=20,
                )
            )

    def test_dataset_too_small(self):
        validator = CrossValidator()
        import asyncio

        with pytest.raises(CrossValidationError, match="dataset has"):
            asyncio.run(
                validator.validate(
                    strategy=_make_strategy(),
                    dataset=_make_dataset(5),
                    evaluation=_make_evaluation(),
                    num_folds=5,
                )
            )

    def test_cross_validation_fold_model(self):
        from libraries.domain.ai_research.models import CrossValidationFold

        fold = CrossValidationFold(
            fold_index=0,
            train_indices=(0, 1, 2, 3),
            test_indices=(4, 5),
            score=0.85,
        )
        assert fold.fold_index == 0
        assert fold.score == 0.85

    def test_cross_validation_result_model(self):
        from libraries.domain.ai_research.models import CrossValidationFold, CrossValidationResult

        fold = CrossValidationFold(fold_index=0, train_indices=(0, 1), test_indices=(2,), score=0.8)
        result = CrossValidationResult(folds=(fold,), mean_score=0.8, std_score=0.0)
        assert result.num_folds == 1
        assert result.mean_score == 0.8

    def test_fold_validation_empty_train(self):
        from libraries.domain.ai_research.models import CrossValidationFold

        with pytest.raises(ValueError, match="train_indices must not be empty"):
            CrossValidationFold(fold_index=0, train_indices=(), test_indices=(0,))

    def test_fold_validation_empty_test(self):
        from libraries.domain.ai_research.models import CrossValidationFold

        with pytest.raises(ValueError, match="test_indices must not be empty"):
            CrossValidationFold(fold_index=0, train_indices=(0,), test_indices=())

    def test_all_folds_have_indices(self):
        validator = CrossValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(100),
                evaluation=_make_evaluation(),
                num_folds=5,
            )
        )
        for fold in result.folds:
            assert len(fold.train_indices) > 0
            assert len(fold.test_indices) > 0

    def test_invalid_min_folds(self):
        with pytest.raises(CrossValidationError, match="min_folds must be at least 2"):
            CrossValidator(min_folds=1)

    def test_invalid_max_folds(self):
        with pytest.raises(CrossValidationError, match="max_folds must be at least min_folds"):
            CrossValidator(min_folds=5, max_folds=3)

    def test_result_immutable(self):
        validator = CrossValidator()
        import asyncio

        result = asyncio.run(
            validator.validate(
                strategy=_make_strategy(),
                dataset=_make_dataset(100),
                evaluation=_make_evaluation(),
                num_folds=5,
            )
        )
        with pytest.raises(AttributeError):
            result.mean_score = 1.0  # type: ignore[misc]
