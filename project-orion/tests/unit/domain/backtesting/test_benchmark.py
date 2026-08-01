"""Tests for EPIC-010 BenchmarkComparator — benchmark-relative performance analysis."""

from __future__ import annotations

import pytest

from libraries.domain.backtesting.benchmark import (
    BenchmarkComparator,
    BenchmarkComparisonConfig,
    BenchmarkStatistics,
)


class TestBenchmarkComparisonConfig:
    """Test BenchmarkComparisonConfig defaults and construction."""

    def test_default_config(self) -> None:
        cfg = BenchmarkComparisonConfig()
        assert cfg.risk_free_rate == 0.02
        assert cfg.periods_per_year == 252
        assert cfg.benchmark_label == "benchmark"

    def test_custom_config(self) -> None:
        cfg = BenchmarkComparisonConfig(
            risk_free_rate=0.03,
            periods_per_year=52,
            benchmark_label="SP500",
        )
        assert cfg.risk_free_rate == 0.03
        assert cfg.periods_per_year == 52
        assert cfg.benchmark_label == "SP500"

    def test_config_frozen(self) -> None:
        cfg = BenchmarkComparisonConfig()
        with pytest.raises(AttributeError):
            cfg.risk_free_rate = 0.05  # type: ignore[misc]


class TestBenchmarkComparator:
    """Test BenchmarkComparator calculation."""

    def test_default_initialization(self) -> None:
        comparator = BenchmarkComparator()
        assert comparator.config.risk_free_rate == 0.02

    def test_config_property(self) -> None:
        comparator = BenchmarkComparator()
        assert isinstance(comparator.config, BenchmarkComparisonConfig)

    def test_empty_returns(self) -> None:
        comparator = BenchmarkComparator()
        stats = comparator.calculate([], [])
        assert isinstance(stats, BenchmarkStatistics)
        assert stats.num_periods == 0

    def test_single_period(self) -> None:
        comparator = BenchmarkComparator()
        stats = comparator.calculate([0.01], [0.005])
        assert stats.num_periods == 0  # Need at least 2 periods

    def test_identical_returns(self) -> None:
        comparator = BenchmarkComparator()
        returns = [0.01, 0.02, -0.01, 0.005, -0.005]
        stats = comparator.calculate(returns, returns)
        assert stats.beta == pytest.approx(1.0, rel=1e-2)
        assert stats.correlation == pytest.approx(1.0, rel=1e-2)
        assert stats.excess_return == pytest.approx(0.0, abs=1e-4)

    def test_higher_returns_than_benchmark(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.02, 0.03, -0.01, 0.015, -0.005]
        benchmark = [0.01, 0.02, -0.02, 0.005, -0.01]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.excess_return > 0
        assert stats.alpha > 0

    def test_lower_returns_than_benchmark(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.005, 0.01, -0.03, 0.005, -0.01]
        benchmark = [0.01, 0.02, -0.01, 0.01, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.excess_return < 0
        assert stats.alpha < 0

    def test_beta_greater_than_one(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.03, 0.04, -0.02, 0.02, -0.01]
        benchmark = [0.01, 0.02, -0.01, 0.01, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.beta > 1.0

    def test_beta_less_than_one(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.005, 0.01, -0.005, 0.003, -0.002]
        benchmark = [0.01, 0.02, -0.01, 0.01, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.beta < 1.0

    def test_information_ratio_positive(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.02, 0.03, -0.005, 0.015, -0.002]
        benchmark = [0.01, 0.02, -0.01, 0.005, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.information_ratio > 0

    def test_statistical_significance(self) -> None:
        comparator = BenchmarkComparator()
        # 30 periods = significant
        portfolio = [0.01] * 30
        benchmark = [0.005] * 30
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.is_statistically_significant
        assert stats.num_periods == 30

    def test_not_statistically_significant(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.01] * 10
        benchmark = [0.005] * 10
        stats = comparator.calculate(portfolio, benchmark)
        assert not stats.is_statistically_significant

    def test_up_capture_ratio(self) -> None:
        comparator = BenchmarkComparator()
        # Portfolio outperforms in up markets
        portfolio = [0.03, -0.01, 0.04, -0.02, 0.02]
        benchmark = [0.02, -0.01, 0.02, -0.02, 0.01]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.up_capture_ratio > 0

    def test_down_capture_ratio(self) -> None:
        comparator = BenchmarkComparator()
        # Portfolio declines less in down markets
        portfolio = [0.02, -0.02, 0.03, -0.01, 0.01]
        benchmark = [0.02, -0.04, 0.03, -0.03, 0.01]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.down_capture_ratio > 0

    def test_treynor_ratio(self) -> None:
        comparator = BenchmarkComparator()
        portfolio = [0.02, 0.01, -0.01, 0.015, -0.005]
        benchmark = [0.01, 0.005, -0.01, 0.01, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        # Treynor ratio should be some value
        assert isinstance(stats.treynor_ratio, float)

    def test_relative_drawdown(self) -> None:
        comparator = BenchmarkComparator()
        # Portfolio drops while benchmark rises
        portfolio = [0.01, 0.02, -0.05, -0.03, 0.01]
        benchmark = [0.01, 0.02, 0.01, 0.005, 0.01]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.max_relative_drawdown >= 0

    def test_custom_config(self) -> None:
        cfg = BenchmarkComparisonConfig(risk_free_rate=0.05, periods_per_year=12)
        comparator = BenchmarkComparator(config=cfg)
        portfolio = [0.02, 0.03, -0.01, 0.015, -0.005]
        benchmark = [0.01, 0.02, -0.01, 0.005, -0.005]
        stats = comparator.calculate(portfolio, benchmark)
        assert stats.num_periods == 5
        assert isinstance(stats.alpha, float)

    def test_benchmark_statistics_defaults(self) -> None:
        stats = BenchmarkStatistics()
        assert stats.alpha == 0.0
        assert stats.beta == 1.0
        assert stats.correlation == 0.0
        assert stats.tracking_error == 0.0
        assert stats.information_ratio == 0.0
        assert stats.treynor_ratio == 0.0
        assert stats.num_periods == 0
        assert not stats.is_statistically_significant
