"""Pydantic schemas for the Institutional Strategy Lab & Backtesting Research API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParameterSchemaResponse(BaseModel):
    """Parameter definition specification for a strategy."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    default: Any
    min: float | int | None = None
    max: float | int | None = None
    options: list[str] | None = None
    description: str = ""


class StrategyCatalogueItemResponse(BaseModel):
    """Registered strategy catalogue item."""

    model_config = ConfigDict(from_attributes=True)

    strategy_id: str
    name: str
    description: str
    category: str
    version: str
    is_deterministic: bool
    supported_instruments: list[str]
    supported_timeframes: list[str]
    parameters: list[ParameterSchemaResponse]


class CreateExperimentRequest(BaseModel):
    """Request payload to initiate a deterministic research backtest."""

    strategy_id: str = Field(..., description="ID of registered strategy")
    symbol: str = Field(..., description="Canonical trading symbol e.g. EUR/USD")
    timeframe: str = Field(..., description="Bar timeframe e.g. H1, M15")
    start_date: date = Field(..., description="Historical start date")
    end_date: date = Field(..., description="Historical end date")
    initial_capital: float = Field(default=10000.0, ge=100.0, le=10000000.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    spread_pips: float = Field(default=1.5, ge=0.0, le=50.0)
    adverse_slippage_pips: float = Field(default=0.5, ge=0.0, le=50.0)
    commission_per_lot: float = Field(default=7.0, ge=0.0, le=100.0)


class ResearchWarningResponse(BaseModel):
    """Advisory quant research warning."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    description: str
    severity: str


class ExperimentSummaryResponse(BaseModel):
    """Summary representation of a research experiment."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    status: str
    execution_time_seconds: float
    created_at: datetime
    completed_at: datetime | None = None
    metrics: dict[str, Any] | None = None
    warnings: list[dict[str, Any]] | None = None
    error_message: str | None = None


class ExperimentDetailResponse(ExperimentSummaryResponse):
    """Full experiment details including parameter configuration."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    simulation_config: dict[str, Any] = Field(default_factory=dict)


class EquityPointResponse(BaseModel):
    """Single equity curve point."""

    timestamp: str
    balance: float
    equity: float
    drawdown_pct: float


class ExperimentEquityResponse(BaseModel):
    """Time-series equity curve for chart rendering."""

    experiment_id: str
    initial_capital: float
    points: list[EquityPointResponse]


class TradeRecordResponse(BaseModel):
    """Executed backtest trade record."""

    trade_id: str
    symbol: str
    side: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    fees: float
    net_pnl: float
    duration_seconds: float
    exit_reason: str


class ExperimentTradesResponse(BaseModel):
    """Paged collection of executed trades."""

    experiment_id: str
    total_trades: int
    trades: list[TradeRecordResponse]


class CompareExperimentsRequest(BaseModel):
    """Request payload to compare multiple completed experiments."""

    experiment_ids: list[str] = Field(..., min_length=2, max_length=5)


class ExperimentComparisonResponse(BaseModel):
    """Side-by-side comparison matrix and normalized equity curves."""

    comparison: list[dict[str, Any]]
    normalized_curves: dict[str, list[dict[str, Any]]]
