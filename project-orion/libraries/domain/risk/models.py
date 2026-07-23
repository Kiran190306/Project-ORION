"""Immutable data models for the Risk Management Engine.

Defines:
- RiskDecision (APPROVED / REJECTED / DEFERRED)
- RiskResult per engine evaluation
- PolicyResult per policy evaluation
- PolicyEvaluation detailed breakdown
- RiskMetrics, PositionRisk, PortfolioRisk, DrawdownMetrics
- AccountProtectionStatus, EmergencyModeStatus
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import IntEnum, StrEnum
from typing import Any

# ─── Enums ────────────────────────────────────────────────────────────────


class RiskDecision(StrEnum):
    """Final decision produced by the RiskEngine.

    APPROVED  → trade may proceed
    REJECTED  → trade is blocked
    DEFERRED  → trade requires manual review / delayed execution
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class PolicySeverity(IntEnum):
    """Severity level of a risk policy violation.

    Higher value = more severe. Used for policy chaining ordering.
    """

    LOW = 10
    MEDIUM = 20
    HIGH = 30
    CRITICAL = 40


class PolicyCategory(StrEnum):
    """Logical grouping of risk policies."""

    POSITION_SIZING = "position_sizing"
    LOSS_LIMITS = "loss_limits"
    EXPOSURE = "exposure"
    LEVERAGE = "leverage"
    MARKET_CONDITIONS = "market_conditions"
    TRADING_HOURS = "trading_hours"
    ACCOUNT_PROTECTION = "account_protection"
    EMERGENCY = "emergency"
    SYSTEM_HEALTH = "system_health"
    COMPLIANCE = "compliance"


class EmergencyTrigger(StrEnum):
    """Triggers that activate emergency mode."""

    BROKER_DISCONNECT = "broker_disconnect"
    MARKET_FEED_FAILURE = "market_feed_failure"
    EXTREME_SPREAD = "extreme_spread"
    EXTREME_SLIPPAGE = "extreme_slippage"
    MARGIN_CALL_RISK = "margin_call_risk"
    CONNECTION_TIMEOUT = "connection_timeout"
    MANUAL_OVERRIDE = "manual_override"


class AccountProtectionLevel(StrEnum):
    """Levels of account protection."""

    NONE = "none"
    SOFT_STOP = "soft_stop"
    HARD_STOP = "hard_stop"
    TRADING_LOCK = "trading_lock"
    RECOVERY_MODE = "recovery_mode"


class PositionSizingMethod(StrEnum):
    """Position sizing methods supported."""

    FIXED_LOTS = "fixed_lots"
    RISK_PERCENT = "risk_percent"
    ATR = "atr"
    KELLY = "kelly"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    ACCOUNT_EQUITY_PERCENT = "account_equity_percent"


