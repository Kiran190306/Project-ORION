"""Parameter space generator, validator, and combinatorial safety engine."""

from __future__ import annotations

import itertools
import math
import random
from decimal import Decimal
from typing import Any

from libraries.domain.research.optimization_models import (
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)
from libraries.domain.strategy.registry import StrategyRegistry


def normalize_strategy_id(strategy_id: str) -> str:
    """Normalize user or archetype string to registered strategy ID."""
    s = strategy_id.strip()
    mapping = {
        "trendfollowing": "trend_following",
        "trend_following": "trend_following",
        "meanreversion": "mean_reversion",
        "mean_reversion": "mean_reversion",
        "breakout": "breakout",
        "momentum": "momentum",
    }
    cleaned = s.lower().replace("-", "_").replace(" ", "_")
    return mapping.get(cleaned, cleaned)


class ParameterSpaceEngine:
    """Validates parameter ranges, calculates combinations, and generates parameter sets."""

    @staticmethod
    def get_default_space(strategy_id: str) -> ParameterSpaceDefinition:
        """Get canonical default parameter search space for a registered strategy."""
        canonical_id = normalize_strategy_id(strategy_id)
        entry = StrategyRegistry.get(canonical_id)

        if canonical_id == "trend_following":
            ranges = (
                ParameterRange(name="fast_period", param_type=ParameterType.INT, min_value=5, max_value=25, step=5),
                ParameterRange(name="slow_period", param_type=ParameterType.INT, min_value=30, max_value=60, step=10),
            )
        elif canonical_id == "mean_reversion":
            ranges = (
                ParameterRange(name="lookback_period", param_type=ParameterType.INT, min_value=10, max_value=30, step=5),
                ParameterRange(name="entry_threshold", param_type=ParameterType.FLOAT, min_value=1.0, max_value=3.0, step=0.5),
            )
        elif canonical_id == "breakout":
            ranges = (
                ParameterRange(name="channel_period", param_type=ParameterType.INT, min_value=10, max_value=30, step=5),
                ParameterRange(name="breakout_multiplier", param_type=ParameterType.FLOAT, min_value=0.5, max_value=2.0, step=0.5),
            )
        elif canonical_id == "momentum":
            ranges = (
                ParameterRange(name="momentum_period", param_type=ParameterType.INT, min_value=10, max_value=25, step=5),
                ParameterRange(name="momentum_threshold", param_type=ParameterType.FLOAT, min_value=0.01, max_value=0.05, step=0.01),
            )
        else:
            param_ranges = []
            for p in entry.parameters:
                p_type = ParameterType.INT if p.param_type == "integer" else ParameterType.FLOAT
                p_min = p.min_value if p.min_value is not None else 1
                p_max = p.max_value if p.max_value is not None else 100
                step = 1 if p_type == ParameterType.INT else 0.1
                param_ranges.append(
                    ParameterRange(name=p.name, param_type=p_type, min_value=p_min, max_value=p_max, step=step)
                )
            ranges = tuple(param_ranges)

        return ParameterSpaceDefinition(strategy_id=canonical_id, ranges=ranges)

    @classmethod
    def validate_space(cls, space: ParameterSpaceDefinition) -> None:
        """Validate parameter space definition against StrategyRegistry schemas and bounds."""
        canonical_id = normalize_strategy_id(space.strategy_id)
        entry = StrategyRegistry.get(canonical_id)

        meta_param_map = {p.name: p for p in entry.parameters}

        for pr in space.ranges:
            if pr.name not in meta_param_map:
                raise ValueError(f"Parameter '{pr.name}' is not recognized for strategy '{canonical_id}'")

            p_meta = meta_param_map[pr.name]

            if pr.param_type in (ParameterType.INT, ParameterType.FLOAT):
                if not math.isfinite(float(pr.min_value)) or not math.isfinite(float(pr.max_value)):
                    raise ValueError(f"Bounds for parameter '{pr.name}' must be finite")

                if p_meta.min_value is not None and float(pr.min_value) < float(p_meta.min_value):
                    raise ValueError(
                        f"min_value ({pr.min_value}) for '{pr.name}' violates strategy minimum bound ({p_meta.min_value})"
                    )

                if p_meta.max_value is not None and float(pr.max_value) > float(p_meta.max_value):
                    raise ValueError(
                        f"max_value ({pr.max_value}) for '{pr.name}' violates strategy maximum bound ({p_meta.max_value})"
                    )

                if pr.step is not None:
                    if not math.isfinite(float(pr.step)) or float(pr.step) <= 0:
                        raise ValueError(f"Step size for '{pr.name}' must be strictly positive and finite")
                    span = float(pr.max_value) - float(pr.min_value)
                    if span > 0 and float(pr.step) > span:
                        raise ValueError(f"Step size ({pr.step}) cannot exceed range span ({span}) for '{pr.name}'")

    @classmethod
    def expand_values(cls, pr: ParameterRange) -> list[Any]:
        """Expand a ParameterRange into discrete values."""
        if pr.param_type == ParameterType.CHOICE:
            if not pr.choices:
                raise ValueError(f"Choice parameter '{pr.name}' has no choices defined")
            return list(pr.choices)

        if pr.step is None:
            step = 1 if pr.param_type == ParameterType.INT else 0.1
        else:
            step = pr.step

        values: list[Any] = []
        if pr.param_type == ParameterType.INT:
            start = int(pr.min_value)
            end = int(pr.max_value)
            istep = max(1, int(step))
            curr = start
            while curr <= end:
                values.append(curr)
                curr += istep
        else:
            start = float(pr.min_value)
            end = float(pr.max_value)
            fstep = float(step)
            d_curr = Decimal(str(start))
            d_end = Decimal(str(end))
            d_step = Decimal(str(fstep))
            while d_curr <= d_end + Decimal("1e-9"):
                values.append(float(round(d_curr, 6)))
                d_curr += d_step

        if not values:
            values.append(pr.min_value)
        return values

    @classmethod
    def count_combinations(cls, space: ParameterSpaceDefinition) -> int:
        """Calculate total raw combinations for a parameter space."""
        total = 1
        for pr in space.ranges:
            vals = cls.expand_values(pr)
            total *= len(vals)
        return total

    @classmethod
    def generate_grid(
        cls,
        space: ParameterSpaceDefinition,
        max_combinations: int = 500,
    ) -> list[dict[str, Any]]:
        """Generate parameter combinations via exhaustive grid search."""
        cls.validate_space(space)
        total_raw = cls.count_combinations(space)
        if total_raw > max_combinations:
            raise ValueError(
                f"Parameter space yields {total_raw} combinations, exceeding maximum limit of {max_combinations}"
            )

        value_lists = []
        for pr in space.ranges:
            vals = cls.expand_values(pr)
            value_lists.append([(pr.name, v) for v in vals])

        canonical_id = normalize_strategy_id(space.strategy_id)
        combinations = []
        for combo in itertools.product(*value_lists):
            params = dict(combo)
            if cls._is_valid_parameter_combination(canonical_id, params):
                combinations.append(params)

        if not combinations:
            raise ValueError("No valid parameter combinations could be generated after applying consistency constraints")

        return combinations

    @classmethod
    def generate_random(
        cls,
        space: ParameterSpaceDefinition,
        n_samples: int = 50,
        random_seed: int = 42,
    ) -> list[dict[str, Any]]:
        """Generate deterministic random parameter samples within parameter space."""
        cls.validate_space(space)
        if n_samples < 1:
            raise ValueError("n_samples must be at least 1")

        rng = random.Random(random_seed)
        candidate_pool = cls.generate_grid(space, max_combinations=max(10000, n_samples * 10))

        if len(candidate_pool) <= n_samples:
            return candidate_pool

        return rng.sample(candidate_pool, n_samples)

    @classmethod
    def _is_valid_parameter_combination(cls, strategy_id: str, params: dict[str, Any]) -> bool:
        """Enforce domain-specific inter-parameter relationships."""
        canonical_id = normalize_strategy_id(strategy_id)
        if canonical_id == "trend_following":
            fast = params.get("fast_period")
            slow = params.get("slow_period")
            if fast is not None and slow is not None and fast >= slow:
                return False
        return True
