"""Risk Evaluator - weighted scoring and aggregation of policy results.

Aggregates individual policy evaluations into a composite risk score
using configurable weights per policy category. Produces the final
RiskDecision based on configurable thresholds.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from libraries.domain.risk.models import (
    PolicyCategory,
    PolicyEvaluation,
    PolicySeverity,
    RiskDecision,
    RiskResult,
    RiskScore,
)


# Default category weights (sum should be ~100)
DEFAULT_CATEGORY_WEIGHTS: dict[PolicyCategory, float] = {
    PolicyCategory.POSITION_SIZING: 10.0,
    PolicyCategory.LOSS_LIMITS: 15.0,
    PolicyCategory.EXPOSURE: 10.0,
    PolicyCategory.LEVERAGE: 10.0,
    PolicyCategory.MARKET_CONDITIONS: 10.0,
    PolicyCategory.TRADING_HOURS: 5.0,
    PolicyCategory.ACCOUNT_PROTECTION: 15.0,
    PolicyCategory.EMERGENCY: 15.0,
    PolicyCategory.SYSTEM_HEALTH: 5.0,
    PolicyCategory.COMPLIANCE: 5.0,
}


@dataclass(frozen=True, slots=True)
class RiskEvaluatorConfig:
    """Configuration for the RiskEvaluator."""

    approve_threshold: float = 30.0  # risk score <= this = APPROVED
    reject_threshold: float = 60.0  # risk score >= this = REJECTED
    deferred_threshold: float = 45.0  # risk score >= this and < reject = DEFERRED
    category_weights: dict[PolicyCategory, float] = field(
        default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS)
    )
    severity_multipliers: dict[PolicySeverity, float] = field(
        default_factory=lambda: {
            PolicySeverity.LOW: 1.0,
            PolicySeverity.MEDIUM: 1.5,
            PolicySeverity.HIGH: 2.0,
            PolicySeverity.CRITICAL: 3.0,
        }
    )
    enable_severity_weighting: bool = True

    def __post_init__(self) -> None:
        # Ensure all categories have weights
        for cat in PolicyCategory:
            if cat not in self.category_weights:
                object.__setattr__(self, "category_weights", {
                    **self.category_weights,
                    cat: 5.0,
                })


class RiskEvaluator:
    """Evaluates and aggregates policy results into a risk decision.

    Thread-safe via asyncio.Lock. Uses weighted category scoring with
    optional severity multipliers for policy chaining.
    """

    def __init__(
        self,
        config: RiskEvaluatorConfig | None = None,
    ) -> None:
        self._config = config or RiskEvaluatorConfig()
        self._lock = asyncio.Lock()

    @property
    def config(self) -> RiskEvaluatorConfig:
        return self._config

    async def evaluate(
        self,
        evaluations: list[PolicyEvaluation],
        is_emergency_mode: bool = False,
    ) -> RiskResult:
        """Aggregate policy evaluations into a final RiskResult.

        Args:
            evaluations: List of PolicyEvaluation from all enabled policies.
            is_emergency_mode: Whether emergency mode is active.

        Returns:
            RiskResult with aggregated decision.
        """
        async with self._lock:
            return self._aggregate(evaluations, is_emergency_mode)

    async def compute_risk_score(
        self,
        evaluations: list[PolicyEvaluation],
    ) -> RiskScore:
        """Compute a detailed risk score breakdown.

        Args:
            evaluations: List of PolicyEvaluation.

        Returns:
            RiskScore with category breakdowns.
        """
        async with self._lock:
            return self._compute_risk_score(evaluations)

    async def get_category_score(
        self,
        evaluations: list[PolicyEvaluation],
        category: PolicyCategory,
    ) -> float:
        """Compute the average score for a specific category.

        Args:
            evaluations: List of PolicyEvaluation.
            category: Category to score.

        Returns:
            Average score 0–100 for that category.
        """
        async with self._lock:
            cat_evals = [e for e in evaluations if e.policy_category == category]
            if not cat_evals:
                return 100.0
            return sum(e.score for e in cat_evals) / len(cat_evals)

    def _aggregate(
        self,
        evaluations: list[PolicyEvaluation],
        is_emergency_mode: bool,
    ) -> RiskResult:
        """Internal aggregation logic."""
        risk_score = self._compute_weighted_risk(evaluations)

        # Determine decision
        decision = self._determine_decision(risk_score, is_emergency_mode, evaluations)

        # Collect rejection/deferred reasons
        rejection_reasons: list[str] = []
        deferred_reasons: list[str] = []
        warnings: list[str] = []

        for ev in evaluations:
            if not ev.passed:
                if ev.severity >= PolicySeverity.HIGH:
                    rejection_reasons.append(
                        f"[{ev.severity.name}] {ev.policy_name}: {ev.details or ev.message}"
                    )
                else:
                    deferred_reasons.append(
                        f"[{ev.severity.name}] {ev.policy_name}: {ev.details or ev.message}"
                    )

            if ev.score < 30.0 and ev.severity >= PolicySeverity.MEDIUM:
                warnings.append(
                    f"Low score ({ev.score:.1f}) in policy '{ev.policy_name}'"
                )

        # Build policy results from evaluations
        policy_results = tuple(
            PolicyResult(
                policy_name=e.policy_name,
                policy_category=e.policy_category,
                severity=e.severity,
                passed=e.passed,
                score=e.score,
                message=e.message,
                details=e.details,
            )
            for e in evaluations
        )

        return RiskResult(
            decision=decision,
            risk_score=round(risk_score, 2),
            policy_results=policy_results,
            evaluations=tuple(evaluations),
            rejection_reasons=tuple(rejection_reasons),
            deferred_reasons=tuple(deferred_reasons),
            warnings=tuple(warnings),
            is_emergency_mode=is_emergency_mode,
            evaluated_policies_count=len(evaluations),
            enabled_policies_count=len(evaluations),
        )

    def _compute_weighted_risk(
        self,
        evaluations: list[PolicyEvaluation],
    ) -> float:
        """Compute weighted risk score from evaluations."""
        if not evaluations:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for ev in evaluations:
            category_weight = self._config.category_weights.get(
                ev.policy_category, 5.0
            )
            severity_mult = (
                self._config.severity_multipliers.get(ev.severity, 1.0)
                if self._config.enable_severity_weighting
                else 1.0
            )

            # Risk contribution = (100 - score) * weight * severity_mult
            risk_contribution = (100.0 - ev.score) * category_weight * severity_mult
            effective_weight = category_weight * severity_mult

            weighted_sum += risk_contribution
            total_weight += effective_weight

        if total_weight == 0:
            return 0.0

        # Normalize to 0–100
        raw_score = weighted_sum / total_weight
        return max(0.0, min(100.0, raw_score))

    def _determine_decision(
        self,
        risk_score: float,
        is_emergency_mode: bool,
        evaluations: list[PolicyEvaluation],
    ) -> RiskDecision:
        """Determine the final risk decision based on score and policies."""
        # Emergency mode overrides to REJECTED
        if is_emergency_mode:
            return RiskDecision.REJECTED

        # Any CRITICAL severity failure = REJECTED
        critical_failures = [
            e for e in evaluations
            if not e.passed and e.severity == PolicySeverity.CRITICAL
        ]
        if critical_failures:
            return RiskDecision.REJECTED

        # Any HIGH severity failure = DEFERRED (or REJECTED if score high)
        high_failures = [
            e for e in evaluations
            if not e.passed and e.severity == PolicySeverity.HIGH
        ]
        if high_failures and risk_score >= self._config.reject_threshold:
            return RiskDecision.REJECTED

        # Score-based thresholds
        if risk_score >= self._config.reject_threshold:
            return RiskDecision.REJECTED

        if risk_score >= self._config.deferred_threshold:
            return RiskDecision.DEFERRED

        if risk_score <= self._config.approve_threshold:
            return RiskDecision.APPROVED

        # Medium severity failures with score in middle range = DEFERRED
        medium_failures = [
            e for e in evaluations
            if not e.passed and e.severity == PolicySeverity.MEDIUM
        ]
        if medium_failures:
            return RiskDecision.DEFERRED

        return RiskDecision.APPROVED

    def _compute_risk_score(self, evaluations: list[PolicyEvaluation]) -> RiskScore:
        """Compute detailed RiskScore breakdown."""
        position_evals = [e for e in evaluations if e.policy_category == PolicyCategory.POSITION_SIZING]
        loss_evals = [e for e in evaluations if e.policy_category == PolicyCategory.LOSS_LIMITS]
        exposure_evals = [e for e in evaluations if e.policy_category == PolicyCategory.EXPOSURE]
        leverage_evals = [e for e in evaluations if e.policy_category == PolicyCategory.LEVERAGE]
        market_evals = [e for e in evaluations if e.policy_category == PolicyCategory.MARKET_CONDITIONS]
        account_evals = [e for e in evaluations if e.policy_category == PolicyCategory.ACCOUNT_PROTECTION]
        health_evals = [e for e in evaluations if e.policy_category == PolicyCategory.SYSTEM_HEALTH]
        compliance_evals = [e for e in evaluations if e.policy_category == PolicyCategory.COMPLIANCE]

        def avg_score(evals: list[PolicyEvaluation]) -> float:
            if not evals:
                return 100.0
            return sum(e.score for e in evals) / len(evals)

        position_score = avg_score(position_evals)
        loss_score = avg_score(loss_evals)
        exposure_score = avg_score(exposure_evals)
        leverage_score = avg_score(leverage_evals)
        market_score = avg_score(market_evals)
        account_score = avg_score(account_evals)
        health_score = avg_score(health_evals)
        compliance_score = avg_score(compliance_evals)

        overall = self._compute_weighted_risk(evaluations)
        failed = sum(1 for e in evaluations if not e.passed)

        return RiskScore(
            overall=round(overall, 2),
            position_size_score=round(position_score, 2),
            loss_limit_score=round(loss_score, 2),
            exposure_score=round(exposure_score, 2),
            leverage_score=round(leverage_score, 2),
            market_condition_score=round(market_score, 2),
            account_protection_score=round(account_score, 2),
            system_health_score=round(health_score, 2),
            compliance_score=round(compliance_score, 2),
            weighted_score=round(overall, 2),
            policy_count=len(evaluations),
            failed_policies=failed,
        )

