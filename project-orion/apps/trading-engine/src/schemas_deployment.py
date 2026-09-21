"""Pydantic v2 schemas for the Strategy Deployment Pipeline & Paper Incubator."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

# ── Request Schemas ──────────────────────────────────────────────────

class PromoteFromOptimizationRequest(BaseModel):
    """Request to promote an optimization top candidate into paper incubation."""

    optimization_job_id: str = Field(..., description="ID of completed optimization job")
    candidate_rank: int = Field(1, ge=1, le=50, description="Rank of candidate to promote (1 = best)")
    symbol: str | None = Field(None, description="Override symbol (defaults to optimization symbol)")
    timeframe: str | None = Field(None, description="Override timeframe (defaults to optimization timeframe)")
    initial_capital: Decimal = Field(Decimal("10000.00"), gt=Decimal(0), description="Initial paper incubation capital")
    incubation_duration_days: int = Field(7, ge=1, le=365, description="Target incubation observation days")
    min_trade_count: int = Field(10, ge=1, le=1000, description="Minimum paper trades required to validate")
    max_drawdown_pct: float = Field(20.0, gt=0.0, le=100.0, description="Maximum paper drawdown tolerated")
    enforce_separation_of_duties: bool = Field(False, description="Enforce that actor cannot self-approve deployment")


class PromoteFromExperimentRequest(BaseModel):
    """Request to promote a research backtest experiment into paper incubation."""

    experiment_id: str = Field(..., description="ID of completed research experiment")
    initial_capital: Decimal = Field(Decimal("10000.00"), gt=Decimal(0), description="Initial paper incubation capital")
    incubation_duration_days: int = Field(7, ge=1, le=365, description="Target incubation observation days")
    min_trade_count: int = Field(10, ge=1, le=1000, description="Minimum paper trades required to validate")
    max_drawdown_pct: float = Field(20.0, gt=0.0, le=100.0, description="Maximum paper drawdown tolerated")
    enforce_separation_of_duties: bool = Field(False, description="Enforce that actor cannot self-approve deployment")


class TransitionDeploymentRequest(BaseModel):
    """Request to transition deployment lifecycle status."""

    reason: str = Field("", description="Audit justification for the state transition")


# ── Quality Gate Schemas ─────────────────────────────────────────────

class QualityGateResultSchema(BaseModel):
    """Single quality gate evaluation result schema."""

    gate_type: str
    verdict: str  # PASS, FAIL, INCONCLUSIVE, INSUFFICIENT_DATA
    actual_value: float | None = None
    threshold: float | None = None
    details: str
    evaluated_at: str


class QualityGateReportSchema(BaseModel):
    """Aggregate quality gate report schema."""

    all_passed: bool
    summary_verdict: str  # PASS, FAIL, INCONCLUSIVE, INSUFFICIENT_DATA
    gate_results: list[QualityGateResultSchema]
    evaluated_at: str


# ── Incubation & Benchmark Schemas ───────────────────────────────────

class IncubationConfigSchema(BaseModel):
    """Incubation policy configuration schema."""

    min_duration_days: int
    min_trade_count: int
    max_drawdown_pct: float
    daily_loss_limit_pct: float
    risk_violation_limit: int
    performance_deviation_threshold_pct: float
    initial_capital: str
    require_market_data_quality: bool
    evaluation_mode: str


class IncubationMetricsSchema(BaseModel):
    """Incubation performance metrics schema."""

    net_pnl: str
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    profit_factor: float
    daily_loss_violations: int
    risk_violations: int
    trading_days: int
    data_quality_score: float


class BenchmarkComparisonSchema(BaseModel):
    """Side-by-side benchmark comparison schema."""

    backtest_return_pct: float
    paper_return_pct: float
    return_ratio: float
    backtest_sharpe: float
    paper_sharpe: float
    sharpe_diff: float
    backtest_max_dd_pct: float
    paper_max_dd_pct: float
    drawdown_diff: float
    backtest_win_rate_pct: float
    paper_win_rate_pct: float
    backtest_trades: int
    paper_trades: int
    deviation_acceptable: bool


class DeploymentTransitionRecordSchema(BaseModel):
    """Audit record for a lifecycle transition."""

    from_status: str
    to_status: str
    actor_id: str
    actor_role: str | None
    timestamp: str
    reason: str
    authorization: str
    validation_passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


# ── Response Schemas ─────────────────────────────────────────────────

class DeploymentSummaryResponse(BaseModel):
    """Summary of a strategy deployment for list views."""

    id: str
    organization_id: str
    created_by: str | None
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    status: str
    initial_capital: Decimal
    promotion_verdict: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source_optimization_id: str | None = None
    source_experiment_id: str | None = None


class DeploymentDetailResponse(BaseModel):
    """Complete detail of a strategy deployment."""

    id: str
    organization_id: str
    created_by: str | None
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    status: str
    parameters: dict[str, Any]
    evidence_chain: dict[str, Any]
    initial_capital: Decimal
    quality_gate_policy: dict[str, Any] | None = None
    quality_gate_results: dict[str, Any] | None = None
    incubation_config: dict[str, Any]
    incubation_metrics: dict[str, Any] | None = None
    benchmark_comparison: dict[str, Any] | None = None
    backtest_benchmark: dict[str, Any] | None = None
    promotion_verdict: str
    transition_history: list[dict[str, Any]] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    warnings: list[str] | None = None
    source_optimization_id: str | None = None
    source_experiment_id: str | None = None


class DeploymentListResponse(BaseModel):
    """Paginated list response of strategy deployments."""

    items: list[DeploymentSummaryResponse]
    total: int
    limit: int
    offset: int
