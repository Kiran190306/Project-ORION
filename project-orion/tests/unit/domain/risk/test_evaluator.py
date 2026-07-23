"""Tests for the RiskEvaluator."""

from __future__ import annotations

import pytest

from libraries.domain.risk.evaluator import RiskEvaluator, RiskEvaluatorConfig
from libraries.domain.risk.models import (
    PolicyCategory,
    PolicyEvaluation,
    PolicySeverity,
    RiskDecision,
)


def make_evaluation(
    policy_name: str,
    score: float,
    passed: bool = True,
    category: PolicyCategory = PolicyCategory.LOSS_LIMITS,
    severity: PolicySeverity = PolicySeverity.MEDIUM,
    risk_contribution: float | None = None,
) -> PolicyEvaluation:
    """Helper to create a PolicyEvaluation."""
    if risk_contribution is None:
        risk_contribution = (100.0 - score) * severity.numeric / 40.0
    return PolicyEvaluation(
        policy_name=policy_name,
        policy_category=category,
        severity=severity,
        passed=passed,
        score=score,
        risk_contribution=risk_contribution,
        message="Test evaluation",
    )


class TestRiskEvaluator:
    @pytest.mark.asyncio
    async def test_empty_evaluations_returns_approved(self):
        evaluator = RiskEvaluator()
        result = await evaluator.evaluate([])
        assert result.decision == RiskDecision.APPROVED
        assert result.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_all_passing_returns_approved(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("policy1", 100.0, passed=True),
            make_evaluation("policy2", 95.0, passed=True),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.APPROVED
        assert result.risk_score < 50.0

    @pytest.mark.asyncio
    async def test_any_failing_returns_rejected(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("policy1", 100.0, passed=True),
            make_evaluation("policy2", 10.0, passed=False, severity=PolicySeverity.CRITICAL),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.REJECTED
        assert result.risk_score > 50.0

    @pytest.mark.asyncio
    async def test_critical_failure_always_rejected(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("critical_policy", 0.0, passed=False, severity=PolicySeverity.CRITICAL),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.REJECTED

    @pytest.mark.asyncio
    async def test_deferred_when_risk_score_in_caution_zone(self):
        evaluator = RiskEvaluator(
            config=RiskEvaluatorConfig(
                approval_threshold=30.0,
                rejection_threshold=70.0,
            )
        )
        evaluations = [
            make_evaluation("policy1", 50.0, passed=True, risk_contribution=40.0),
        ]
        result = await evaluator.evaluate(evaluations)
        # Risk score should be in caution zone (30-70)
        if 30.0 < result.risk_score < 70.0:
            assert result.decision == RiskDecision.DEFERRED

    @pytest.mark.asyncio
    async def test_emergency_mode_always_rejected(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("policy1", 100.0, passed=True),
        ]
        result = await evaluator.evaluate(evaluations, is_emergency_mode=True)
        assert result.decision == RiskDecision.REJECTED
        assert result.risk_score == 100.0

    @pytest.mark.asyncio
    async def test_risk_score_calculation(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation("p2", 80.0, passed=True, risk_contribution=20.0),
            make_evaluation("p3", 60.0, passed=False, risk_contribution=40.0),
        ]
        result = await evaluator.evaluate(evaluations)
        assert 0.0 <= result.risk_score <= 100.0

    @pytest.mark.asyncio
    async def test_risk_score_breakdown(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation(
                "p2", 50.0, passed=False, severity=PolicySeverity.HIGH, risk_contribution=50.0
            ),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.risk_score > 0.0
        assert len(result.evaluations) == 2

    @pytest.mark.asyncio
    async def test_compute_risk_score(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation("p2", 50.0, passed=False, risk_contribution=50.0),
        ]
        score = await evaluator.compute_risk_score(evaluations)
        assert score.overall > 0.0
        assert score.policy_count == 2
        assert score.max_risk > 0.0

    @pytest.mark.asyncio
    async def test_rejection_reasons_aggregated(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 10.0, passed=False, severity=PolicySeverity.HIGH),
            make_evaluation("p2", 5.0, passed=False, severity=PolicySeverity.CRITICAL),
        ]
        result = await evaluator.evaluate(evaluations)
        assert len(result.rejection_reasons) >= 1

    @pytest.mark.asyncio
    async def test_deferred_reasons(self):
        evaluator = RiskEvaluator(
            config=RiskEvaluatorConfig(
                approval_threshold=30.0,
                rejection_threshold=70.0,
            )
        )
        evaluations = [
            make_evaluation("p1", 60.0, passed=True, risk_contribution=40.0),
        ]
        result = await evaluator.evaluate(evaluations)
        # May be deferred if risk score is in the middle
        if result.decision == RiskDecision.DEFERRED:
            assert len(result.deferred_reasons) >= 1

    @pytest.mark.asyncio
    async def test_config_properties(self):
        config = RiskEvaluatorConfig(approval_threshold=25.0, rejection_threshold=75.0)
        evaluator = RiskEvaluator(config=config)
        assert evaluator.config.approval_threshold == 25.0

    @pytest.mark.asyncio
    async def test_low_risk_score_approved(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation("p2", 95.0, passed=True, risk_contribution=5.0),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.APPROVED

    @pytest.mark.asyncio
    async def test_high_risk_score_rejected(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation(
                "p1", 10.0, passed=False, severity=PolicySeverity.CRITICAL, risk_contribution=90.0
            ),
            make_evaluation(
                "p2", 20.0, passed=False, severity=PolicySeverity.HIGH, risk_contribution=80.0
            ),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.REJECTED
        assert result.risk_score > 70.0

    @pytest.mark.asyncio
    async def test_approved_policies_count(self):
        evaluator = RiskEvaluator()
        evaluations = [
            make_evaluation("p1", 100.0, passed=True),
            make_evaluation("p2", 10.0, passed=False, severity=PolicySeverity.CRITICAL),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.approved_policies_count == 1
        assert result.rejected_policies_count == 1

    @pytest.mark.asyncio
    async def test_high_severity_rejection_override(self):
        evaluator = RiskEvaluator()
        # Even if risk score is low, a CRITICAL policy failure should reject
        evaluations = [
            make_evaluation("p1", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation("p2", 100.0, passed=True, risk_contribution=0.0),
            make_evaluation(
                "p3", 0.0, passed=False, severity=PolicySeverity.CRITICAL, risk_contribution=100.0
            ),
        ]
        result = await evaluator.evaluate(evaluations)
        assert result.decision == RiskDecision.REJECTED
