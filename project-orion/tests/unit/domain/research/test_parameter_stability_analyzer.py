"""Unit tests for ParameterStabilityAnalyzer in EPIC-024."""

from decimal import Decimal

from libraries.domain.research.optimization_models import (
    OptimizationCandidate,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)
from libraries.domain.research.parameter_stability_analyzer import (
    ParameterStabilityAnalyzer,
)


def _make_candidate(rank: int, fast: int, slow: int, sharpe: float) -> OptimizationCandidate:
    return OptimizationCandidate(
        rank=rank,
        parameters={"fast_period": fast, "slow_period": slow},
        fitness_score=sharpe,
        total_return=Decimal("12.5"),
        sharpe_ratio=sharpe,
        sortino_ratio=1.5,
        calmar_ratio=1.2,
        max_drawdown=5.0,
        win_rate=0.55,
        profit_factor=1.8,
        total_trades=40,
        net_pnl=Decimal("1250.00"),
    )


def test_stability_robust_plateau():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 20, step=5),
        ParameterRange("slow_period", ParameterType.INT, 30, 40, step=5),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)

    best = _make_candidate(1, fast=15, slow=35, sharpe=2.0)
    neighbor_a = _make_candidate(2, fast=10, slow=35, sharpe=1.9)
    neighbor_b = _make_candidate(3, fast=20, slow=35, sharpe=1.85)
    neighbor_c = _make_candidate(4, fast=15, slow=30, sharpe=1.95)

    all_cands = [best, neighbor_a, neighbor_b, neighbor_c]

    report = ParameterStabilityAnalyzer.analyze_stability(best, all_cands, space)

    assert not report.is_cliff
    assert report.plateau_stability_score >= 0.80
    assert "ROBUST PARAMETER PLATEAU" in report.cliff_details
    assert len(report.adjacent_evaluations) == 3


def test_stability_parameter_cliff_detection():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 20, step=5),
        ParameterRange("slow_period", ParameterType.INT, 30, 40, step=5),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)

    best = _make_candidate(1, fast=15, slow=35, sharpe=2.5)
    # Neighbor with steep collapse
    cliff_neighbor = _make_candidate(2, fast=20, slow=35, sharpe=-0.5)

    all_cands = [best, cliff_neighbor]

    report = ParameterStabilityAnalyzer.analyze_stability(best, all_cands, space)

    assert report.is_cliff
    assert "PARAMETER CLIFF DETECTED" in report.cliff_details
    assert report.max_neighbor_drop_pct >= 40.0


def test_stability_no_neighbors():
    ranges = (
        ParameterRange("fast_period", ParameterType.INT, 10, 20, step=5),
    )
    space = ParameterSpaceDefinition("TrendFollowing", ranges)
    best = _make_candidate(1, fast=15, slow=35, sharpe=2.0)

    report = ParameterStabilityAnalyzer.analyze_stability(best, [best], space)

    assert not report.is_cliff
    assert report.plateau_stability_score == 0.5
    assert len(report.adjacent_evaluations) == 0
