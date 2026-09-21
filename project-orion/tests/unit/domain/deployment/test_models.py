"""Unit tests for Deployment domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.deployment.models import (
    DeploymentStatus,
    DeploymentTransitionRecord,
    EvidenceChain,
    PromotionVerdict,
    QualityGateReport,
    QualityGateResult,
    QualityGateType,
    QualityGateVerdict,
    StrategyDeployment,
)


def test_deployment_status_enum():
    """Verify all 10 deployment status lifecycle states."""
    expected = {
        "PENDING_GATES",
        "GATES_PASSED",
        "GATES_FAILED",
        "INCUBATING",
        "PAUSED",
        "PAPER_VALIDATED",
        "INCUBATION_FAILED",
        "CANCELLED",
        "SUSPENDED",
        "PROMOTION_CANDIDATE",
    }
    actual = {s.value for s in DeploymentStatus}
    assert actual == expected


def test_quality_gate_verdict_enum():
    """Verify 4 explicit quality gate verdicts."""
    expected = {"PASS", "FAIL", "INCONCLUSIVE", "INSUFFICIENT_DATA"}
    actual = {v.value for v in QualityGateVerdict}
    assert actual == expected


def test_quality_gate_result_to_dict():
    """Verify QualityGateResult serialization."""
    res = QualityGateResult(
        gate_type=QualityGateType.WFE_THRESHOLD,
        verdict=QualityGateVerdict.PASS,
        actual_value=68.5,
        threshold=50.0,
        details="Strong WFE",
    )
    d = res.to_dict()
    assert d["gate_type"] == "WFE_THRESHOLD"
    assert d["verdict"] == "PASS"
    assert d["actual_value"] == 68.5
    assert d["threshold"] == 50.0
    assert d["details"] == "Strong WFE"


def test_quality_gate_report_verdicts():
    """Verify QualityGateReport aggregate properties and verdict priority."""
    # 1. All passed
    r_pass = QualityGateReport(
        gate_results=(
            QualityGateResult(QualityGateType.WFE_THRESHOLD, QualityGateVerdict.PASS, 60.0, 50.0, "ok"),
            QualityGateResult(QualityGateType.MINIMUM_TRADES, QualityGateVerdict.PASS, 25.0, 15.0, "ok"),
        )
    )
    assert r_pass.all_passed is True
    assert r_pass.has_failures is False
    assert r_pass.summary_verdict == QualityGateVerdict.PASS

    # 2. Insufficient data blocks advancement
    r_insufficient = QualityGateReport(
        gate_results=(
            QualityGateResult(QualityGateType.WFE_THRESHOLD, QualityGateVerdict.PASS, 60.0, 50.0, "ok"),
            QualityGateResult(QualityGateType.PARAMETER_STABILITY, QualityGateVerdict.INSUFFICIENT_DATA, None, 0.4, "no data"),
        )
    )
    assert r_insufficient.all_passed is False
    assert r_insufficient.has_insufficient_data is True
    assert r_insufficient.summary_verdict == QualityGateVerdict.INSUFFICIENT_DATA

    # 3. Inconclusive
    r_inconclusive = QualityGateReport(
        gate_results=(
            QualityGateResult(QualityGateType.WFE_THRESHOLD, QualityGateVerdict.PASS, 60.0, 50.0, "ok"),
            QualityGateResult(QualityGateType.MINIMUM_SHARPE, QualityGateVerdict.INCONCLUSIVE, 0.55, 0.5, "borderline"),
        )
    )
    assert r_inconclusive.all_passed is False
    assert r_inconclusive.has_inconclusive is True
    assert r_inconclusive.summary_verdict == QualityGateVerdict.INCONCLUSIVE

    # 4. Fail overrides insufficient data
    r_fail = QualityGateReport(
        gate_results=(
            QualityGateResult(QualityGateType.WFE_THRESHOLD, QualityGateVerdict.FAIL, 30.0, 50.0, "low"),
            QualityGateResult(QualityGateType.PARAMETER_STABILITY, QualityGateVerdict.INSUFFICIENT_DATA, None, 0.4, "no data"),
        )
    )
    assert r_fail.has_failures is True
    assert r_fail.summary_verdict == QualityGateVerdict.FAIL


def test_transition_record_immutability():
    """Verify DeploymentTransitionRecord cannot be mutated."""
    rec = DeploymentTransitionRecord(
        from_status=DeploymentStatus.PENDING_GATES,
        to_status=DeploymentStatus.GATES_PASSED,
        actor_id="user-123",
        actor_role="PORTFOLIO_MANAGER",
        timestamp=datetime.now(timezone.utc),
        reason="Gates passed",
        authorization="DEPLOYMENT_EXECUTE",
        validation_passed=True,
    )
    with pytest.raises(AttributeError):
        rec.reason = "modified"  # type: ignore


def test_evidence_chain():
    """Verify evidence chain serialization and required fields."""
    ev = EvidenceChain(
        strategy_id="trend_following",
        strategy_version="1.0.0",
        source_optimization_id="opt-abc",
        walk_forward_job_id="wfa-xyz",
        stability_analysis_available=True,
        regime_analysis_available=True,
    )
    d = ev.to_dict()
    assert d["strategy_id"] == "trend_following"
    assert d["source_optimization_id"] == "opt-abc"
    assert d["stability_analysis_available"] is True


def test_strategy_deployment_aggregate():
    """Verify StrategyDeployment construction."""
    ev = EvidenceChain(strategy_id="trend_following", strategy_version="1.0.0")
    dep = StrategyDeployment(
        id="dep-001",
        organization_id="org-1",
        created_by="user-1",
        strategy_id="trend_following",
        strategy_version="1.0.0",
        symbol="EUR/USD",
        timeframe="H1",
        parameters={"fast_period": 10, "slow_period": 30},
        evidence_chain=ev,
    )
    assert dep.status == DeploymentStatus.PENDING_GATES
    assert dep.initial_capital == Decimal("10000.00")
    assert dep.promotion_verdict == PromotionVerdict.PENDING
