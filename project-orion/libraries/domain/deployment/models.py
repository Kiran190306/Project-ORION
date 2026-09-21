"""Institutional Strategy Deployment Pipeline domain models.

Immutable, frozen dataclasses and value objects for the deployment
lifecycle, quality gate evaluation, incubation tracking, and
provenance evidence chain.

Quality gates produce four verdicts: PASS, FAIL, INCONCLUSIVE,
INSUFFICIENT_DATA — never implying guaranteed profitability.

EPIC-025 terminates at PAPER_VALIDATED or PROMOTION_CANDIDATE.
No live trading pathways exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

# ── Lifecycle Enums ──────────────────────────────────────────────────

class DeploymentStatus(StrEnum):
    """Lifecycle states for a strategy deployment.

    Terminal states: GATES_FAILED, INCUBATION_FAILED, CANCELLED,
    SUSPENDED, PROMOTION_CANDIDATE.
    """

    PENDING_GATES = "PENDING_GATES"
    GATES_PASSED = "GATES_PASSED"
    GATES_FAILED = "GATES_FAILED"
    INCUBATING = "INCUBATING"
    PAUSED = "PAUSED"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    INCUBATION_FAILED = "INCUBATION_FAILED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"
    PROMOTION_CANDIDATE = "PROMOTION_CANDIDATE"


class PromotionVerdict(StrEnum):
    """Outcome verdict for deployment promotion evaluation."""

    PENDING = "PENDING"
    PROMOTED = "PROMOTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ── Quality Gate Enums ───────────────────────────────────────────────

class QualityGateType(StrEnum):
    """Types of institutional quality gates for deployment approval."""

    WFE_THRESHOLD = "WFE_THRESHOLD"
    REGIME_ROBUSTNESS = "REGIME_ROBUSTNESS"
    PARAMETER_STABILITY = "PARAMETER_STABILITY"
    MINIMUM_TRADES = "MINIMUM_TRADES"
    MINIMUM_SHARPE = "MINIMUM_SHARPE"
    OVERFITTING_CHECK = "OVERFITTING_CHECK"
    MAXIMUM_DRAWDOWN = "MAXIMUM_DRAWDOWN"
    DATA_QUALITY = "DATA_QUALITY"


class QualityGateVerdict(StrEnum):
    """Four-state verdict for quality gate evaluation.

    PASS: Gate criteria met.
    FAIL: Gate criteria explicitly violated.
    INCONCLUSIVE: Criteria partially met or ambiguous — manual review recommended.
    INSUFFICIENT_DATA: Not enough data to evaluate — MUST NOT auto-advance.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ── Quality Gate Models ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class QualityGateResult:
    """Individual quality gate evaluation result."""

    gate_type: QualityGateType
    verdict: QualityGateVerdict
    actual_value: float | None
    threshold: float | None
    details: str
    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "gate_type": self.gate_type.value,
            "verdict": self.verdict.value,
            "actual_value": self.actual_value,
            "threshold": self.threshold,
            "details": self.details,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class QualityGateReport:
    """Aggregate quality gate evaluation report.

    A deployment advances only if all gates produce PASS.
    INCONCLUSIVE or INSUFFICIENT_DATA block automatic advancement.
    """

    gate_results: tuple[QualityGateResult, ...]
    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def all_passed(self) -> bool:
        """True only if every gate verdict is PASS."""
        return all(g.verdict == QualityGateVerdict.PASS for g in self.gate_results)

    @property
    def has_failures(self) -> bool:
        """True if any gate explicitly failed."""
        return any(g.verdict == QualityGateVerdict.FAIL for g in self.gate_results)

    @property
    def has_insufficient_data(self) -> bool:
        """True if any gate returned INSUFFICIENT_DATA."""
        return any(
            g.verdict == QualityGateVerdict.INSUFFICIENT_DATA
            for g in self.gate_results
        )

    @property
    def has_inconclusive(self) -> bool:
        """True if any gate returned INCONCLUSIVE."""
        return any(
            g.verdict == QualityGateVerdict.INCONCLUSIVE for g in self.gate_results
        )

    @property
    def summary_verdict(self) -> QualityGateVerdict:
        """Aggregate verdict: FAIL > INSUFFICIENT_DATA > INCONCLUSIVE > PASS."""
        if self.has_failures:
            return QualityGateVerdict.FAIL
        if self.has_insufficient_data:
            return QualityGateVerdict.INSUFFICIENT_DATA
        if self.has_inconclusive:
            return QualityGateVerdict.INCONCLUSIVE
        return QualityGateVerdict.PASS

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "gate_results": [g.to_dict() for g in self.gate_results],
            "all_passed": self.all_passed,
            "summary_verdict": self.summary_verdict.value,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


# ── Lifecycle Transition Audit Record ────────────────────────────────

@dataclass(frozen=True, slots=True)
class DeploymentTransitionRecord:
    """Immutable audit record for every deployment state transition.

    Every lifecycle transition MUST record: current state, target state,
    actor, timestamp, reason, authorization, and validation result.
    """

    from_status: DeploymentStatus
    to_status: DeploymentStatus
    actor_id: str
    actor_role: str | None
    timestamp: datetime
    reason: str
    authorization: str  # Permission used, e.g. "deployment:execute"
    validation_passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "authorization": self.authorization,
            "validation_passed": self.validation_passed,
            "details": self.details,
        }


