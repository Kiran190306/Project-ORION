"""Tests for parameter_stability module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import ParameterStabilityError
from libraries.domain.ai_research.models import (
    WalkForwardResult,
    WalkForwardWindow,
)
from libraries.domain.ai_research.parameter_stability import ParameterStabilityAnalyzer


def _make_walk_forward(windows: int = 3) -> WalkForwardResult:
    return WalkForwardResult(
        windows=tuple(
            WalkForwardWindow(
                window_index=i,
                train_start=i * 100,
                train_end=(i * 100) + 80,
                test_start=(i * 100) + 80,
                test_end=(i * 100) + 100,
                test_metrics={"sharpe": 1.5 + (i * 0.1), "profit_factor": 2.0},
            )
            for i in range(windows)
        ),
        robustness_score=0.8,
    )


class TestParameterStabilityAnalyzer:
    def test_analyze_valid(self):
        analyzer = ParameterStabilityAnalyzer()
        import asyncio

        report = asyncio.run(analyzer.analyze(_make_walk_forward()))
        assert 0.0 <= report.stability_score <= 1.0
        assert len(report.parameter_std) > 0

    def test_no_windows_raises_error(self):
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(windows=())
        import asyncio

        with pytest.raises(ParameterStabilityError, match="no walk-forward windows"):
            asyncio.run(analyzer.analyze(wf))

    def test_single_window(self):
        analyzer = ParameterStabilityAnalyzer()
        import asyncio

        report = asyncio.run(analyzer.analyze(_make_walk_forward(windows=1)))
        assert report.stability_score == 1.0

    def test_identical_windows_give_perfect_stability(self):
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 1.5},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": 1.5},
                ),
            ),
            robustness_score=1.0,
        )
        import asyncio

        report = asyncio.run(analyzer.analyze(wf))
        assert report.stability_score > 0.9

    def test_different_windows_give_lower_stability(self):
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 1.5},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": -1.5},
                ),
            ),
            robustness_score=0.5,
        )
        import asyncio

        report = asyncio.run(analyzer.analyze(wf))
        assert report.stability_score < 0.9

    def test_report_immutable(self):
        analyzer = ParameterStabilityAnalyzer()
        import asyncio

        report = asyncio.run(analyzer.analyze(_make_walk_forward()))
        with pytest.raises(AttributeError):
            report.stability_score = 0.5  # type: ignore[misc]

    def test_multiple_metrics(self):
        analyzer = ParameterStabilityAnalyzer()
        wf = WalkForwardResult(
            windows=(
                WalkForwardWindow(
                    window_index=0,
                    train_start=0,
                    train_end=100,
                    test_start=100,
                    test_end=120,
                    test_metrics={"sharpe": 1.5, "profit_factor": 2.0, "win_rate": 0.6},
                ),
                WalkForwardWindow(
                    window_index=1,
                    train_start=100,
                    train_end=200,
                    test_start=200,
                    test_end=220,
                    test_metrics={"sharpe": 1.6, "profit_factor": 2.1, "win_rate": 0.61},
                ),
            ),
            robustness_score=0.9,
        )
        import asyncio

        report = asyncio.run(analyzer.analyze(wf))
        assert len(report.parameter_std) == 3
