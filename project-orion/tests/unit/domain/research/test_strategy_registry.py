"""Unit tests for StrategyRegistry and parameter validation (EPIC-023 Phase 2 & 3)."""

from __future__ import annotations

import pytest

from libraries.domain.strategy.registry import (
    InvalidStrategyParameterError,
    StrategyRegistry,
    UnknownStrategyError,
)


def test_catalogue_contains_core_strategies() -> None:
    """Strategy catalogue must contain standard institutional strategies."""
    strategies = StrategyRegistry.list_strategies()
    assert len(strategies) >= 4
    strategy_ids = {s.strategy_id for s in strategies}
    assert "trend_following" in strategy_ids
    assert "mean_reversion" in strategy_ids
    assert "breakout" in strategy_ids
    assert "momentum" in strategy_ids


def test_get_strategy_metadata() -> None:
    """Strategy details must expose typed parameters and supported instruments."""
    entry = StrategyRegistry.get("trend_following")
    assert entry.strategy_id == "trend_following"
    assert entry.is_deterministic is True
    assert "EUR/USD" in entry.supported_instruments
    assert "H1" in entry.supported_timeframes
    param_names = [p.name for p in entry.parameters]
    assert "fast_period" in param_names
    assert "slow_period" in param_names


def test_get_unknown_strategy_raises_error() -> None:
    """Querying unregistered strategy must raise UnknownStrategyError."""
    with pytest.raises(UnknownStrategyError, match="not registered"):
        StrategyRegistry.get("non_existent_strategy_xyz")


def test_validate_parameters_defaults() -> None:
    """Validating None or empty dict returns valid default parameters."""
    validated = StrategyRegistry.validate_parameters("trend_following", None)
    assert validated["fast_period"] == 10
    assert validated["slow_period"] == 30


def test_validate_parameters_custom_valid() -> None:
    """Valid custom parameters pass validation."""
    custom = {
        "fast_period": 15,
        "slow_period": 50,
    }
    validated = StrategyRegistry.validate_parameters("trend_following", custom)
    assert validated["fast_period"] == 15
    assert validated["slow_period"] == 50


def test_validate_parameters_out_of_bounds() -> None:
    """Parameter violating min/max bounds must raise InvalidStrategyParameterError."""
    with pytest.raises(InvalidStrategyParameterError, match="cannot be less than minimum"):
        StrategyRegistry.validate_parameters("trend_following", {"fast_period": 1})

    with pytest.raises(InvalidStrategyParameterError, match="cannot exceed maximum"):
        StrategyRegistry.validate_parameters("trend_following", {"fast_period": 101})


def test_validate_parameters_nan_inf_rejected() -> None:
    """NaN and Inf float parameters must be rejected."""
    with pytest.raises(InvalidStrategyParameterError, match="cannot be NaN or Infinity"):
        StrategyRegistry.validate_parameters("mean_reversion", {"entry_threshold": float("nan")})

    with pytest.raises(InvalidStrategyParameterError, match="cannot be NaN or Infinity"):
        StrategyRegistry.validate_parameters("mean_reversion", {"entry_threshold": float("inf")})


def test_validate_parameters_type_mismatch() -> None:
    """Invalid types that cannot be coerced must raise InvalidStrategyParameterError."""
    with pytest.raises(InvalidStrategyParameterError, match="must be an integer"):
        StrategyRegistry.validate_parameters("trend_following", {"fast_period": "abc"})

    with pytest.raises(InvalidStrategyParameterError, match="Unknown parameters"):
        StrategyRegistry.validate_parameters("trend_following", {"unrecognized_param": 123})


def test_create_strategy_factory() -> None:
    """Factory must instantiate working strategy instance with parameters."""
    strategy = StrategyRegistry.create_strategy(
        strategy_id="trend_following",
        parameters={"fast_period": 12, "slow_period": 26},
        symbols=["EUR/USD"],
    )
    assert strategy is not None
    assert strategy.strategy_id == "trend_following"
    assert hasattr(strategy, "generate_signal")
