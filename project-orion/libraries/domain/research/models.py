"""Institutional Strategy Lab and Quantitative Research domain models.

Provides immutable data structures, domain value objects, and lifecycle models
for research experiments, trade analytics, equity curves, and overfitting guards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ResearchExperimentStatus(StrEnum):
    """Lifecycle status of a quantitative research experiment."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DataSourceMode(StrEnum):
    """Source mode policy for historical market data sourcing."""

    EXTERNAL = "external"
    SYNTHETIC = "synthetic"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class DatasetProvenance:
    """Audit provenance describing the exact market dataset consumed by a backtest."""

    data_source: str  # "external" or "synthetic"
    provider: str  # e.g. "twelvedata", "mock_market_data", "deterministic_prng"
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    candle_count: int
    synthetic: bool
    deterministic: bool
    data_quality: str | None = None
    dataset_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize provenance to primitive dictionary representation."""
        return {
            "data_source": self.data_source,
            "provider": self.provider,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start": self.start.isoformat() if hasattr(self.start, "isoformat") else str(self.start),
            "end": self.end.isoformat() if hasattr(self.end, "isoformat") else str(self.end),
            "candle_count": self.candle_count,
            "synthetic": self.synthetic,
            "deterministic": self.deterministic,
            "data_quality": self.data_quality,
            "dataset_hash": self.dataset_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> DatasetProvenance | None:
        """Deserialize provenance from dictionary, returning None for legacy unpopulated records."""
        if not data:
            return None
        start_val = data.get("start")
        if isinstance(start_val, str):
            start_dt = datetime.fromisoformat(start_val)
        else:
            start_dt = start_val  # type: ignore[assignment]

        end_val = data.get("end")
        if isinstance(end_val, str):
            end_dt = datetime.fromisoformat(end_val)
        else:
            end_dt = end_val  # type: ignore[assignment]

        return cls(
            data_source=str(data.get("data_source", "unknown")),
            provider=str(data.get("provider", "unknown")),
            symbol=str(data.get("symbol", "")),
            timeframe=str(data.get("timeframe", "")),
            start=start_dt,
            end=end_dt,
            candle_count=int(data.get("candle_count", 0)),
            synthetic=bool(data.get("synthetic", False)),
            deterministic=bool(data.get("deterministic", False)),
            data_quality=data.get("data_quality"),
            dataset_hash=data.get("dataset_hash"),
        )


class WarningSeverity(StrEnum):
    """Severity of quantitative research warnings."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class ResearchWarning:
    """Advisory quant research warning explaining statistical caveats."""

    code: str
    title: str
    description: str
    severity: WarningSeverity = WarningSeverity.WARNING


OverfittingWarning = ResearchWarning


@dataclass(frozen=True, slots=True)
class EquityCurvePoint:
    """Single point along a simulated equity curve."""

    timestamp: datetime
    balance: Decimal
    equity: Decimal
    drawdown_pct: float


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """Historical trade execution record from backtest simulation."""

    trade_id: str
    symbol: str
    side: str  # BUY or SELL
    entry_time: datetime
    exit_time: datetime
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal
    duration_seconds: float
    exit_reason: str = "SIGNAL"  # SIGNAL, STOP_LOSS, TAKE_PROFIT, END_OF_DATA
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResearchPerformanceMetrics:
    """Comprehensive statistical performance metrics for a backtest experiment."""

    initial_capital: Decimal
    final_balance: Decimal
    net_profit: Decimal
    total_return_pct: float
    gross_profit: Decimal
    gross_loss: Decimal
    profit_factor: float
    win_rate_pct: float
    loss_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_pnl: Decimal
    largest_win: Decimal
    largest_loss: Decimal
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_seconds: float
    recovery_factor: float
    expectancy: Decimal


@dataclass(frozen=True, slots=True)
class ResearchExperiment:
    """Aggregated research experiment representing a deterministic backtest run."""

    id: str
    organization_id: str
    created_by: str
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    parameters: dict[str, Any]
    simulation_config: dict[str, Any]
    status: ResearchExperimentStatus = ResearchExperimentStatus.CREATED
    metrics: ResearchPerformanceMetrics | None = None
    equity_curve: list[EquityCurvePoint] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    warnings: list[ResearchWarning] = field(default_factory=list)
    error_message: str | None = None
    execution_time_seconds: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    provenance: DatasetProvenance | None = None
