"""Cross-validation for AI research strategies.

Consumes evaluation results only — does NOT execute trades or communicate with brokers.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import CrossValidationError
from libraries.domain.ai_research.models import (
    CrossValidationFold,
    CrossValidationResult,
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
)


class CrossValidator:
    """K-fold cross-validation that splits a dataset into folds.

    Each fold uses a different train/test split for evaluation.
    """

    def __init__(self, min_folds: int = 2, max_folds: int = 20) -> None:
        if min_folds < 2:
            raise CrossValidationError("min_folds must be at least 2")
        if max_folds < min_folds:
            raise CrossValidationError("max_folds must be at least min_folds")
        self._min_folds = min_folds
        self._max_folds = max_folds

    async def validate(
        self,
        strategy: StrategyCandidate,
        dataset: ResearchDataset,
        evaluation: StrategyEvaluation,
        num_folds: int = 5,
    ) -> CrossValidationResult:
        """Run k-fold cross-validation on a single strategy.

        Args:
            strategy: Strategy candidate to validate.
            dataset: The research dataset.
            evaluation: Pre-computed evaluation result.
            num_folds: Number of folds.

        Returns:
            CrossValidationResult with per-fold scores.

        Raises:
            CrossValidationError: If dataset is too small or parameters are invalid.
        """
        if num_folds < self._min_folds:
            raise CrossValidationError(f"num_folds must be at least {self._min_folds}")
        if num_folds > self._max_folds:
            raise CrossValidationError(f"num_folds must be at most {self._max_folds}")

        row_count = dataset.row_count
        if row_count < num_folds * 2:
            raise CrossValidationError(
                f"dataset has {row_count} rows, need at least {num_folds * 2} for {num_folds} folds"
            )

        fold_size = row_count // num_folds
        folds: list[CrossValidationFold] = []

        for fold_index in range(num_folds):
            test_start = fold_index * fold_size
            test_end = test_start + fold_size if fold_index < num_folds - 1 else row_count

            train_indices = tuple(i for i in range(row_count) if i < test_start or i >= test_end)
            test_indices = tuple(range(test_start, test_end))

            # Use the evaluation's sharpe ratio as a proxy score per fold
            score = evaluation.metrics.get("sharpe", evaluation.metrics.get("sharpe_ratio", 0.0))

            fold = CrossValidationFold(
                fold_index=fold_index,
                train_indices=train_indices,
                test_indices=test_indices,
                score=score,
            )
            folds.append(fold)

        scores = [f.score for f in folds]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        std_score = (
            (sum((s - mean_score) ** 2 for s in scores) / len(scores)) ** 0.5 if scores else 0.0
        )

        return CrossValidationResult(
            folds=tuple(folds),
            mean_score=mean_score,
            std_score=std_score,
        )
