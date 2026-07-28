"""Tests for EPIC-010 WalkForwardAnalyzer."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from libraries.domain.backtesting.models import WalkForwardConfig, WalkForwardResult
from libraries.domain.backtesting.walk_forward import WalkForwardAnalyzer, WalkForwardWindow


class TestWalkForwardWindow:
    """Test WalkForwardWindow dataclass."""

    def test_window_defaults(self):
        window = WalkForwardWindow(
            window_index=0,
            train_start=date(2023, 1, 1),
            train_end=date(2023, 6, 30),
            val_start=date(2023, 7, 1),
            val_end=date(2023, 9, 30),
        )
        assert window.window_index == 0
        assert window.is_anchored is False

    def test_anchored_window(self):
        window = WalkForwardWindow(
            window_index=0,
            train_start=date(2023, 1, 1),
            train_end=date(2023, 6, 30),
            val_start=date(2023, 7, 1),
            val_end=date(2023, 9, 30),
            is_anchored=True,
        )
        assert window.is_anchored is True

    def test_window_dates(self):
        window = WalkForwardWindow(
            window_index=1,
            train_start=date(2023, 1, 1),
            train_end=date(2023, 3, 31),
            val_start=date(2023, 4, 1),
            val_end=date(2023, 6, 30),
        )
        assert window.train_start == date(2023, 1, 1)
        assert window.train_end == date(2023, 3, 31)
        assert window.val_start == date(2023, 4, 1)
        assert window.val_end == date(2023, 6, 30)


class TestWalkForwardAnalyzerInitialization:
    """Test analyzer creation."""

    def test_default_config(self):
        analyzer = WalkForwardAnalyzer()
        assert analyzer.config.training_window_days == 365
        assert analyzer.config.validation_window_days == 90
        assert analyzer.config.step_size_days == 90
        assert analyzer.windows == []

    def test_custom_config(self):
        config = WalkForwardConfig(
            training_window_days=200,
            validation_window_days=50,
            step_size_days=25,
        )
        analyzer = WalkForwardAnalyzer(config)
        assert analyzer.config.training_window_days == 200
        assert analyzer.config.step_size_days == 25

    def test_properties(self):
        analyzer = WalkForwardAnalyzer()
        assert analyzer.config is not None
        assert analyzer.windows == []


class TestWalkForwardWindowGeneration:
    """Test walk-forward window generation."""

    def test_rolling_windows(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=10,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),
        )
        assert len(windows) > 0
        for w in windows:
            assert w.train_start < w.train_end
            assert w.train_end <= w.val_start
            assert w.val_start < w.val_end
            assert w.is_anchored is False

    def test_rolling_window_dates(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),
        )
        if windows:
            w = windows[0]
            assert w.train_start == date(2023, 1, 1)
            assert (w.train_end - w.train_start).days == 30

    def test_anchored_windows(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=10,
                window_type="anchored",
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),
        )
        for w in windows:
            assert w.is_anchored is True
            assert w.train_start == date(2023, 1, 1)  # Always anchored to start

    def test_windows_overlap_correctly(self):
        """In rolling WFA, windows should not overlap."""
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=40,  # Large step to avoid overlap
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 1),
        )
        for i in range(len(windows) - 1):
            assert windows[i].val_end <= windows[i + 1].train_start

    def test_insufficient_data_returns_no_windows(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=365,
                validation_window_days=90,
                step_size_days=90,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 1),  # Only 2 months of data
        )
        assert len(windows) == 0

    def test_windows_stored_in_analyzer(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 1),
        )
        assert analyzer.windows == windows

    def test_windows_are_deterministic(self):
        config = WalkForwardConfig(
            training_window_days=30, validation_window_days=10, step_size_days=10
        )
        a1 = WalkForwardAnalyzer(config)
        a2 = WalkForwardAnalyzer(config)
        w1 = a1.generate_windows(date(2023, 1, 1), date(2023, 6, 1))
        w2 = a2.generate_windows(date(2023, 1, 1), date(2023, 6, 1))
        assert len(w1) == len(w2)
        for wf1, wf2 in zip(w1, w2):
            assert wf1.train_start == wf2.train_start
            assert wf1.val_end == wf2.val_end

    def test_large_date_range(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=365,
                validation_window_days=90,
                step_size_days=90,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2010, 1, 1),
            end_date=date(2020, 1, 1),
        )
        assert len(windows) > 5

    def test_window_indices(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        windows = analyzer.generate_windows(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 6, 1),
        )
        for i, w in enumerate(windows):
            assert w.window_index == i


class TestWalkForwardExecute:
    """Test execution of walk-forward analysis."""

    @pytest.mark.asyncio
    async def test_execute_without_windows_raises(self):
        analyzer = WalkForwardAnalyzer()

        async def train(s, e):
            return {}

        async def validate(m, s, e):
            return {}

        with pytest.raises(ValueError, match="No windows generated"):
            await analyzer.execute(train, validate)

    @pytest.mark.asyncio
    async def test_single_window_execution(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        analyzer.generate_windows(date(2023, 1, 1), date(2023, 3, 1))

        async def train(s, e):
            return {"model": "trained"}

        async def validate(m, s, e):
            return {"sharpe_ratio": 1.5, "net_profit": 1000.0}

        results = await analyzer.execute(train, validate)
        assert len(results) > 0
        for result in results:
            assert isinstance(result, WalkForwardResult)
            assert result.parameters.get("sharpe_ratio") == 1.5

    @pytest.mark.asyncio
    async def test_multiple_window_execution(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=10,
            )
        )
        analyzer.generate_windows(date(2023, 1, 1), date(2023, 4, 1))

        async def train(s, e):
            return {"model": f"trained_{s}_{e}"}

        async def validate(m, s, e):
            return {"sharpe_ratio": 1.0, "net_profit": 500.0}

        results = await analyzer.execute(train, validate)
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_execution_stores_results(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        analyzer.generate_windows(date(2023, 1, 1), date(2023, 3, 1))

        async def train(s, e):
            return {}

        async def validate(m, s, e):
            return {"sharpe_ratio": 2.0}

        results = await analyzer.execute(train, validate)
        assert len(results) > 0


class TestWalkForwardSummary:
    """Test summary generation."""

    @pytest.mark.asyncio
    async def test_empty_summary(self):
        analyzer = WalkForwardAnalyzer()
        assert analyzer.get_summary() == {}

    @pytest.mark.asyncio
    async def test_summary_with_results(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=30,
            )
        )
        analyzer.generate_windows(date(2023, 1, 1), date(2023, 4, 1))

        async def train(s, e):
            return {}

        async def validate(m, s, e):
            return {"sharpe_ratio": 1.5, "net_profit": 1000.0, "max_drawdown_pct": 5.0}

        await analyzer.execute(train, validate)
        summary = analyzer.get_summary()
        assert "window_count" in summary
        assert "avg_sharpe_ratio" in summary
        assert "avg_net_profit" in summary
        assert "avg_max_drawdown_pct" in summary
        assert summary["window_count"] > 0

    @pytest.mark.asyncio
    async def test_summary_statistics(self):
        analyzer = WalkForwardAnalyzer(
            WalkForwardConfig(
                training_window_days=30,
                validation_window_days=10,
                step_size_days=10,
            )
        )
        analyzer.generate_windows(date(2023, 1, 1), date(2023, 5, 1))

        async def train(s, e):
            return {}

        async def validate(m, s, e):
            return {"sharpe_ratio": 1.0, "net_profit": 500.0, "max_drawdown_pct": 10.0}

        results = await analyzer.execute(train, validate)
        summary = analyzer.get_summary()
        assert "min_sharpe" in summary
        assert "max_sharpe" in summary
        assert "std_sharpe" in summary
