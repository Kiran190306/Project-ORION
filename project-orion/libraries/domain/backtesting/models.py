"""Immutable data models for the Institutional Backtesting & Quantitative Research Laboratory.

Defines:
- Timeframe, ReplayMode, ReplayState enums
- BacktestConfig, ReplayConfig, SimulationConfig
- Order/Execution simulation models
- Portfolio snapshot models
- Walk-forward, Monte Carlo, Optimization models
- Scenario models
- Backtest event types
- Performance metrics categories
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ─── Enums ────────────────────────────────────────────────────────────────


class Timeframe(StrEnum):
    """Supported backtesting timeframes."""

    M1 = "m1"
    M5 = "m5"
    M15 = "m15"
    M30 = "m30"
    H1 = "h1"
    H4 = "h4"
    D1 = "d1"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReplayMode(StrEnum):
    """Replay mode for the replay engine."""

    TICK = "tick"
    CANDLE = "candle"
    ORDER = "order"
    TRADE = "trade"
    MARKET = "market"


class ReplayState(StrEnum):
    """State of the replay engine."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    SEEKING = "seeking"


class HistoricalDataSource(StrEnum):
    """Supported historical data source types."""

    CSV = "csv"
    PARQUET = "parquet"
    DATABASE = "database"
    DUCKDB = "duckdb"
    COMPRESSED = "compressed"
    STREAM = "stream"
    S3 = "s3"
    OBJECT_STORE = "object_store"


class OrderSimulationSide(StrEnum):
    """Side of a simulated order."""

    BUY = "buy"
    SELL = "sell"


class OrderSimulationType(StrEnum):
    """Type of a simulated order."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSimulationStatus(StrEnum):
    """Status of a simulated order."""

    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExecutionSimulationStatus(StrEnum):
    """Status of an execution simulation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class OptimizationAlgorithm(StrEnum):
    """Supported optimization algorithms."""

    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"  # Hook only — not implemented
    GENETIC = "genetic"  # Hook only — not implemented
    PARTICLE_SWARM = "particle_swarm"  # Hook only — not implemented
    REINFORCEMENT = "reinforcement"  # Hook only — not implemented


class OptimizationDirection(StrEnum):
    """Direction for optimization."""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class OptimizationConstraint(StrEnum):
    """Constraint types for optimization."""

    LESS_THAN = "lt"
    GREATER_THAN = "gt"
    BETWEEN = "between"
    EQUAL = "eq"


class MetricCategory(StrEnum):
    """Categories of performance metrics."""

    TRADE = "trade"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    EXECUTION = "execution"
    STATISTICAL = "statistical"


class ScenarioType(StrEnum):
    """Types of scenario that can be simulated."""

    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    SPREAD_SPIKE = "spread_spike"
    FLASH_CRASH = "flash_crash"
    NEWS_EVENT = "news_event"
    BROKER_DISCONNECT = "broker_disconnect"
    GAP_OPEN = "gap_open"
    NORMAL = "normal"


class ScenarioEffect(StrEnum):
    """Types of scenario effects that can be applied."""

    HIGH_VOLATILITY = "high_volatility"
    LOW_LIQUIDITY = "low_liquidity"
    SPREAD_SPIKE = "spread_spike"
    FLASH_CRASH = "flash_crash"
    NEWS_EVENT = "news_event"
    BROKER_DISCONNECT = "broker_disconnect"
    GAP_OPEN = "gap_open"
    SLIPPAGE_INCREASE = "slippage_increase"
    LATENCY_INCREASE = "latency_increase"
    COMMISSION_INCREASE = "commission_increase"


# ─── Backtest Event Types ─────────────────────────────────────────────────


class BacktestEventType(StrEnum):
    """Types of events emitted during backtesting."""

    MARKET_DATA = "market_data"
    SIGNAL = "signal"
    RISK = "risk"
    ORDER = "order"
    EXECUTION = "execution"
    PORTFOLIO = "portfolio"
    STATISTICS = "statistics"
    SCENARIO = "scenario"
    ENGINE = "engine"


