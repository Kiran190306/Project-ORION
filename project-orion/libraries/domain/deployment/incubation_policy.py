"""Institutional Paper Incubation Policy and Validation Engine.

Provides configurable institutional policies for paper trading incubation:
- Minimum duration (days)
- Minimum trade count
- Maximum tolerated drawdown (%)
- Daily loss limits
- Maximum allowed risk violations
- Performance deviation tolerance vs. backtest benchmark
- Market data quality hurdles

Enforces non-negotiable quantitative safety:
Deployments that fail risk violation limits, experience severe drawdown,
or show severe performance degradation fail incubation.
Deployments with insufficient trades or duration cannot advance.

EPIC-025 strictly operates in Paper Trading ($0.00 Capital at risk).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.deployment.models import (
    BenchmarkComparison,
    IncubationConfig,
    IncubationMetrics,
)


@dataclass(frozen=True, slots=True)
class IncubationPolicyViolation:
    """Record of an explicit incubation policy violation or warning."""

    rule_name: str
    actual_value: Any
    threshold: Any
    severity: str  # "CRITICAL", "WARNING", "INFO"
    message: str


@dataclass(frozen=True, slots=True)
class IncubationPolicy:
    """Configurable, versioned institutional policy for paper incubator validation."""

    policy_id: str = "paper_incubator_standard_v1"
    version: str = "1.0.0"
    default_min_duration_days: int = 7
    default_min_trade_count: int = 10
    default_max_drawdown_pct: float = 20.0
    default_daily_loss_limit_pct: float = 5.0
    max_tolerated_risk_violations: int = 0
    max_tolerated_daily_loss_violations: int = 0
    max_performance_deviation_pct: float = 50.0  # Max acceptable degradation vs benchmark
    min_market_data_quality_score: float = 0.95  # 95% quote integrity hurdle
    require_positive_net_pnl: bool = True
    description: str = (
        "Standard institutional paper incubation policy for strategy validation."
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize policy to JSON-safe dictionary."""
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "default_min_duration_days": self.default_min_duration_days,
            "default_min_trade_count": self.default_min_trade_count,
            "default_max_drawdown_pct": self.default_max_drawdown_pct,
            "default_daily_loss_limit_pct": self.default_daily_loss_limit_pct,
            "max_tolerated_risk_violations": self.max_tolerated_risk_violations,
            "max_tolerated_daily_loss_violations": self.max_tolerated_daily_loss_violations,
            "max_performance_deviation_pct": self.max_performance_deviation_pct,
            "min_market_data_quality_score": self.min_market_data_quality_score,
            "require_positive_net_pnl": self.require_positive_net_pnl,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class IncubationEvaluationResult:
    """Comprehensive evaluation outcome of paper incubation against policy."""

    can_validate: bool  # True if duration and minimum trade sample are satisfied
    is_passed: bool  # True if all validation criteria pass and no critical violations
    is_failed: bool  # True if hard risk limit/drawdown thresholds were breached
    violations: tuple[IncubationPolicyViolation, ...]
    benchmark_comparison: BenchmarkComparison
    summary: str
    evaluated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize evaluation result to JSON-safe dictionary."""
        return {
            "can_validate": self.can_validate,
            "is_passed": self.is_passed,
            "is_failed": self.is_failed,
            "violations": [
                {
                    "rule_name": v.rule_name,
                    "actual_value": v.actual_value,
                    "threshold": v.threshold,
                    "severity": v.severity,
                    "message": v.message,
                }
                for v in self.violations
            ],
            "benchmark_comparison": self.benchmark_comparison.to_dict(),
            "summary": self.summary,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class IncubationPolicyEvaluator:
    """Evaluates paper trading incubation metrics against policy and benchmark."""

    def __init__(self, policy: IncubationPolicy | None = None) -> None:
        self.policy = policy or IncubationPolicy()

    def evaluate(
        self,
        *,
        metrics: IncubationMetrics,
        config: IncubationConfig,
        benchmark: dict[str, Any],
        elapsed_days: int,
    ) -> IncubationEvaluationResult:
        """Evaluate paper incubation results against policy rules and backtest benchmark."""
        violations: list[IncubationPolicyViolation] = []

        min_days = config.min_duration_days or self.policy.default_min_duration_days
        min_trades = config.min_trade_count or self.policy.default_min_trade_count
        max_dd = config.max_drawdown_pct or self.policy.default_max_drawdown_pct
        max_risk_viols = config.risk_violation_limit
        max_deviation = config.performance_deviation_threshold_pct

        # 1. Sample Sufficiency Checks
        has_sufficient_duration = elapsed_days >= min_days
        has_sufficient_trades = metrics.total_trades >= min_trades

        if not has_sufficient_duration:
            violations.append(
                IncubationPolicyViolation(
                    rule_name="MINIMUM_DURATION",
                    actual_value=elapsed_days,
                    threshold=min_days,
                    severity="WARNING",
                    message=f"Elapsed incubation days ({elapsed_days}) < required minimum ({min_days})",
                )
            )

        if not has_sufficient_trades:
            violations.append(
                IncubationPolicyViolation(
                    rule_name="MINIMUM_TRADES",
                    actual_value=metrics.total_trades,
                    threshold=min_trades,
                    severity="WARNING",
                    message=f"Paper trade count ({metrics.total_trades}) < required minimum ({min_trades})",
                )
            )

        can_validate = has_sufficient_duration and has_sufficient_trades

        # 2. Risk & Drawdown Checks (Hard failure rules)
        is_hard_failed = False

        if metrics.max_drawdown_pct > max_dd:
            is_hard_failed = True
            violations.append(
                IncubationPolicyViolation(
                    rule_name="MAXIMUM_DRAWDOWN",
                    actual_value=metrics.max_drawdown_pct,
                    threshold=max_dd,
                    severity="CRITICAL",
                    message=f"Paper max drawdown {metrics.max_drawdown_pct:.1f}% breached limit {max_dd:.1f}%",
                )
            )

        if metrics.risk_violations > max_risk_viols:
            is_hard_failed = True
            violations.append(
                IncubationPolicyViolation(
                    rule_name="RISK_VIOLATIONS",
                    actual_value=metrics.risk_violations,
                    threshold=max_risk_viols,
                    severity="CRITICAL",
                    message=f"Paper risk violations ({metrics.risk_violations}) exceeded tolerance ({max_risk_viols})",
                )
            )

        if metrics.daily_loss_violations > self.policy.max_tolerated_daily_loss_violations:
            is_hard_failed = True
            violations.append(
                IncubationPolicyViolation(
                    rule_name="DAILY_LOSS_LIMIT",
                    actual_value=metrics.daily_loss_violations,
                    threshold=self.policy.max_tolerated_daily_loss_violations,
                    severity="CRITICAL",
                    message=f"Daily loss limit violated {metrics.daily_loss_violations} time(s)",
                )
            )

        # 3. Data Quality Check
        if config.require_market_data_quality and metrics.data_quality_score < self.policy.min_market_data_quality_score:
            violations.append(
                IncubationPolicyViolation(
                    rule_name="DATA_QUALITY",
                    actual_value=metrics.data_quality_score,
                    threshold=self.policy.min_market_data_quality_score,
                    severity="CRITICAL",
                    message=f"Market data quality score {metrics.data_quality_score:.2f} below hurdle {self.policy.min_market_data_quality_score:.2f}",
                )
            )
            is_hard_failed = True

        # 4. PnL Check
        if self.policy.require_positive_net_pnl and metrics.net_pnl <= Decimal("0.00"):
            violations.append(
                IncubationPolicyViolation(
                    rule_name="POSITIVE_NET_PNL",
                    actual_value=str(metrics.net_pnl),
                    threshold="0.00",
                    severity="WARNING",
                    message=f"Paper incubation net PnL is non-positive ({metrics.net_pnl})",
                )
            )

        # 5. Benchmark Comparison Computation
        bt_return = float(benchmark.get("total_return_pct", 0.0))
        bt_sharpe = float(benchmark.get("sharpe_ratio", 0.0))
        bt_max_dd = float(benchmark.get("max_drawdown_pct", 0.0))
        bt_win_rate = float(benchmark.get("win_rate_pct", 0.0))
        bt_trades = int(benchmark.get("total_trades", 0))

        paper_ret = metrics.total_return_pct
        paper_sharpe = metrics.sharpe_ratio
        paper_max_dd = metrics.max_drawdown_pct
        paper_win_rate = metrics.win_rate_pct
        paper_trades = metrics.total_trades

        ret_ratio = (paper_ret / bt_return) if bt_return > 0 else 0.0
        sharpe_diff = paper_sharpe - bt_sharpe
        dd_diff = paper_max_dd - bt_max_dd

        # Performance degradation check:
        # e.g., if paper Sharpe dropped by more than max_deviation % of backtest Sharpe
        acceptable_deviation = True
        if bt_sharpe > 0.5:
            sharpe_drop_pct = max(0.0, (bt_sharpe - paper_sharpe) / bt_sharpe * 100.0)
            if sharpe_drop_pct > max_deviation:
                acceptable_deviation = False
                violations.append(
                    IncubationPolicyViolation(
                        rule_name="PERFORMANCE_DEVIATION",
                        actual_value=round(sharpe_drop_pct, 1),
                        threshold=max_deviation,
                        severity="WARNING",
                        message=f"Sharpe degradation ({sharpe_drop_pct:.1f}%) exceeds acceptable threshold ({max_deviation:.1f}%)",
                    )
                )

        benchmark_comparison = BenchmarkComparison(
            backtest_return_pct=round(bt_return, 2),
            paper_return_pct=round(paper_ret, 2),
            return_ratio=round(ret_ratio, 2),
            backtest_sharpe=round(bt_sharpe, 2),
            paper_sharpe=round(paper_sharpe, 2),
            sharpe_diff=round(sharpe_diff, 2),
            backtest_max_dd_pct=round(bt_max_dd, 2),
            paper_max_dd_pct=round(paper_max_dd, 2),
            drawdown_diff=round(dd_diff, 2),
            backtest_win_rate_pct=round(bt_win_rate, 2),
            paper_win_rate_pct=round(paper_win_rate, 2),
            backtest_trades=bt_trades,
            paper_trades=paper_trades,
            deviation_acceptable=acceptable_deviation,
        )

        critical_violations = [v for v in violations if v.severity == "CRITICAL"]
        is_passed = can_validate and len(critical_violations) == 0 and acceptable_deviation and (metrics.net_pnl > Decimal("0.00") if self.policy.require_positive_net_pnl else True)

        if is_hard_failed:
            summary = f"Incubation FAILED: {len(critical_violations)} critical policy breach(es)."
        elif not can_validate:
            summary = f"Incubation INSUFFICIENT DATA: Requires {min_days} days and {min_trades} trades to validate."
        elif is_passed:
            summary = "Incubation PASSED: Met all duration, risk, and benchmark fidelity criteria."
        else:
            summary = f"Incubation INCONCLUSIVE: {len(violations)} warnings/deviations detected."

        return IncubationEvaluationResult(
            can_validate=can_validate,
            is_passed=is_passed,
            is_failed=is_hard_failed,
            violations=tuple(violations),
            benchmark_comparison=benchmark_comparison,
            summary=summary,
        )
