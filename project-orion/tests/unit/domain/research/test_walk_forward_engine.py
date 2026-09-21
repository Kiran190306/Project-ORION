"""Unit tests for WalkForwardEngine in EPIC-024."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from libraries.domain.research.optimization_models import (
    FitnessObjective,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
    WalkForwardRobustness,
)
from libraries.domain.research.walk_forward_engine import WalkForwardEngine


def _generate_synthetic_candles(n: int = 250) -> list[dict[str, Any]]:
    base_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = []
    price = Decimal("1.1000")
    for i in range(n):
        delta = Decimal("0.0012") if (i % 8 < 5) else Decimal("-0.0009")
        o = price
        c = price + delta
        h = max(o, c) + Decimal("0.0004")
        l = min(o, c) - Decimal("0.0004")
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


def test_walk_forward_partitioning_chronology():
    candles = _generate_synthetic_candles(200)
    wfa = WalkForwardEngine()

    partitions = wfa._partition_windows(candles, n_windows=3, in_sample_ratio=0.7, anchored=False)
    assert len(partitions) >= 2

    for is_c, oos_c in partitions:
        assert len(is_c) > 0
        assert len(oos_c) > 0
        # Strict chronological separation
        assert is_c[-1]["timestamp"] <= oos_c[0]["timestamp"]


@pytest.mark.asyncio
async def test_walk_forward_run_analysis():
    candles = _generate_synthetic_candles(250)
    wfa = WalkForwardEngine()

    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 15, step=5),
        ParameterRange("slow_period", ParameterType.INT, 30, 35, step=5),
    )
    space = ParameterSpaceDefinition("trend_following", ranges)
    combos = [
        {"fast_period": 10, "slow_period": 30},
        {"fast_period": 15, "slow_period": 35},
    ]

    result = await wfa.run_analysis(
        strategy_id="TrendFollowing",
        space=space,
        candidate_combinations=combos,
        candles=candles,
        n_windows=3,
        in_sample_ratio=0.70,
        fitness_objective=FitnessObjective.SHARPE_RATIO,
    )

    assert result.total_windows >= 2
    assert len(result.windows) == result.total_windows
    assert result.robustness_verdict in (
        WalkForwardRobustness.ROBUST,
        WalkForwardRobustness.MODERATE,
        WalkForwardRobustness.OVERFITTED,
        WalkForwardRobustness.UNDEFINED,
    )
    assert len(result.concatenated_oos_equity) > 0


@pytest.mark.asyncio
async def test_walk_forward_insufficient_data():
    candles = _generate_synthetic_candles(30)
    wfa = WalkForwardEngine()
    space = ParameterSpaceDefinition(
        "trend_following",
        (ParameterRange("fast_period", ParameterType.INT, 10, 15, step=5),),
    )

    with pytest.raises(ValueError, match="Historical series has 30 candles; need at least"):
        await wfa.run_analysis(
            strategy_id="TrendFollowing",
            space=space,
            candidate_combinations=[{"fast_period": 10, "slow_period": 30}],
            candles=candles,
            n_windows=4,
        )