# ─── Configuration Models ─────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Overall configuration for a backtest run."""

    name: str = "backtest"
    symbols: tuple[str, ...] = ()
    timeframes: tuple[Timeframe, ...] = (Timeframe.H1,)
    start_date: datetime | None = None
    end_date: datetime | None = None
    initial_balance: Decimal = Decimal("10000")
    base_currency: str = "USD"
    leverage_max: Decimal = Decimal("100")
    execution_mode: str = "simulation"
    random_seed: int | None = 42
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    """Configuration for the replay engine."""

    mode: ReplayMode = ReplayMode.CANDLE
    speed_multiplier: float = 1.0
    chunk_size: int = 10000
    streaming_mode: bool = True
    reverse_enabled: bool = False
    seek_enabled: bool = True
    publish_events: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Configuration for the simulation layer."""

    slippage_model: str = "default"
    spread_model: str = "default"
    commission_model: str = "default"
    swap_model: str = "default"
    latency_model: str = "default"
    liquidity_model: str = "default"
    market_impact_model: str = "default"
    partial_fills_enabled: bool = True
    broker_delay_enabled: bool = True
    max_slippage_bps: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CommissionConfig:
    """Commission configuration."""

    type: str = "fixed_per_lot"
    value: Decimal = Decimal("0")
    min_commission: Decimal = Decimal("0")
    max_commission: Decimal | None = None
    currency: str = "USD"


@dataclass(frozen=True, slots=True)
class SpreadConfig:
    """Spread configuration."""

    type: str = "fixed"
    value_pips: float = 0.0
    variable_factor: float = 0.0
    min_pips: float = 0.0
    max_pips: float = 100.0


@dataclass(frozen=True, slots=True)
class SlippageConfig:
    """Slippage configuration."""

    type: str = "fixed"
    value_bps: float = 0.0
    variable_factor: float = 0.0
    max_bps: float = 50.0
    random_seed: int | None = None


@dataclass(frozen=True, slots=True)
class SwapConfig:
    """Swap/overnight configuration."""

    long_rate: Decimal = Decimal("0")
    short_rate: Decimal = Decimal("0")
    charge_weekends: bool = False
    triple_swap_wednesday: bool = True


# ─── Order & Execution Models ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OrderSimulation:
    """A simulated order during backtesting."""

    order_id: str
    symbol: str
    side: OrderSimulationSide
    order_type: OrderSimulationType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    status: OrderSimulationStatus = OrderSimulationStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    rejection_reason: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    @property
    def is_finalized(self) -> bool:
        return self.status in (
            OrderSimulationStatus.FILLED,
            OrderSimulationStatus.REJECTED,
            OrderSimulationStatus.CANCELLED,
            OrderSimulationStatus.EXPIRED,
        )


@dataclass(frozen=True, slots=True)
class FillSimulation:
    """A single fill on a simulated order."""

    fill_id: str
    order_id: str
    symbol: str
    side: OrderSimulationSide
    quantity: Decimal
    price: Decimal
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    liquidity: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionSimulationResult:
    """Result of executing a simulated order."""

    order: OrderSimulation
    status: ExecutionSimulationStatus
    fills: tuple[FillSimulation, ...] = ()
    total_quantity: Decimal = Decimal("0")
    average_price: Decimal | None = None
    total_commission: Decimal = Decimal("0")
    total_swap: Decimal = Decimal("0")
    total_slippage: Decimal = Decimal("0")
    latency_ms: float = 0.0
    rejection_reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionSimulationStatus.SUCCESS

    @property
    def is_partial(self) -> bool:
        return self.status == ExecutionSimulationStatus.PARTIAL

    @property
    def is_failure(self) -> bool:
        return self.status in (
            ExecutionSimulationStatus.FAILURE,
            ExecutionSimulationStatus.REJECTED,
        )


# ─── Portfolio Models ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BalanceSnapshot:
    """Snapshot of account balance at a point in time."""

    timestamp: datetime
    balance: Decimal
    currency: str = "USD"

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "balance": float(self.balance),
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class EquitySnapshot:
    """Snapshot of account equity at a point in time."""

    timestamp: datetime
    equity: Decimal
    balance: Decimal
    unrealized_pnl: Decimal = Decimal("0")
    currency: str = "USD"

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "equity": float(self.equity),
            "balance": float(self.balance),
            "unrealized_pnl": float(self.unrealized_pnl),
            "currency": self.currency,
        }


@dataclass(frozen=True, slots=True)
class DrawdownSnapshot:
    """Drawdown snapshot for tracking peak-to-trough."""

    timestamp: datetime
    current_drawdown: float = 0.0  # % from peak
    max_drawdown: float = 0.0
    peak_equity: Decimal = Decimal("0")
    current_equity: Decimal = Decimal("0")

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "current_drawdown_pct": self.current_drawdown,
            "max_drawdown_pct": self.max_drawdown,
            "peak_equity": float(self.peak_equity),
            "current_equity": float(self.current_equity),
        }


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Complete portfolio snapshot at a point in time."""

    timestamp: datetime
    balance: Decimal
    equity: Decimal
    margin_used: Decimal = Decimal("0")
    free_margin: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_swap: Decimal = Decimal("0")
    gross_exposure: Decimal = Decimal("0")
    net_exposure: Decimal = Decimal("0")
    position_count: int = 0
    portfolio_heat: float = 0.0  # 0–100
    drawdown: DrawdownSnapshot | None = None

    @property
    def margin_level_pct(self) -> float:
        if self.margin_used > 0:
            return float(self.equity / self.margin_used * 100)
        return float("inf")

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "balance": float(self.balance),
            "equity": float(self.equity),
            "margin_used": float(self.margin_used),
            "free_margin": float(self.free_margin),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "total_commission": float(self.total_commission),
            "total_swap": float(self.total_swap),
            "gross_exposure": float(self.gross_exposure),
            "net_exposure": float(self.net_exposure),
            "position_count": self.position_count,
            "portfolio_heat": self.portfolio_heat,
            "margin_level_pct": self.margin_level_pct,
            "drawdown": self.drawdown.as_dict if self.drawdown else None,
        }


