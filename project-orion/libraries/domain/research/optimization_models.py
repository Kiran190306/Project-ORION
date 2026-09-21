"""Institutional domain models for quantitative strategy optimization and walk-forward research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Any


def _frozen_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(values or {}))


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _finite(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be finite")


class OptimizationType(StrEnum):
    """Type of optimization procedure executed."""

    GRID_SEARCH = "GRID_SEARCH"
    RANDOM_SEARCH = "RANDOM_SEARCH"
    WALK_FORWARD = "WALK_FORWARD"


class OptimizationStatus(StrEnum):
    """Lifecycle status of an optimization job."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class FitnessObjective(StrEnum):
    """Primary quantitative objective metric to maximize or minimize."""

    SHARPE_RATIO = "SHARPE_RATIO"
    SORTINO_RATIO = "SORTINO_RATIO"
    CALMAR_RATIO = "CALMAR_RATIO"
    PROFIT_FACTOR = "PROFIT_FACTOR"
    TOTAL_RETURN = "TOTAL_RETURN"
    WIN_RATE = "WIN_RATE"
    MIN_DRAWDOWN = "MIN_DRAWDOWN"
    COMPOSITE = "COMPOSITE"


class ParameterType(StrEnum):
    """Primitive type of a strategy parameter."""

    INT = "int"
    FLOAT = "float"
    CHOICE = "choice"


class WalkForwardRobustness(StrEnum):
    """Institutional verdict on Walk-Forward Efficiency (WFE)."""

    ROBUST = "ROBUST"          # WFE >= 60%
    MODERATE = "MODERATE"      # 40% <= WFE < 60%
    OVERFITTED = "OVERFITTED"  # WFE < 40% or negative OOS
    UNDEFINED = "UNDEFINED"    # Insufficient trades or variance


class OptimizationWarningCode(StrEnum):
    """Standardized institutional warnings emitted during optimization."""

    COMBINATORIAL_EXPLOSION_RISK = "COMBINATORIAL_EXPLOSION_RISK"
    PARAMETER_CLIFF = "PARAMETER_CLIFF"
    SEVERE_OVERFITTING_WFE = "SEVERE_OVERFITTING_WFE"
    REGIME_OVERCONCENTRATION = "REGIME_OVERCONCENTRATION"
    INSUFFICIENT_OUT_OF_SAMPLE_TRADES = "INSUFFICIENT_OUT_OF_SAMPLE_TRADES"
    ZERO_VARIANCE_SURFACE = "ZERO_VARIANCE_SURFACE"


@dataclass(frozen=True, slots=True)
class ParameterRange:
    """Defined search range for a single strategy parameter."""

    name: str
    param_type: ParameterType
    min_value: float | int | str
    max_value: float | int | str
    step: float | int | None = None
    choices: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        _required(self.name, "name")
        if self.param_type in (ParameterType.INT, ParameterType.FLOAT):
            if not isinstance(self.min_value, (int, float)) or not isinstance(self.max_value, (int, float)):
                raise ValueError(f"Numeric parameter {self.name} requires numeric min_value and max_value")
            if self.min_value > self.max_value:
                raise ValueError(f"min_value ({self.min_value}) cannot exceed max_value ({self.max_value}) for {self.name}")
            if self.step is not None and self.step <= 0:
                raise ValueError(f"step must be strictly positive for parameter {self.name}")


@dataclass(frozen=True, slots=True)
class ParameterSpaceDefinition:
    """Collection of parameter ranges defining the searchable hypervolume."""

    strategy_id: str
    ranges: tuple[ParameterRange, ...]

    def __post_init__(self) -> None:
        _required(self.strategy_id, "strategy_id")
        if not self.ranges:
            raise ValueError("Parameter space must define at least one parameter range")
        names = {r.name for r in self.ranges}
        if len(names) != len(self.ranges):
            raise ValueError("Duplicate parameter names detected in parameter space")


@dataclass(frozen=True, slots=True)
class OptimizationCandidate:
    """An individual parameter combination evaluated during optimization."""

    rank: int
    parameters: Mapping[str, Any]
    fitness_score: float
    total_return: Decimal
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    net_pnl: Decimal

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("Candidate rank must be positive")
        _finite(self.fitness_score, "fitness_score")
        _finite(self.sharpe_ratio, "sharpe_ratio")
        _finite(self.sortino_ratio, "sortino_ratio")
        _finite(self.calmar_ratio, "calmar_ratio")
        _finite(self.max_drawdown, "max_drawdown")
        _finite(self.win_rate, "win_rate")
        _finite(self.profit_factor, "profit_factor")
        object.__setattr__(self, "parameters", _frozen_mapping(self.parameters))


