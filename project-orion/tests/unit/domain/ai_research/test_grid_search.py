"""Tests for grid_search module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import OptimizationError
from libraries.domain.ai_research.grid_search import GridSearchOptimizer
from libraries.domain.ai_research.models import (
    OptimizationState,
    ParameterConstraint,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
)


def _make_space(params: list[ParameterDefinition]) -> ParameterSpace:
    return ParameterSpace(parameters=tuple(params))


class TestGridSearchOptimizer:
    def test_empty_space_raises_error(self):
        optimizer = GridSearchOptimizer()
        space = _make_space([])
        with pytest.raises(OptimizationError, match="parameter space has no parameters"):
            optimizer.generate(space)

    def test_single_int_parameter(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="lookback",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=3),
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 3

    def test_single_float_parameter_with_step(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="threshold",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(min_value=0.0, max_value=1.0, step=0.5),
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 3

    def test_bool_parameter(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="enabled",
            parameter_type=ParameterType.BOOL,
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 2
        assert results[0] == {"enabled": True}
        assert results[1] == {"enabled": False}

    def test_categorical_parameter(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="method",
            parameter_type=ParameterType.CATEGORICAL,
            constraint=ParameterConstraint(values=("sma", "ema", "wma")),
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 3

    def test_multiple_parameters(self):
        optimizer = GridSearchOptimizer()
        p1 = ParameterDefinition(
            name="p1",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=2),
        )
        p2 = ParameterDefinition(
            name="p2",
            parameter_type=ParameterType.BOOL,
        )
        results = optimizer.generate(_make_space([p1, p2]))
        assert len(results) == 4

    def test_max_combinations(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=100),
        )
        results = optimizer.generate(_make_space([p]), max_combinations=10)
        assert len(results) == 10

    def test_cancel(self):
        optimizer = GridSearchOptimizer()
        assert optimizer.state == OptimizationState.PENDING
        optimizer.cancel()
        assert optimizer.state == OptimizationState.CANCELLED

    def test_cancellation_stops_generation(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=10000),
        )
        optimizer.cancel()
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 0

    def test_deterministic_order(self):
        optimizer = GridSearchOptimizer()
        p1 = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=3),
        )
        p2 = ParameterDefinition(
            name="y",
            parameter_type=ParameterType.BOOL,
        )
        results1 = optimizer.generate(_make_space([p1, p2]))
        results2 = optimizer.generate(_make_space([p1, p2]))
        assert results1 == results2

    def test_progress_callback(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(min_value=1, max_value=10),
        )
        calls = []

        def callback(report):
            calls.append(report)

        results = optimizer.generate(_make_space([p]), progress_callback=callback)
        assert len(results) == 10
        assert len(calls) > 0

    def test_int_with_values(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.INT,
            constraint=ParameterConstraint(values=(5, 10, 15)),
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 3
        values = set(r["x"] for r in results)
        assert values == {5, 10, 15}

    def test_float_with_values(self):
        optimizer = GridSearchOptimizer()
        p = ParameterDefinition(
            name="x",
            parameter_type=ParameterType.FLOAT,
            constraint=ParameterConstraint(values=(0.1, 0.5, 1.0)),
        )
        results = optimizer.generate(_make_space([p]))
        assert len(results) == 3