# ─── Backtest Event ───────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BacktestEvent:
    """Generic event emitted during backtesting.

    The engine is fully event-driven. Components publish events
    and consume events through the BacktestEventPublisher interface.
    """

    event_id: str
    event_type: BacktestEventType
    symbol: str
    timestamp: datetime
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MarketEvent(BacktestEvent):
    """Event emitted when market data is replayed."""

    pass  # Inherits all from BacktestEvent with event_type=MARKET_DATA


# ─── Performance Metrics ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TradeMetrics:
    """Trade-specific performance metrics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    expectancy: float = 0.0
    avg_bars_held: float = 0.0


@dataclass(frozen=True, slots=True)
class PortfolioMetrics:
    """Portfolio-level performance metrics."""

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    sterling_ratio: float = 0.0
    omega_ratio: float = 0.0
    ulcer_index: float = 0.0
    recovery_factor: float = 0.0
    return_pct: float = 0.0
    annualized_return: float = 0.0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    r_squared: float = 0.0


@dataclass(frozen=True, slots=True)
class RiskMetrics:
    """Risk-specific performance metrics."""

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    current_drawdown: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    var_99: float = 0.0  # Value at Risk 99%
    cvar_95: float = 0.0  # Conditional VaR 95%
    volatility: float = 0.0
    downside_volatility: float = 0.0
    kelly_criterion: float = 0.0
    risk_of_ruin: float = 0.0
    ulcer_performance_index: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionMetrics:
    """Execution-specific performance metrics."""

    total_orders: int = 0
    filled_orders: int = 0
    partial_fills: int = 0
    rejected_orders: int = 0
    cancelled_orders: int = 0
    average_slippage_bps: float = 0.0
    max_slippage_bps: float = 0.0
    average_commission: float = 0.0
    total_commission: float = 0.0
    average_latency_ms: float = 0.0
    fill_rate: float = 0.0
    average_fill_time_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class StatisticalMetrics:
    """Statistical performance metrics."""

    skewness: float = 0.0
    kurtosis: float = 0.0
    gain_to_pain_ratio: float = 0.0
    profit_per_bar: float = 0.0
    profit_per_day: float = 0.0
    profit_per_month: float = 0.0
    avg_daily_volatility: float = 0.0
    avg_weekly_volatility: float = 0.0
    correlation_to_benchmark: float = 0.0
    alpha: float = 0.0
    beta: float = 1.0
    treynor_ratio: float = 0.0
    information_ratio: float = 0.0


@dataclass(frozen=True, slots=True)
class ResearchMetrics:
    """Research-specific aggregated metrics."""

    total_walk_forward_runs: int = 0
    total_monte_carlo_runs: int = 0
    total_optimization_runs: int = 0
    walk_forward_robustness: float = 0.0
    parameter_stability: float = 0.0
    strategy_quality_score: float = 0.0


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Complete set of performance metrics."""

    trade_metrics: TradeMetrics = field(default_factory=TradeMetrics)
    portfolio_metrics: PortfolioMetrics = field(default_factory=PortfolioMetrics)
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    execution_metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    statistical_metrics: StatisticalMetrics = field(default_factory=StatisticalMetrics)
    research_metrics: ResearchMetrics = field(default_factory=ResearchMetrics)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "trade": {
                "total_trades": self.trade_metrics.total_trades,
                "win_rate": self.trade_metrics.win_rate,
                "profit_factor": self.trade_metrics.profit_factor,
                "net_profit": self.trade_metrics.net_profit,
            },
            "portfolio": {
                "sharpe_ratio": self.portfolio_metrics.sharpe_ratio,
                "sortino_ratio": self.portfolio_metrics.sortino_ratio,
                "calmar_ratio": self.portfolio_metrics.calmar_ratio,
                "return_pct": self.portfolio_metrics.return_pct,
            },
            "risk": {
                "max_drawdown_pct": self.risk_metrics.max_drawdown_pct,
                "var_95": self.risk_metrics.var_95,
                "volatility": self.risk_metrics.volatility,
            },
            "execution": {
                "fill_rate": self.execution_metrics.fill_rate,
                "average_slippage_bps": self.execution_metrics.average_slippage_bps,
                "total_commission": self.execution_metrics.total_commission,
            },
        }


