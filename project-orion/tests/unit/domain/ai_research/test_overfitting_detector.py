"""Tests for overfitting_detector module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.ai_research.exceptions import OverfittingError
from libraries.domain.ai_research.models import (
    StrategyEvaluation,
    WalkForwardResult,
    WalkForwardWindow,
)
from libraries.domain.ai_research.overfitting_detector import OverfittingDetector


def _make_evaluation(**overrides) -> StrategyEvaluation:
    metrics = {
        "sharpe": 1.5,
        "profit_factor": 2.0,
        "win_rate": 0.6,
        "max_drawdown": 15.0,
    }
    metrics.update(overrides)
    return StrategyEvaluation(
        strategy_id="s-1",
        dataset_id="ds-1",
        metrics=metrics,
        evaluated_at=datetime.now(timezone.utc),
    )


def _make_walk_forward(robustness: float = 0.8) -> WalkForwardResult:
    return WalkForwardResult(
        windows=(
            WalkForwardWindow(
                window_index=0,
                train_start=0,
                train_end=100,
                test_start=100,
                test_end=120,
                train_metrics={"sharpe": 2.0},
                test_metrics={"sharpe": 2.0 * robustness},
            ),
        ),
        robustness_score=robustness,
    )


class TestOverfittingDetector:
    def test_detect_no_overfitting(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation()))
        assert report.strategy_id == "s-1"
        assert report.is_overfit is False
        assert len(report.reasons) == 0

    def test_detect_high_sharpe(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation(sharpe=5.0)))
        assert report.is_overfit is True
        assert any("Sharpe" in r for r in report.reasons)

    def test_detect_high_win_rate(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation(win_rate=0.99)))
        assert report.is_overfit is True
        assert any("win rate" in r for r in report.reasons)

    def test_detect_high_profit_factor(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation(profit_factor=20.0)))
        assert report.is_overfit is True
        assert any("profit factor" in r for r in report.reasons)

    def test_detect_with_walk_forward(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(
            detector.detect(_make_evaluation(sharpe=3.5), _make_walk_forward(robustness=0.3))
        )
        assert report.is_overfit is True

    def test_empty_metrics_raises_error(self):
        detector = OverfittingDetector()
        with pytest.raises(ValueError, match="metrics must not be empty"):
            StrategyEvaluation(
                strategy_id="s-1",
                dataset_id="ds-1",
                metrics={},
                evaluated_at=datetime.now(timezone.utc),
            )

    def test_indicators_present(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation(sharpe=2.5, profit_factor=5.0)))
        assert "sharpe_ratio" in report.indicators
        assert "profit_factor" in report.indicators

    def test_win_rate_normalized(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation(win_rate=98.0)))
        assert report.is_overfit is True

    def test_overfitting_report_immutable(self):
        detector = OverfittingDetector()
        import asyncio

        report = asyncio.run(detector.detect(_make_evaluation()))
        with pytest.raises(AttributeError):
            report.is_overfit = True  # type: ignore[misc]
