"""Parameter optimizer for backtesting.

Supports grid search, random search, Bayesian optimization (hook),
and genetic algorithm (hook) for strategy parameter optimization
with parallel evaluation support.
"""

from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from libraries.domain.backtesting.models import (
    OptimizationAlgorithm,
    OptimizationConfig,
    OptimizationResult,
)


@dataclass(frozen=True, slots=True)
class Parameter:
    """A single parameter definition for optimization."""

    name: str
    param_type: str  # int, float, choice
    min_value: float | None = None
    max_value: float | None = None
    choices: list[Any] | None = None
    step: float | None = None


class ParameterGrid:
    """Generates parameter grids for optimization."""

    @staticmethod
    def generate_grid(params: list[Parameter]) -> list[dict[str, Any]]:
        """Generate exhaustive grid of parameter combinations.

        Args:
            params: List of parameter definitions.

        Returns:
            List of parameter combination dicts.
        """
        param_values: list[list[Any]] = []
        for p in params:
            values: list[Any] = []
            if p.param_type == "int":
                if p.step:
                    values = list(
                        range(int(p.min_value or 0), int(p.max_value or 100) + 1, int(p.step))
                    )
                else:
                    values = list(range(int(p.min_value or 0), int(p.max_value or 100) + 1))
            elif p.param_type == "float":
                if p.step:
                    current = p.min_value or 0.0
                    while current <= (p.max_value or 1.0):
                        values.append(round(current, 4))
                        current += p.step or 0.1
                else:
                    values = [(p.min_value or 0.0), (p.max_value or 1.0)]
            elif p.param_type == "choice":
                values = p.choices or []
            else:
                values = []

            param_values.append(values)

        grids = list(itertools.product(*param_values))
        return [dict(zip([p.name for p in params], g)) for g in grids]


class ParameterOptimizer:
    """Optimizes strategy parameters using various search methods.

    Supports grid search, random search, with hooks for Bayesian
    optimization and genetic algorithms.
    """

    def __init__(self, config: OptimizationConfig | None = None) -> None:
        """Initialize parameter optimizer.

        Args:
            config: Optimization configuration.
        """
        self._config = config or OptimizationConfig(
            algorithm=OptimizationAlgorithm.GRID_SEARCH,
            max_iterations=100,
        )
        self._random = random.Random(42)

    @property
    def config(self) -> OptimizationConfig:
        return self._config

    async def optimize(
        self,
        params: list[Parameter],
        objective_func: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> OptimizationResult:
        """Run parameter optimization.

        Args:
            params: List of parameters to optimize.
            objective_func: Function that evaluates a parameter set.
                Returns dict with at least 'score' key.

        Returns:
            OptimizationResult with best parameters and history.
        """
        cfg = self._config
        evaluations: list[dict[str, Any]] = []
        best_score = float("-inf") if cfg.direction.value == "maximize" else float("inf")
        best_params: dict[str, Any] = {}
        start_time = time.time()

        algorithm_str = cfg.algorithm.value

        if algorithm_str == "grid_search":
            param_grid = ParameterGrid.generate_grid(params)
            for i, combo in enumerate(param_grid):
                if i >= cfg.max_iterations:
                    break
                result = await objective_func(combo)
                score = result.get("score", 0.0)
                evaluations.append({"params": combo, "result": result, "score": score})
                if (cfg.direction.value == "maximize" and score > best_score) or (
                    cfg.direction.value == "minimize" and score < best_score
                ):
                    best_score = score
                    best_params = combo

        elif algorithm_str == "random_search":
            for i in range(min(cfg.max_iterations, 10000)):
                combo = self._random_sample(params)
                result = await objective_func(combo)
                score = result.get("score", 0.0)
                evaluations.append({"params": combo, "result": result, "score": score})
                if (cfg.direction.value == "maximize" and score > best_score) or (
                    cfg.direction.value == "minimize" and score < best_score
                ):
                    best_score = score
                    best_params = combo

        elif algorithm_str in ("bayesian", "genetic", "particle_swarm", "reinforcement"):
            raise NotImplementedError(
                f"Algorithm '{algorithm_str}' requires external optimizer hook. "
                f"Use grid_search or random_search for built-in support."
            )

        elapsed = time.time() - start_time

        # Build all_scores dict for canonical result
        all_scores = {str(i): e["score"] for i, e in enumerate(evaluations)}

        return OptimizationResult(
            best_params=best_params,
            best_score=round(best_score, 4),
            all_scores=all_scores,
            iterations_run=len(evaluations),
            total_iterations=cfg.max_iterations,
            algorithm=cfg.algorithm,
            direction=cfg.direction,
            metric=cfg.metric,
            random_seed=cfg.random_seed,
            execution_time_seconds=round(elapsed, 2),
        )

    def _random_sample(self, params: list[Parameter]) -> dict[str, Any]:
        """Generate a random parameter combination.

        Args:
            params: List of parameter definitions.

        Returns:
            Random parameter combination dict.
        """
        combo: dict[str, Any] = {}
        for p in params:
            if p.param_type == "int":
                min_v = int(p.min_value or 0)
                max_v = int(p.max_value or 100)
                if p.step:
                    step_count = int((max_v - min_v) / p.step)
                    combo[p.name] = min_v + self._random.randint(0, step_count) * int(p.step)
                else:
                    combo[p.name] = self._random.randint(min_v, max_v)
            elif p.param_type == "float":
                min_f = p.min_value or 0.0
                max_f = p.max_value or 1.0
                combo[p.name] = round(self._random.uniform(min_f, max_f), 4)
            elif p.param_type == "choice":
                choices = p.choices or []
                val: Any | None = self._random.choice(choices) if choices else None
                combo[p.name] = val
        return combo