@dataclass(frozen=True, slots=True)
class WalkForwardWindowResult:
    """Results for a single In-Sample / Out-of-Sample window pair."""

    window_index: int
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    optimal_parameters: Mapping[str, Any]
    is_metrics: Mapping[str, Any]
    oos_metrics: Mapping[str, Any]
    is_return: Decimal
    oos_return: Decimal
    efficiency_ratio: float | None  # None if IS return <= 0 (WFE mathematically undefined)
    oos_equity_curve: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.window_index < 0:
            raise ValueError("window_index cannot be negative")
        if self.is_start >= self.is_end:
            raise ValueError(f"is_start ({self.is_start}) must be before is_end ({self.is_end})")
        if self.is_end > self.oos_start:
            raise ValueError(f"is_end ({self.is_end}) cannot overlap with oos_start ({self.oos_start})")
        if self.oos_start >= self.oos_end:
            raise ValueError(f"oos_start ({self.oos_start}) must be before oos_end ({self.oos_end})")
        if self.efficiency_ratio is not None:
            _finite(self.efficiency_ratio, "efficiency_ratio")
        object.__setattr__(self, "optimal_parameters", _frozen_mapping(self.optimal_parameters))
        object.__setattr__(self, "is_metrics", _frozen_mapping(self.is_metrics))
        object.__setattr__(self, "oos_metrics", _frozen_mapping(self.oos_metrics))


@dataclass(frozen=True, slots=True)
class WalkForwardAnalysisResult:
    """Aggregated results across all walk-forward windows."""

    total_windows: int
    windows: tuple[WalkForwardWindowResult, ...]
    mean_wfe: float | None
    annualized_oos_return: Decimal
    annualized_oos_sharpe: float
    robustness_verdict: WalkForwardRobustness
    concatenated_oos_equity: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.total_windows < 1:
            raise ValueError("total_windows must be at least 1")
        if self.mean_wfe is not None:
            _finite(self.mean_wfe, "mean_wfe")
        _finite(self.annualized_oos_sharpe, "annualized_oos_sharpe")


@dataclass(frozen=True, slots=True)
class RegimePerformanceBreakdown:
    """Strategy performance partitioned into market regime segments."""

    regime_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    total_return: Decimal
    sharpe_ratio: float
    drawdown: float

    def __post_init__(self) -> None:
        _required(self.regime_name, "regime_name")
        _finite(self.win_rate, "win_rate")
        _finite(self.profit_factor, "profit_factor")
        _finite(self.sharpe_ratio, "sharpe_ratio")
        _finite(self.drawdown, "drawdown")


@dataclass(frozen=True, slots=True)
class ParameterStabilityAnalysis:
    """Sensitivity and parameter plateau analysis around the optimal configuration."""

    optimal_parameters: Mapping[str, Any]
    plateau_stability_score: float  # [0.0..1.0] where 1.0 = perfect plateau
    max_neighbor_drop_pct: float    # Drop in objective across adjacent parameter grid points
    is_cliff: bool                  # True if drop exceeds safety threshold
    cliff_details: str
    adjacent_evaluations: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        _finite(self.plateau_stability_score, "plateau_stability_score")
        _finite(self.max_neighbor_drop_pct, "max_neighbor_drop_pct")
        if not 0.0 <= self.plateau_stability_score <= 1.0:
            raise ValueError("plateau_stability_score must be bounded between 0.0 and 1.0")
        object.__setattr__(self, "optimal_parameters", _frozen_mapping(self.optimal_parameters))


@dataclass(frozen=True, slots=True)
class SensitivityHeatmapPoint:
    """A single cell in a 2D parameter sensitivity surface."""

    param1_value: float | int
    param2_value: float | int
    sharpe_ratio: float
    total_return: float
    drawdown: float
    fitness_score: float


@dataclass(frozen=True, slots=True)
class SensitivityHeatmapMatrix:
    """2D sensitivity matrix for visual surface plotting."""

    param1_name: str
    param2_name: str
    points: tuple[SensitivityHeatmapPoint, ...]
    min_fitness: float
    max_fitness: float


@dataclass(frozen=True, slots=True)
class OptimizationJob:
    """High-level aggregate root representing an optimization study."""

    id: str
    organization_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    optimization_type: OptimizationType
    fitness_objective: FitnessObjective
    parameter_space: ParameterSpaceDefinition
    status: OptimizationStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str | None = None
    total_combinations: int = 0
    completed_combinations: int = 0
    execution_time_seconds: float = 0.0
    best_candidate: OptimizationCandidate | None = None
    top_candidates: tuple[OptimizationCandidate, ...] = ()
    walk_forward_result: WalkForwardAnalysisResult | None = None
    regime_breakdowns: tuple[RegimePerformanceBreakdown, ...] = ()
    stability_analysis: ParameterStabilityAnalysis | None = None
    heatmap: SensitivityHeatmapMatrix | None = None
    warnings: tuple[str, ...] = ()
    error_message: str | None = None
    completed_at: datetime | None = None