class RiskProfileType(StrEnum):
    """Built-in risk profile types."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


# ─── Core Result Models ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """Detailed breakdown of a single policy evaluation."""

    policy_name: str
    policy_category: PolicyCategory
    severity: PolicySeverity
    passed: bool
    score: float  # 0–100 (100 = perfectly safe)
    risk_contribution: float  # contribution to overall risk score
    message: str
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PolicyResult:
    """Result of a single risk policy evaluation."""

    policy_name: str
    policy_category: PolicyCategory
    severity: PolicySeverity
    passed: bool
    score: float  # 0–100
    message: str  # Human-readable result
    details: str = ""  # Detailed explanation for rejection
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        return self.passed

    @property
    def is_rejected(self) -> bool:
        return not self.passed

    def to_evaluation(self, weight: float = 1.0) -> PolicyEvaluation:
        """Convert to a PolicyEvaluation for aggregation."""
        return PolicyEvaluation(
            policy_name=self.policy_name,
            policy_category=self.policy_category,
            severity=self.severity,
            passed=self.passed,
            score=self.score,
            risk_contribution=(100.0 - self.score) * weight,
            message=self.message,
            details=self.details,
            timestamp=self.timestamp,
            metadata=self.metadata,
        )


@dataclass(frozen=True, slots=True)
class RiskResult:
    """Aggregated result from the RiskEngine.

    Contains the final decision, overall risk score, individual policy
    results, and any rejection reasons.
    """

    decision: RiskDecision
    risk_score: float  # 0 (no risk) – 100 (max risk)
    policy_results: tuple[PolicyResult, ...] = ()
    evaluations: tuple[PolicyEvaluation, ...] = ()
    rejection_reasons: tuple[str, ...] = ()
    deferred_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    is_emergency_mode: bool = False
    emergency_triggers: tuple[EmergencyTrigger, ...] = ()
    account_protection_level: AccountProtectionLevel = AccountProtectionLevel.NONE
    risk_profile: str = ""
    evaluated_policies_count: int = 0
    enabled_policies_count: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        return self.decision == RiskDecision.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.decision == RiskDecision.REJECTED

    @property
    def is_deferred(self) -> bool:
        return self.decision == RiskDecision.DEFERRED

    @property
    def approved_count(self) -> int:
        return sum(1 for p in self.policy_results if p.passed)

    @property
    def rejected_count(self) -> int:
        return sum(1 for p in self.policy_results if not p.passed)

    @property
    def summary(self) -> str:
        """Return a human-readable summary."""
        parts = [
            f"RiskDecision: {self.decision.value.upper()}",
            f"Risk Score: {self.risk_score:.1f}/100",
        ]
        if self.rejection_reasons:
            parts.append(
                f"Rejections ({len(self.rejection_reasons)}): {'; '.join(self.rejection_reasons)}"
            )
        if self.deferred_reasons:
            parts.append(
                f"Deferred ({len(self.deferred_reasons)}): {'; '.join(self.deferred_reasons)}"
            )
        return " | ".join(parts)


# ─── Risk Metrics Models ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PositionRisk:
    """Risk metrics for a single position."""

    symbol: str
    size: Decimal
    notional_value: Decimal
    risk_amount: Decimal
    risk_pct: float  # % of account at risk
    direction: str = ""  # long / short
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    atr: Decimal | None = None
    volatility: float = 0.0
    beta: float = 1.0
    correlation_to_portfolio: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    """Aggregated portfolio-level risk metrics."""

    portfolio_heat: float = 0.0  # 0–100
    net_exposure: Decimal = Decimal("0")
    long_exposure: Decimal = Decimal("0")
    short_exposure: Decimal = Decimal("0")
    gross_exposure: Decimal = Decimal("0")
    currency_exposure: dict[str, Decimal] = field(default_factory=dict)
    correlation_exposure: dict[str, float] = field(default_factory=dict)
    sector_exposure: dict[str, Decimal] = field(default_factory=dict)
    concentration_risk: float = 0.0  # 0–100
    position_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DrawdownMetrics:
    """Drawdown tracking metrics."""

    current_drawdown: float = 0.0  # % from peak
    max_drawdown: float = 0.0  # historical max
    intraday_drawdown: float = 0.0
    weekly_drawdown: float = 0.0
    monthly_drawdown: float = 0.0
    peak_balance: Decimal | None = None
    current_balance: Decimal | None = None
    recovery_factor: float = 0.0  # net profit / max drawdown
    drawdown_duration_days: int = 0
    is_recovery_mode: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class AccountProtectionStatus:
    """Current account protection status."""

    level: AccountProtectionLevel = AccountProtectionLevel.NONE
    soft_stop_triggered: bool = False
    hard_stop_triggered: bool = False
    trading_locked: bool = False
    cooldown_active: bool = False
    cooldown_until: datetime | None = None
    cooldown_remaining_seconds: float = 0.0
    recovery_mode_active: bool = False
    daily_loss_limit_reached: bool = False
    weekly_loss_limit_reached: bool = False
    monthly_loss_limit_reached: bool = False
    consecutive_losses_limit_reached: bool = False
    warnings: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_locked(self) -> bool:
        return self.trading_locked or self.hard_stop_triggered

    @property
    def can_trade(self) -> bool:
        if self.trading_locked or self.hard_stop_triggered:
            return False
        if (
            self.cooldown_active
            and self.cooldown_until
            and datetime.now(timezone.utc) < self.cooldown_until
        ):
            return False
        return True


@dataclass(frozen=True, slots=True)
class EmergencyModeStatus:
    """Current emergency mode status."""

    active: bool = False
    triggers: tuple[EmergencyTrigger, ...] = ()
    activated_at: datetime | None = None
    auto_resolve: bool = True
    auto_resolve_after_seconds: float = 300.0  # 5 min default
    execution_engine_notified: bool = False
    broker_disconnected: bool = False
    market_feed_failed: bool = False
    extreme_spread_detected: bool = False
    extreme_slippage_detected: bool = False
    margin_call_risk: bool = False
    connection_timeout: bool = False
    manual_override: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if not self.active:
            return "Emergency mode: INACTIVE"
        triggers = ", ".join(t.value for t in self.triggers)
        return f"Emergency mode: ACTIVE (triggers: {triggers})"


# ─── Risk Score Model ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RiskScore:
    """Comprehensive risk score breakdown."""

    overall: float = 0.0  # 0–100 (0 = no risk, 100 = max risk)
    position_size_score: float = 100.0
    loss_limit_score: float = 100.0
    exposure_score: float = 100.0
    leverage_score: float = 100.0
    market_condition_score: float = 100.0
    account_protection_score: float = 100.0
    system_health_score: float = 100.0
    compliance_score: float = 100.0
    weighted_score: float = 0.0
    policy_count: int = 0
    failed_policies: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_safe(self) -> bool:
        return self.overall < 30.0

    @property
    def is_caution(self) -> bool:
        return 30.0 <= self.overall < 60.0

    @property
    def is_dangerous(self) -> bool:
        return self.overall >= 60.0
