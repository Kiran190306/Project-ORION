"""Unit tests for ParameterSpaceEngine in EPIC-024."""

import pytest

from libraries.domain.research.optimization_models import (
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)
from libraries.domain.research.parameter_space_engine import ParameterSpaceEngine


def test_get_default_space_for_all_archetypes():
    for arch in ["TrendFollowing", "MeanReversion", "Breakout", "Momentum"]:
        space = ParameterSpaceEngine.get_default_space(arch)
        assert space.strategy_id in ("trend_following", "mean_reversion", "breakout", "momentum")
        assert len(space.ranges) >= 2
        combos = ParameterSpaceEngine.count_combinations(space)
        assert combos > 0


def test_count_combinations():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 20, step=5),  # 10, 15, 20 -> 3
        ParameterRange("slow_period", ParameterType.INT, 30, 50, step=10), # 30, 40, 50 -> 3
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    assert ParameterSpaceEngine.count_combinations(space) == 9


def test_generate_grid_and_filter_invariants():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 30, step=10), # 10, 20, 30
        ParameterRange("slow_period", ParameterType.INT, 20, 40, step=10), # 20, 30, 40
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    grid = ParameterSpaceEngine.generate_grid(space, max_combinations=100)
    # Every generated combo must satisfy fast < slow
    for c in grid:
        assert c["fast_period"] < c["slow_period"]


def test_generate_grid_combination_limit_exceeded():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 5, 50, step=1),
        ParameterRange("slow_period", ParameterType.INT, 10, 50, step=1),
    )
    space = ParameterSpaceDefinition("trend_following", ranges)
    with pytest.raises(ValueError, match="exceeding maximum limit"):
        ParameterSpaceEngine.generate_grid(space, max_combinations=50)


def test_generate_random_deterministic_seed():
    space = ParameterSpaceEngine.get_default_space("TrendFollowing")
    samples1 = ParameterSpaceEngine.generate_random(space, n_samples=10, random_seed=123)
    samples2 = ParameterSpaceEngine.generate_random(space, n_samples=10, random_seed=123)
    samples3 = ParameterSpaceEngine.generate_random(space, n_samples=10, random_seed=999)

    assert len(samples1) == 10
    assert samples1 == samples2
    assert samples1 != samples3


def test_validate_space_invalid_parameter():
    ranges = (
        ParameterRange("non_existent_param", ParameterType.INT, 1, 10, step=1),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    with pytest.raises(ValueError, match="not recognized"):
        ParameterSpaceEngine.validate_space(space)


def test_validate_space_out_of_bounds():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, -5, 20, step=5),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    with pytest.raises(ValueError, match="violates strategy minimum bound"):
        ParameterSpaceEngine.validate_space(space)


def test_validate_space_step_exceeds_span():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 15, step=20),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    with pytest.raises(ValueError, match="cannot exceed range span"):
        ParameterSpaceEngine.validate_space(space)
