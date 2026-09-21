"""Unit tests for OptimizationEngine in EPIC-024."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from libraries.domain.research.optimization_engine import OptimizationEngine
from libraries.domain.research.optimization_models import (
    FitnessObjective,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)


def _generate_synthetic_candles(n: int = 100) -> list[dict[str, Any]]:
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = []
    price = Decimal("1.1000")
    for i in range(n):
        delta = Decimal("0.0015") if (i % 6 < 4) else Decimal("-0.0010")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0005")
        l = min(o, c) - Decimal("0.0005")
        candles.append(
            {
                "timestamp": base_time + timedelta(hours=i),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": Decimal(1000),
            }
        )
        price = c
    return candles


@pytest.mark.asyncio
async def test_optimization_sweep_sharpe_ranking():
    candles = _generate_synthetic_candles(120)
    engine = OptimizationEngine()

    combos = [
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 15, "slow_period": 40},
        {"fast_period": 20, "slow_period": 50},
    ]

    candidates, _heatmap = await engine.run_sweep(
        strategy_id="TrendFollowing",
        parameter_combinations=combos,
        candles=candles,
        fitness_objective=FitnessObjective.SHARPE_RATIO,
    )

    assert len(candidates) == 3
    assert candidates[0].rank == 1
    assert candidates[1].rank == 2
    assert candidates[2].rank == 3
    # First candidate must have highest fitness score
    assert candidates[0].fitness_score >= candidates[1].fitness_score
    assert candidates[1].fitness_score >= candidates[2].fitness_score


@pytest.mark.asyncio
async def test_optimization_sweep_composite_ranking():
    candles = _generate_synthetic_candles(100)
    engine = OptimizationEngine()

    combos = [
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 15, "slow_period": 45},
    ]

    candidates, _ = await engine.run_sweep(
        strategy_id="TrendFollowing",
        parameter_combinations=combos,
        candles=candles,
        fitness_objective=FitnessObjective.COMPOSITE,
    )

    assert len(candidates) == 2
    assert candidates[0].rank == 1
    assert 0.0 <= candidates[0].fitness_score <= 1.0


@pytest.mark.asyncio
async def test_optimization_sweep_heatmap_generation():
    candles = _generate_synthetic_candles(100)
    engine = OptimizationEngine()

    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 20, step=10),
        ParameterRange("slow_period", ParameterType.INT, 30, 40, step=10),
    )
    space = ParameterSpaceDefinition("trend_following", ranges)

    combos = [
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 10, "slow_period": 40},
        {"fast_period": 20, "slow_period": 30},
        {"fast_period": 20, "slow_period": 40},
    ]

    _candidates, heatmap = await engine.run_sweep(
        strategy_id="trend_following",
        parameter_combinations=combos,
        candles=candles,
        fitness_objective=FitnessObjective.SHARPE_RATIO,
        parameter_space=space,
    )

    assert heatmap is not None
    assert heatmap.param1_name == "fast_period"
    assert heatmap.param2_name == "slow_period"
    assert len(heatmap.points) == 4


@pytest.mark.asyncio
async def test_optimization_sweep_cancellation():
    candles = _generate_synthetic_candles(100)
    engine = OptimizationEngine()

    combos = [
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 12, "slow_period": 32},
        {"fast_period": 14, "slow_period": 34},
    ]

    # Pre-cancel
    engine.cancel()
    with pytest.raises(RuntimeError, match="0 evaluated candidates"):
        await engine.run_sweep(
            strategy_id="TrendFollowing",
            parameter_combinations=combos,
            candles=candles,
        )
