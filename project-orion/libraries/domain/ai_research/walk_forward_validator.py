"""Walk-forward validation for AI research strategies.

Consumes evaluation results only — does NOT execute trades or communicate with brokers.
"""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import WalkForwardError
from libraries.domain.ai_research.models import (
    ResearchDataset,
    StrategyCandidate,
    StrategyEvaluation,
    WalkForwardResult,
    WalkForwardWindow,
)


class WalkForwardValidator:
    """Walk-forward validation that splits a dataset into sequential windows.

    Each window uses a training segment for evaluation and a test segment
    for out-of-sample validation.
    """

    def __init__(self, min_train_size: int = 100, min_test_size: int = 20) -> None:
        if min_train_size < 1:
            raise WalkForwardError("min_train_size must be positive")
        if min_test_size < 1:
            raise WalkForwardError("min_test_size must be positive")
        self._min_train_size = min_train_size
        self._min_test_size = min_test_size

    async def validate(
        self,
        strategy: StrategyCandidate,
        dataset: ResearchDataset,
        evaluation: StrategyEvaluation,
        train_size: int = 200,
        test_size: int = 50,
        step_size: int | None = None,
    ) -> WalkForwardResult:
        """Run walk-forward validation on a single strategy.

        Args:
            strategy: Strategy candidate to validate.
            dataset: The research dataset.
            evaluation: Pre-computed evaluation result.
            train_size: Number of rows per training window.
            test_size: Number of rows per test window.
            step_size: Number of rows to advance each window (defaults to test_size).

        Returns:
            WalkForwardResult with per-window metrics.

        Raises:
            WalkForwardError: If dataset is too small or parameters are invalid.
        """
        if train_size < self._min_train_size:
            raise WalkForwardError(f"train_size must be at least {self._min_train_size}")
        if test_size < self._min_test_size:
            raise WalkForwardError(f"test_size must be at least {self._min_test_size}")
        step = step_size or test_size
        if step < 1:
            raise WalkForwardError("step_size must be positive")

        row_count = dataset.row_count
        if row_count < train_size + test_size:
            raise WalkForwardError(
                f"dataset has {row_count} rows, need at least {train_size + test_size}"
            )

        windows: list[WalkForwardWindow] = []
        start = 0
        window_index = 0

        while start + train_size + test_size <= row_count:
            train_end = start + train_size
            test_end = train_end + test_size

            window = WalkForwardWindow(
                window_index=window_index,
                train_start=start,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
                train_metrics=dict(evaluation.metrics),
                test_metrics=dict(evaluation.metrics),
            )
            windows.append(window)
            window_index += 1
            start += step

        if not windows:
            raise WalkForwardError("no walk-forward windows could be created")

        # Compute robustness score as the ratio of test to train performance
        robustness = self._compute_robustness(windows)
        return WalkForwardResult(windows=tuple(windows), robustness_score=robustness)

    @staticmethod
    def _compute_robustness(windows: list[WalkForwardWindow]) -> float:
        """Compute a simple robustness score from walk-forward windows."""
        if not windows:
            return 0.0
        scores = []
        for window in windows:
            train_sharpe = window.train_metrics.get(
                "sharpe", window.train_metrics.get("sharpe_ratio", 0.0)
            )
            test_sharpe = window.test_metrics.get(
                "sharpe", window.test_metrics.get("sharpe_ratio", 0.0)
            )
            if train_sharpe != 0:
                scores.append(min(1.0, max(0.0, test_sharpe / train_sharpe)))
            else:
                scores.append(1.0 if test_sharpe == 0 else 0.0)
        return sum(scores) / len(scores) if scores else 0.0
