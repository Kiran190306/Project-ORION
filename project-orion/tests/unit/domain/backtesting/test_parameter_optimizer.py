"""Tests for EPIC-010 ParameterOptimizer and ParameterGrid."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    OptimizationAlgorithm,
    OptimizationConfig,
    OptimizationDirection,
    OptimizationResult,
)
from libraries.domain.backtesting.parameter_optimizer import (
    Parameter,
    ParameterGrid,
    ParameterOptimizer,
)


class TestParameter:
    """Test Parameter dataclass."""

    def test_int_parameter(self):
        p = Parameter(name="period", param_type="int", min_value=10, max_value=50)
        assert p.name == "period"
        assert p.param_type == "int"
        assert p.min_value == 10
        assert p.max_value == 50

    def test_float_parameter(self):
        p = Parameter(name="threshold", param_type="float", min_value=0.0, max_value=1.0)
        assert p.param_type == "float"

    def test_choice_parameter(self):
        p = Parameter(name="method", param_type="choice", choices=["sma", "ema", "wma"])
        assert p.choices == ["sma", "ema", "wma"]

    def test_parameter_with_step(self):
        p = Parameter(name="period", param_type="int", min_value=10, max_value=20, step=2)
        assert p.step == 2


class TestParameterGrid:
    """Test grid generation."""

    def test_single_int_param(self):
        params = [Parameter(name="period", param_type="int", min_value=1, max_value=3)]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 3
        assert grid[0] == {"period": 1}
        assert grid[1] == {"period": 2}
        assert grid[2] == {"period": 3}

    def test_int_param_with_step(self):
        params = [Parameter(name="period", param_type="int", min_value=0, max_value=10, step=5)]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 3
        assert grid[0] == {"period": 0}
        assert grid[1] == {"period": 5}
        assert grid[2] == {"period": 10}

    def test_float_param(self):
        params = [Parameter(name="ratio", param_type="float", min_value=0.0, max_value=1.0)]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 2
        assert grid[0] == {"ratio": 0.0}
        assert grid[1] == {"ratio": 1.0}

    def test_float_param_with_step(self):
        params = [
            Parameter(name="ratio", param_type="float", min_value=0.0, max_value=0.5, step=0.25)
        ]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 3
        assert grid[0] == {"ratio": 0.0}
        assert grid[1] == {"ratio": 0.25}
        assert grid[2] == {"ratio": 0.5}

    def test_choice_param(self):
        params = [Parameter(name="method", param_type="choice", choices=["sma", "ema"])]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 2
        assert grid[0] == {"method": "sma"}
        assert grid[1] == {"method": "ema"}

    def test_multiple_params_product(self):
        params = [
            Parameter(name="period", param_type="int", min_value=1, max_value=2),
            Parameter(name="method", param_type="choice", choices=["a", "b"]),
        ]
        grid = ParameterGrid.generate_grid(params)
        assert len(grid) == 4
        assert {"period": 1, "method": "a"} in grid
        assert {"period": 2, "method": "b"} in grid

    def test_empty_params(self):
        grid = ParameterGrid.generate_grid([])
        assert grid == [{}]

    def test_invalid_param_type(self):
        params = [Parameter(name="x", param_type="invalid_type", min_value=1, max_value=5)]
        grid = ParameterGrid.generate_grid(params)
        assert isinstance(grid, list)

    def test_empty_choices(self):
        params = [Parameter(name="x", param_type="choice", choices=[])]
        grid = ParameterGrid.generate_grid(params)
        assert isinstance(grid, list)


class TestParameterOptimizer:
    """Test the ParameterOptimizer."""

    @pytest.mark.asyncio
    async def test_grid_search(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.GRID_SEARCH, max_iterations=100)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=5)]
        results = []

        async def objective(combo):
            score = combo["x"] ** 2
            results.append(combo["x"])
            return {"score": score}

        result = await opt.optimize(params, objective)
        assert isinstance(result, OptimizationResult)
        assert result.algorithm == OptimizationAlgorithm.GRID_SEARCH
        assert result.best_params == {"x": 5}
        assert result.iterations_run == 5

    @pytest.mark.asyncio
    async def test_random_search(self):
        config = OptimizationConfig(
            algorithm=OptimizationAlgorithm.RANDOM_SEARCH, max_iterations=20, random_seed=42
        )
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=100)]

        async def objective(combo):
            return {"score": combo["x"]}

        result = await opt.optimize(params, objective)
        assert isinstance(result, OptimizationResult)
        assert result.iterations_run == 20

    @pytest.mark.asyncio
    async def test_grid_search_max_iterations(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.GRID_SEARCH, max_iterations=2)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=100)]
        call_count = 0

        async def objective(combo):
            nonlocal call_count
            call_count += 1
            return {"score": combo["x"]}

        result = await opt.optimize(params, objective)
        assert result.iterations_run == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_minimize_direction(self):
        config = OptimizationConfig(
            algorithm=OptimizationAlgorithm.GRID_SEARCH,
            direction=OptimizationDirection.MINIMIZE,
            max_iterations=100,
        )
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=5)]

        async def objective(combo):
            return {"score": combo["x"]}

        result = await opt.optimize(params, objective)
        assert result.best_params == {"x": 1}

    @pytest.mark.asyncio
    async def test_maximize_direction(self):
        config = OptimizationConfig(
            algorithm=OptimizationAlgorithm.GRID_SEARCH,
            direction=OptimizationDirection.MAXIMIZE,
            max_iterations=100,
        )
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=5)]

        async def objective(combo):
            return {"score": combo["x"]}

        result = await opt.optimize(params, objective)
        assert result.best_params == {"x": 5}

    @pytest.mark.asyncio
    async def test_unsupported_algorithm_raises(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.BAYESIAN)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=5)]

        async def objective(combo):
            return {"score": combo["x"]}

        with pytest.raises(NotImplementedError, match="requires external optimizer hook"):
            await opt.optimize(params, objective)

    @pytest.mark.asyncio
    async def test_genetic_algorithm_raises(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.GENETIC)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=5)]

        async def objective(combo):
            return {"score": combo["x"]}

        with pytest.raises(NotImplementedError):
            await opt.optimize(params, objective)

    @pytest.mark.asyncio
    async def test_all_scores_in_result(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.GRID_SEARCH, max_iterations=100)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=3)]

        async def objective(combo):
            return {"score": combo["x"] * 10}

        result = await opt.optimize(params, objective)
        assert len(result.all_scores) == 3
        assert "0" in result.all_scores
        assert result.all_scores["0"] == 10

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self):
        config = OptimizationConfig(algorithm=OptimizationAlgorithm.GRID_SEARCH, max_iterations=100)
        opt = ParameterOptimizer(config)
        params = [Parameter(name="x", param_type="int", min_value=1, max_value=3)]

        async def objective(combo):
            return {"score": combo["x"]}

        result = await opt.optimize(params, objective)
        assert isinstance(result.execution_time_seconds, (int, float))

    @pytest.mark.asyncio
    async def test_random_search_with_choice_param(self):
        config = OptimizationConfig(
            algorithm=OptimizationAlgorithm.RANDOM_SEARCH, max_iterations=10
        )
        opt = ParameterOptimizer(config)
        params = [Parameter(name="method", param_type="choice", choices=["sma", "ema", "wma"])]

        async def objective(combo):
            return {"score": 1.0}

        result = await opt.optimize(params, objective)
        assert result.iterations_run == 10

    @pytest.mark.asyncio
    async def test_random_search_with_float_param(self):
        config = OptimizationConfig(
            algorithm=OptimizationAlgorithm.RANDOM_SEARCH, max_iterations=10
        )
        opt = ParameterOptimizer(config)
        params = [Parameter(name="threshold", param_type="float", min_value=0.0, max_value=1.0)]

        async def objective(combo):
            return {"score": combo["threshold"]}

        result = await opt.optimize(params, objective)
        assert result.iterations_run == 10
        assert "threshold" in result.best_params


class TestOptimizationResult:
    """Test OptimizationResult model."""

    def test_result_defaults(self):
        result = OptimizationResult()
        assert result.best_score == 0.0
        assert result.iterations_run == 0

    def test_result_custom(self):
        result = OptimizationResult(
            best_params={"x": 5},
            best_score=25.0,
            iterations_run=100,
            total_iterations=100,
        )
        assert result.best_params == {"x": 5}
        assert result.best_score == 25.0
        assert result.iterations_run == 100

    def test_direction_enum(self):
        assert OptimizationDirection.MAXIMIZE.value == "maximize"
        assert OptimizationDirection.MINIMIZE.value == "minimize"
