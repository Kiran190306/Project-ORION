"""Deterministic grid search optimizer with exhaustive parameter combination generation."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from libraries.domain.ai_research.exceptions import OptimizationError
from libraries.domain.ai_research.models import (
    OptimizationState,
    ParameterDefinition,
    ParameterSpace,
    ParameterType,
    ProgressReport,
)


class GridSearchOptimizer:
    """Deterministic exhaustive grid search over a parameter space.

    Generates all possible parameter combinations within the defined space.
    Supports:
        - Exhaustive search
        - Maximum combinations limit
        - Progress reporting
        - Cancellation
    """

    def __init__(self) -> None:
        self._state = OptimizationState.PENDING
        self._cancelled = False

    @property
    def state(self) -> OptimizationState:
        return self._state

    def cancel(self) -> None:
        """Cancel the current search."""
        self._cancelled = True
        self._state = OptimizationState.CANCELLED

    def generate(
        self,
        space: ParameterSpace,
        max_combinations: int = 10000,
        progress_callback: Callable[[ProgressReport], None] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Generate all parameter combinations exhaustively.

        Args:
            space: Parameter space to search.
            max_combinations: Maximum number of combinations to generate.
            progress_callback: Optional callback for progress reporting.

        Returns:
            Tuple of parameter combination dictionaries.

        Raises:
            OptimizationError: If the space is empty or has no parameters.
        """
        if not space.parameters:
            raise OptimizationError("parameter space has no parameters")

        self._state = OptimizationState.RUNNING

        # Build value lists for each parameter
        value_lists: list[list[tuple[str, Any]]] = []
        for param in space.parameters:
            values = self._get_values(param)
            if not values:
                raise OptimizationError(f"parameter '{param.name}' has no values to search")
            value_lists.append([(param.name, v) for v in values])

        # Calculate total combinations
        total_combos = 1
        for vl in value_lists:
            total_combos *= len(vl)
        total_combos = min(total_combos, max_combinations)

        # Generate all combinations
        total = 0
        results: list[dict[str, Any]] = []

        for combo in itertools.product(*value_lists):
            if self._cancelled:
                self._state = OptimizationState.CANCELLED
                break

            if total >= max_combinations:
                break

            params = dict(combo)
            results.append(params)
            total += 1

            if progress_callback and total % max(1, total_combos // 100) == 0:
                progress_callback(
                    ProgressReport(
                        completed=total,
                        total=total_combos,
                        message=f"Grid search iteration {total}",
                    )
                )

        # Final progress report
        if progress_callback:
            progress_callback(
                ProgressReport(
                    completed=total,
                    total=total_combos,
                    message="Grid search completed",
                )
            )

        self._state = OptimizationState.COMPLETED
        return tuple(results)

    @staticmethod
    def _get_values(param: ParameterDefinition) -> list[Any]:
        """Get all possible values for a single parameter."""
        constraint = param.constraint
        param_type = param.parameter_type

        if param_type == ParameterType.INT:
            if constraint.values:
                return [int(v) for v in constraint.values]
            if constraint.min_value is not None and constraint.max_value is not None:
                step = int(constraint.step) if constraint.step is not None else 1
                return list(range(int(constraint.min_value), int(constraint.max_value) + 1, step))
            return []

        elif param_type == ParameterType.FLOAT:
            if constraint.values:
                return [float(v) for v in constraint.values]
            if constraint.min_value is not None and constraint.max_value is not None:
                step = float(constraint.step) if constraint.step is not None else 0.1
                values = []
                current = float(constraint.min_value)
                while current <= float(constraint.max_value):
                    values.append(round(current, 10))
                    current += step
                return values
            return []

        elif param_type == ParameterType.DECIMAL:
            if constraint.values:
                return [Decimal(str(v)) for v in constraint.values]
            return []

        elif param_type == ParameterType.BOOL:
            return [True, False]

        elif param_type in (ParameterType.CATEGORICAL, ParameterType.ENUM):
            return list(constraint.values) if constraint.values else []

        return []
