"""Tests for random_search module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.ai_research.models import (
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
)
from libraries.domain.ai_research.random_search import RandomSearchOptimizer


def _make_space(params: list[ParameterDefinition]) -> ParameterSpace:
    return ParameterSpace(parameters=tuple(params))


class TestRandomSearchOptimizer:
    def test_sample_empty_space(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        space = _make_space([])
        results = optimizer.sample(space, max_iterations=10)
        assert len(results) == 0

    def test_sample_int_parameter(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="lookback",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=100),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=5)
        assert len(results) == 5
        for r in results:
            assert 1 <= r["lookback"] <= 100

    def test_sample_float_parameter(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="threshold",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=5)
        assert len(results) == 5
        for r in results:
            assert 0.0 <= r["threshold"] <= 1.0

    def test_sample_bool_parameter(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="enabled",
            parameter_type=ParameterType.BOOL,
        )
        results = optimizer.sample(_make_space([p]), max_iterations=10, duplicate_prevention=False)
        assert len(results) == 10
        assert all(isinstance(r["enabled"], bool) for r in results)

    def test_sample_categorical_parameter(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            constraint=ParameterConstraint(values=("sma", "ema", "wma")),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=10, duplicate_prevention=False)
        assert len(results) == 10
        for r in results:
            assert r["method"] in ("sma", "ema", "wma")

    def test_deterministic_reproducibility(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=100),
        )
        space = _make_space([p])
        results1 = optimizer.sample(space, max_iterations=5, random_seed=42)
        results2 = optimizer.sample(space, max_iterations=5, random_seed=42)
        assert results1 == results2

    def test_different_seeds_produce_different_results(self):
        optimizer = RandomSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=100),
        )
        space = _make_space([p])
        results1 = optimizer.sample(space, max_iterations=5, random_seed=42)
        results2 = optimizer.sample(space, max_iterations=5, random_seed=99)
        assert results1 != results2

    def test_duplicate_prevention(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.BOOL,
        )
        space = _make_space([p])
        results = optimizer.sample(space, max_iterations=10, duplicate_prevention=True)
        # Only 2 unique combinations of bool
        assert len(results) <= 2

    def test_max_iterations_zero_raises_error(self):
        optimizer = RandomSearchOptimizer()
        space = _make_space([ParameterDefinition(name="x", parameter_type=ParameterType.INT)])
        with pytest.raises(ValueError, match="max_iterations must be positive"):
            optimizer.sample(space, max_iterations=0)

    def test_cancel(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        assert optimizer.is_cancelled is False
        optimizer.cancel()
        assert optimizer.is_cancelled is True

    def test_reset(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        optimizer.cancel()
        optimizer.reset()
        assert optimizer.is_cancelled is False

    def test_cancel_stops_sampling(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=1000),
        )
        space = _make_space([p])
        optimizer.cancel()
        results = optimizer.sample(space, max_iterations=100)
        assert len(results) == 0

    def test_enum_parameter(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="mode",
            parameter_type=ParameterType.ENUM,
            constraint=ParameterConstraint(values=("fast", "normal", "slow")),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=5)
        for r in results:
            assert r["mode"] in ("fast", "normal", "slow")

    def test_multiple_parameters(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p1 = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=10),
        )
        p2 = ParameterDefinition(
            name="y",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0),
        )
        p3 = ParameterDefinition(
            name="z",
            parameter_type=ParameterType.BOOL,
        )
        results = optimizer.sample(_make_space([p1, p2, p3]), max_iterations=5)
        assert len(results) == 5
        for r in results:
            assert "x" in r and "y" in r and "z" in r

    def test_progress_callback(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=100),
        )
        calls = []

        def callback(report):
            calls.append(report)

        optimizer.sample(_make_space([p]), max_iterations=5, progress_callback=callback)
        assert len(calls) > 0


class TestRandomSearchCoverageBoost:
    """Coverage boost for uncovered lines in random_search.py."""

    def test_decimal_with_range(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="price",
            parameter_type=ParameterType.DECIMAL,
            constraint=ParameterConstraint(min_value=Decimal("1"), max_value=Decimal("10")),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=5)
        assert len(results) == 5
        for r in results:
            assert isinstance(r["price"], Decimal)

    def test_decimal_with_values(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="price",
            parameter_type=ParameterType.DECIMAL,
            constraint=ParameterConstraint(values=(Decimal("1"), Decimal("5"), Decimal("10"))),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=3, duplicate_prevention=False)
        assert len(results) == 3
        for r in results:
            assert isinstance(r["price"], Decimal)

    def test_enum_without_values_uses_default(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="mode",
            parameter_type=ParameterType.ENUM,
            constraint=ParameterConstraint(),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=3, duplicate_prevention=False)
        assert len(results) == 3
        assert all(r["mode"] == "default" for r in results)

    def test_categorical_without_values_uses_default(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            constraint=ParameterConstraint(),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=3, duplicate_prevention=False)
        assert len(results) == 3
        assert all(r["method"] == "default" for r in results)

    def test_int_without_range_uses_zero(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=3, duplicate_prevention=False)
        assert len(results) == 3
        assert all(r["x"] == 0 for r in results)

    def test_float_without_range_uses_zero(self):
        optimizer = RandomSearchOptimizer(random_seed=42)
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(),
        )
        results = optimizer.sample(_make_space([p]), max_iterations=3, duplicate_prevention=False)
        assert len(results) == 3
        assert all(r["x"] == 0.0 for r in results)
