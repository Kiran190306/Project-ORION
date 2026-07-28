"""Deterministic random search optimizer with seeded reproducibility."""

from __future__ import annotations

import random as _random
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from libraries.domain.ai_research.models import (
    OptimizationState,
    ParameterSpace,
    ParameterType,
    ProgressReport,
)


class RandomSearchOptimizer:
    """Deterministic random search over a parameter space.

    Supports:
        - Deterministic random seed
        - Maximum iterations
        - Reproducible sampling
        - Duplicate prevention
        - Progress reporting
    """

    def __init__(self, random_seed: int | None = None) -> None:
        self._random_seed = random_seed
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Cancel the current search."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset cancellation state."""
        self._cancelled = False

    def sample(
        self,
        space: ParameterSpace,
        max_iterations: int = 100,
        random_seed: int | None = None,
        duplicate_prevention: bool = True,
        progress_callback: Callable[[ProgressReport], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Sample parameter combinations randomly.

        Args:
            space: Parameter space.
            max_iterations: Maximum number of samples.
            random_seed: Seed for reproducibility (overrides instance seed).
            duplicate_prevention: Whether to prevent duplicate samples.
            progress_callback: Optional progress callback.

        Returns:
            List of sampled parameter combinations.
        """
        if max_iterations < 1:
            raise ValueError("max_iterations must be positive")

        if not space.parameters:
            return []

        seed = random_seed if random_seed is not None else self._random_seed
        rng = _random.Random(seed)

        results: list[dict[str, Any]] = []
        seen: set[frozenset] = set()
        max_attempts = max_iterations * 10

        for iteration in range(max_iterations):
            if self._cancelled:
                break

            attempts = 0
            found = False
            while attempts < max_attempts:
                if self._cancelled:
                    break
                sample = self._sample_single(space, rng)
                if duplicate_prevention:
                    key = frozenset(sample.items())
                    if key not in seen:
                        seen.add(key)
                        found = True
                        break
                    attempts += 1
                else:
                    found = True
                    break

            if not found:
                # All unique combinations exhausted; stop early
                break

            results.append(sample)

            if progress_callback:
                progress_callback(
                    ProgressReport(
                        completed=iteration + 1,
                        total=max_iterations,
                        message=f"Sampling iteration {iteration + 1}/{max_iterations}",
                    )
                )

        return results

    def _sample_single(
        self,
        space: ParameterSpace,
        rng: _random.Random,
    ) -> dict[str, Any]:
        """Sample a single parameter combination."""
        sample: dict[str, Any] = {}
        for param in space.parameters:
            constraint = param.constraint
            if param.parameter_type == ParameterType.INT:
                if constraint.min_value is not None and constraint.max_value is not None:
                    sample[param.name] = rng.randint(
                        int(constraint.min_value), int(constraint.max_value)
                    )
                elif constraint.values:
                    sample[param.name] = int(rng.choice(list(constraint.values)))
                else:
                    sample[param.name] = 0
            elif param.parameter_type == ParameterType.FLOAT:
                if constraint.min_value is not None and constraint.max_value is not None:
                    sample[param.name] = rng.uniform(
                        float(constraint.min_value), float(constraint.max_value)
                    )
                elif constraint.values:
                    sample[param.name] = float(rng.choice(list(constraint.values)))
                else:
                    sample[param.name] = 0.0
            elif param.parameter_type == ParameterType.BOOL:
                sample[param.name] = rng.choice([True, False])
            elif param.parameter_type == ParameterType.CATEGORICAL:
                if constraint.values:
                    sample[param.name] = rng.choice(list(constraint.values))
                else:
                    sample[param.name] = "default"
            elif param.parameter_type == ParameterType.ENUM:
                if constraint.values:
                    sample[param.name] = rng.choice(list(constraint.values))
                else:
                    sample[param.name] = "default"
            elif param.parameter_type == ParameterType.DECIMAL:
                if constraint.min_value is not None and constraint.max_value is not None:
                    min_dec = (
                        constraint.min_value
                        if isinstance(constraint.min_value, Decimal)
                        else Decimal(str(constraint.min_value))
                    )
                    max_dec = (
                        constraint.max_value
                        if isinstance(constraint.max_value, Decimal)
                        else Decimal(str(constraint.max_value))
                    )
                    sampled = rng.uniform(float(min_dec), float(max_dec))
                    sample[param.name] = Decimal(str(sampled))
                elif constraint.values:
                    sample[param.name] = Decimal(str(rng.choice(list(constraint.values))))
                else:
                    sample[param.name] = Decimal("0")
            else:
                sample[param.name] = param.default
        return sample