# ─── Walk Forward Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class WalkForwardConfig:
    """Configuration for walk-forward analysis."""

    training_window_days: int = 252
    validation_window_days: int = 63
    step_size_days: int = 21
    window_type: str = "rolling"  # rolling or anchored
    min_samples: int = 100
    random_seed: int | None = 42
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WalkForwardResult:
    """Result of a single walk-forward window."""

    window_index: int
    training_start: datetime
    training_end: datetime
    validation_start: datetime
    validation_end: datetime
    in_sample_metrics: PerformanceMetrics | None = None
    out_of_sample_metrics: PerformanceMetrics | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    robustness_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Aggregated evaluation result with in/out-of-sample comparison."""

    in_sample: PerformanceMetrics | None = None
    out_of_sample: PerformanceMetrics | None = None
    robustness_score: float = 0.0
    parameter_stability: float = 0.0
    walk_forward_results: tuple[WalkForwardResult, ...] = ()


# ─── Monte Carlo Models ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation."""

    num_simulations: int = 1000
    random_seed: int | None = 42
    randomize_trade_ordering: bool = True
    randomize_trade_removal: bool = False
    spread_variation: bool = True
    slippage_variation: bool = True
    execution_delay_variation: bool = False
    confidence_intervals: tuple[float, ...] = (0.95, 0.99)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MonteCarloResult:
    """Result of a Monte Carlo simulation."""

    num_simulations: int = 0
    simulation_type: str = ""
    median: float = 0.0
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    pct_positive: float = 0.0
    median_final_equity: float = 0.0
    mean_final_equity: float = 0.0
    std_final_equity: float = 0.0
    min_final_equity: float = 0.0
    max_final_equity: float = 0.0
    prob_profit: float = 0.0
    prob_ruin: float = 0.0
    median_max_drawdown: float = 0.0
    mean_max_drawdown: float = 0.0
    ci_lower_95: float = 0.0
    ci_upper_95: float = 0.0
    ci_lower_99: float = 0.0
    ci_upper_99: float = 0.0
    equity_curves: tuple[tuple[float, ...], ...] = ()
    random_seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Optimization Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OptimizationConfig:
    """Configuration for parameter optimization."""

    algorithm: OptimizationAlgorithm = OptimizationAlgorithm.GRID_SEARCH
    direction: OptimizationDirection = OptimizationDirection.MAXIMIZE
    metric: str = "sharpe_ratio"
    parameters: dict[str, list[Any]] = field(default_factory=dict)
    max_iterations: int = 1000
    random_seed: int | None = 42
    parallel: bool = False
    n_jobs: int = 1
    early_stopping: bool = False
    early_stopping_rounds: int = 10
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Result of a parameter optimization run."""

    best_params: dict[str, Any] = field(default_factory=dict)
    best_score: float = 0.0
    all_scores: dict[str, float] = field(default_factory=dict)
    iterations_run: int = 0
    total_iterations: int = 0
    algorithm: OptimizationAlgorithm = OptimizationAlgorithm.GRID_SEARCH
    direction: OptimizationDirection = OptimizationDirection.MAXIMIZE
    metric: str = "sharpe_ratio"
    random_seed: int | None = None
    execution_time_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Scenario Models ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    """Configuration for a scenario to apply during backtesting."""

    name: str
    effects: tuple[ScenarioEffect, ...] = ()
    start_delay_bars: int = 0
    duration_bars: int = 0
    intensity: float = 1.0  # 0.0–1.0 multiplier
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Result of applying a scenario."""

    scenario_name: str
    effects: tuple[ScenarioEffect, ...]
    normal_metrics: PerformanceMetrics | None = None
    scenario_metrics: PerformanceMetrics | None = None
    impact_score: float = 0.0  # How much the scenario affected performance
    survived: bool = True
    max_drawdown_during_scenario: float = 0.0
    pnl_during_scenario: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ─── Research Database Record ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Result of a completed backtest run.

    Encapsulates the full output of a backtest including performance
    metrics, equity curve, and trade statistics.
    """

    success: bool = True
    symbol: str = ""
    timeframe: Timeframe = Timeframe.H1
    start_date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    end_date: date = field(default_factory=lambda: datetime.now(timezone.utc).date())
    initial_balance: Decimal = Decimal("10000")
    final_balance: Decimal = Decimal("10000")
    net_profit: Decimal = Decimal("0")
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    performance: PerformanceMetrics | None = None
    equity_curve: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BacktestRunRecord:
    """Record of a completed backtest run, stored in the research database."""

    run_id: str
    config: BacktestConfig
    performance: PerformanceMetrics | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    status: str = "pending"
    error: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    trades: tuple[OrderSimulation, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
