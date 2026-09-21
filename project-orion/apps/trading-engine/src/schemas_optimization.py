"""Pydantic schemas for quantitative strategy optimization and walk-forward research."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParameterRangeSchema(BaseModel):
    """Schema for defining a searchable parameter range."""

    name: str = Field(..., description="Parameter name as defined in strategy archetype")
    param_type: str = Field(..., description="'int', 'float', or 'choice'")
    min_value: float | int | str = Field(..., description="Minimum searchable value")
    max_value: float | int | str = Field(..., description="Maximum searchable value")
    step: float | int | None = Field(default=None, description="Increment step for grid search")
    choices: list[Any] | None = Field(default=None, description="Discrete options for choice parameter")


class ParameterSpaceRequest(BaseModel):
    """Schema for custom parameter space configuration."""

    strategy_id: str = Field(..., description="Target strategy archetype ID")
    ranges: list[ParameterRangeSchema] = Field(..., description="Parameter search ranges")


class OptimizationRunRequest(BaseModel):
    """Request payload to launch a Grid or Random Search optimization sweep."""

    strategy_id: str = Field(..., description="Strategy archetype ID")
    symbol: str = Field(default="EUR/USD", description="Currency pair symbol")
    timeframe: str = Field(default="H1", description="Bar timeframe: M1, M5, M15, H1, D1")
    start_date: datetime = Field(..., description="Start of historical backtest window (UTC)")
    end_date: datetime = Field(..., description="End of historical backtest window (UTC)")
    initial_capital: Decimal = Field(default=Decimal("10000.00"), description="Starting capital in base currency")
    optimization_type: str = Field(default="GRID_SEARCH", description="'GRID_SEARCH' or 'RANDOM_SEARCH'")
    fitness_objective: str = Field(default="SHARPE_RATIO", description="Metric to maximize (SHARPE_RATIO, SORTINO_RATIO, etc.)")
    parameter_space: ParameterSpaceRequest | None = Field(default=None, description="Custom parameter ranges, or null for defaults")
    max_combinations: int = Field(default=300, description="Hard cap on combinations evaluated")
    n_samples: int = Field(default=50, description="Number of candidate iterations for RANDOM_SEARCH")
    random_seed: int = Field(default=42, description="Reproducible random seed")
    spread_pips: Decimal = Field(default=Decimal("1.5"), description="Simulated bid/ask spread in pips")
    slippage_pips: Decimal = Field(default=Decimal("0.5"), description="Simulated adverse execution slippage in pips")
    commission: Decimal = Field(default=Decimal("7.00"), description="Round-turn commission per standard lot")


class WalkForwardRunRequest(BaseModel):
    """Request payload to launch an institutional Walk-Forward Analysis (WFA)."""

    strategy_id: str = Field(..., description="Strategy archetype ID")
    symbol: str = Field(default="EUR/USD", description="Currency pair symbol")
    timeframe: str = Field(default="H1", description="Bar timeframe: M1, M5, M15, H1, D1")
    start_date: datetime = Field(..., description="Start of historical backtest window (UTC)")
    end_date: datetime = Field(..., description="End of historical backtest window (UTC)")
    initial_capital: Decimal = Field(default=Decimal("10000.00"), description="Starting capital")
    n_windows: int = Field(default=4, ge=2, le=10, description="Number of rolling/anchored walk-forward windows")
    in_sample_ratio: float = Field(default=0.70, ge=0.50, le=0.85, description="Fraction of window dedicated to In-Sample optimization")
    anchored: bool = Field(default=False, description="True for expanding/anchored window, False for rolling window")
    fitness_objective: str = Field(default="SHARPE_RATIO", description="Objective to optimize inside each IS window")
    parameter_space: ParameterSpaceRequest | None = Field(default=None, description="Custom parameter space or null for defaults")
    max_combinations_per_window: int = Field(default=100, description="Combinations evaluated per IS window")
    spread_pips: Decimal = Field(default=Decimal("1.5"))
    slippage_pips: Decimal = Field(default=Decimal("0.5"))
    commission: Decimal = Field(default=Decimal("7.00"))


class OptimizationCandidateResponse(BaseModel):
    """Schema for an individual evaluated parameter set."""

    rank: int
    parameters: dict[str, Any]
    fitness_score: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    net_pnl: float

    model_config = ConfigDict(from_attributes=True)


class WalkForwardWindowResponse(BaseModel):
    """Schema for a single In-Sample / Out-of-Sample window evaluation."""

    window_index: int
    is_start: datetime
    is_end: datetime
    oos_start: datetime
    oos_end: datetime
    optimal_parameters: dict[str, Any]
    is_metrics: dict[str, Any]
    oos_metrics: dict[str, Any]
    is_return: float
    oos_return: float
    efficiency_ratio: float | None
    oos_equity_curve: list[dict[str, Any]] = Field(default_factory=list)


class WalkForwardAnalysisResponse(BaseModel):
    """Schema for aggregated Walk-Forward Analysis results."""

    total_windows: int
    windows: list[WalkForwardWindowResponse]
    mean_wfe: float | None
    annualized_oos_return: float
    annualized_oos_sharpe: float
    robustness_verdict: str
    concatenated_oos_equity: list[dict[str, Any]]
    warnings: list[str]


class RegimeBreakdownResponse(BaseModel):
    """Schema for performance breakdown across a market regime."""

    regime_name: str
    trade_count: int
    win_rate: float
    profit_factor: float
    total_return: float
    sharpe_ratio: float
    drawdown: float


class ParameterStabilityResponse(BaseModel):
    """Schema for parameter plateau and cliff analysis."""

    optimal_parameters: dict[str, Any]
    plateau_stability_score: float
    max_neighbor_drop_pct: float
    is_cliff: bool
    cliff_details: str
    adjacent_evaluations: list[dict[str, Any]]


class SensitivityHeatmapResponse(BaseModel):
    """Schema for 2D parameter sensitivity surface plotting."""

    param1_name: str
    param2_name: str
    min_fitness: float
    max_fitness: float
    points: list[dict[str, Any]]


class OptimizationJobSummaryResponse(BaseModel):
    """Compact summary schema for optimization job lists."""

    id: str
    organization_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    optimization_type: str
    fitness_objective: str
    status: str
    total_combinations: int
    completed_combinations: int
    execution_time_seconds: float
    best_parameters: dict[str, Any] | None = None
    best_fitness_score: float | None = None
    best_sharpe: float | None = None
    best_return: float | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class OptimizationJobDetailResponse(BaseModel):
    """Full detail schema for an optimization job."""

    id: str
    organization_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    optimization_type: str
    fitness_objective: str
    parameter_space: dict[str, Any]
    optimization_config: dict[str, Any]
    status: str
    total_combinations: int
    completed_combinations: int
    execution_time_seconds: float
    best_parameters: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    top_candidates: list[OptimizationCandidateResponse] | None = None
    walk_forward_result: WalkForwardAnalysisResponse | None = None
    regime_breakdowns: list[RegimeBreakdownResponse] | None = None
    stability_analysis: ParameterStabilityResponse | None = None
    heatmap: SensitivityHeatmapResponse | None = None
    warnings: list[str] | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StrategyDefaultSpaceResponse(BaseModel):
    """Schema for default parameter space and bounds for a strategy archetype."""

    strategy_id: str
    ranges: list[ParameterRangeSchema]
    estimated_combinations: int