# ── Incubation Configuration & Metrics ───────────────────────────────

@dataclass(frozen=True, slots=True)
class IncubationConfig:
    """Configurable paper-incubation policy parameters.

    Not hard-coded — all thresholds are configurable per deployment.
    """

    min_duration_days: int = 7
    min_trade_count: int = 10
    max_drawdown_pct: float = 25.0
    daily_loss_limit_pct: float = 5.0
    risk_violation_limit: int = 3
    performance_deviation_threshold_pct: float = 50.0
    initial_capital: Decimal = Decimal("10000.00")
    require_market_data_quality: bool = True
    evaluation_mode: str = "AUTOMATIC"  # AUTOMATIC or MANUAL

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "min_duration_days": self.min_duration_days,
            "min_trade_count": self.min_trade_count,
            "max_drawdown_pct": self.max_drawdown_pct,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "risk_violation_limit": self.risk_violation_limit,
            "performance_deviation_threshold_pct": self.performance_deviation_threshold_pct,
            "initial_capital": str(self.initial_capital),
            "require_market_data_quality": self.require_market_data_quality,
            "evaluation_mode": self.evaluation_mode,
        }


@dataclass(frozen=True, slots=True)
class IncubationMetrics:
    """Paper trading performance metrics captured during incubation."""

    net_pnl: Decimal = Decimal("0.00")
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    total_trades: int = 0
    profit_factor: float = 0.0
    daily_loss_violations: int = 0
    risk_violations: int = 0
    trading_days: int = 0
    data_quality_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "net_pnl": str(self.net_pnl),
            "total_return_pct": self.total_return_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate_pct": self.win_rate_pct,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "daily_loss_violations": self.daily_loss_violations,
            "risk_violations": self.risk_violations,
            "trading_days": self.trading_days,
            "data_quality_score": self.data_quality_score,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """Side-by-side comparison of paper incubation vs backtest benchmark metrics."""

    backtest_return_pct: float = 0.0
    paper_return_pct: float = 0.0
    return_ratio: float = 0.0  # paper / backtest (WFE-style)
    backtest_sharpe: float = 0.0
    paper_sharpe: float = 0.0
    sharpe_diff: float = 0.0
    backtest_max_dd_pct: float = 0.0
    paper_max_dd_pct: float = 0.0
    drawdown_diff: float = 0.0
    backtest_win_rate_pct: float = 0.0
    paper_win_rate_pct: float = 0.0
    backtest_trades: int = 0
    paper_trades: int = 0
    deviation_acceptable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "backtest_return_pct": self.backtest_return_pct,
            "paper_return_pct": self.paper_return_pct,
            "return_ratio": self.return_ratio,
            "backtest_sharpe": self.backtest_sharpe,
            "paper_sharpe": self.paper_sharpe,
            "sharpe_diff": self.sharpe_diff,
            "backtest_max_dd_pct": self.backtest_max_dd_pct,
            "paper_max_dd_pct": self.paper_max_dd_pct,
            "drawdown_diff": self.drawdown_diff,
            "backtest_win_rate_pct": self.backtest_win_rate_pct,
            "paper_win_rate_pct": self.paper_win_rate_pct,
            "backtest_trades": self.backtest_trades,
            "paper_trades": self.paper_trades,
            "deviation_acceptable": self.deviation_acceptable,
        }


# ── Evidence Chain ───────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class EvidenceChain:
    """Full provenance evidence chain for deployment traceability.

    Strategy → Research Experiment → Optimization Job → Walk-Forward Job →
    Stability Analysis → Strategy Version → Deployment → Paper Incubator

    No orphan deployments allowed — at least strategy_id and strategy_version
    must be present.
    """

    strategy_id: str
    strategy_version: str
    source_experiment_id: str | None = None
    source_optimization_id: str | None = None
    walk_forward_job_id: str | None = None
    stability_analysis_available: bool = False
    regime_analysis_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dictionary."""
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "source_experiment_id": self.source_experiment_id,
            "source_optimization_id": self.source_optimization_id,
            "walk_forward_job_id": self.walk_forward_job_id,
            "stability_analysis_available": self.stability_analysis_available,
            "regime_analysis_available": self.regime_analysis_available,
        }


# ── Aggregate Root ───────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class StrategyDeployment:
    """Aggregate root representing a strategy deployment through the
    institutional pipeline.

    Immutable snapshot — mutations create new instances via dataclass replace.
    """

    id: str
    organization_id: str
    created_by: str
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    parameters: dict[str, Any]
    evidence_chain: EvidenceChain
    status: DeploymentStatus = DeploymentStatus.PENDING_GATES
    initial_capital: Decimal = Decimal("10000.00")
    quality_gate_report: QualityGateReport | None = None
    incubation_config: IncubationConfig = field(default_factory=IncubationConfig)
    incubation_metrics: IncubationMetrics | None = None
    benchmark_comparison: BenchmarkComparison | None = None
    backtest_benchmark: dict[str, Any] = field(default_factory=dict)
    promotion_verdict: PromotionVerdict = PromotionVerdict.PENDING
    transition_history: tuple[DeploymentTransitionRecord, ...] = ()
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
