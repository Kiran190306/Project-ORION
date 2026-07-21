"""Tests for risk data models."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.risk.models import (
    AccountProtectionLevel,
    AccountProtectionStatus,
    DrawdownMetrics,
    EmergencyModeStatus,
    EmergencyTrigger,
    PolicyCategory,
    PolicyEvaluation,
    PolicyResult,
    PolicySeverity,
    PortfolioRisk,
    PositionRisk,
    RiskDecision,
    RiskResult,
    RiskScore,
)


class TestRiskDecision:
    def test_approved_enum(self):
        assert RiskDecision.APPROVED.value == "approved"

    def test_rejected_enum(self):
        assert RiskDecision.REJECTED.value == "rejected"

    def test_deferred_enum(self):
        assert RiskDecision.DEFERRED.value == "deferred"

    def test_all_values_unique(self):
        values = [d.value for d in RiskDecision]
        assert len(values) == len(set(values))


class TestPolicySeverity:
    def test_ordering(self):
        assert PolicySeverity.LOW < PolicySeverity.MEDIUM
        assert PolicySeverity.MEDIUM < PolicySeverity.HIGH
        assert PolicySeverity.HIGH < PolicySeverity.CRITICAL

    def test_numeric_values(self):
        assert PolicySeverity.LOW.value == 10
        assert PolicySeverity.MEDIUM.value == 20
        assert PolicySeverity.HIGH.value == 30
        assert PolicySeverity.CRITICAL.value == 40


class TestPolicyCategory:
    def test_valid_categories(self):
        cats = [c.value for c in PolicyCategory]
        assert "position_sizing" in cats
        assert "loss_limits" in cats
        assert "exposure" in cats
        assert "emergency" in cats


class TestPolicyResult:
    def test_create_passed(self):
        result = PolicyResult(
            policy_name="test_policy",
            policy_category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.MEDIUM,
            passed=True,
            score=85.0,
            message="All good",
        )
        assert result.passed
        assert result.is_approved
        assert not result.is_rejected
        assert result.score == 85.0

    def test_create_failed(self):
        result = PolicyResult(
            policy_name="test_policy",
            policy_category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.HIGH,
            passed=False,
            score=20.0,
            message="Limit exceeded",
            details="Daily loss limit exceeded by 5%",
        )
        assert not result.passed
        assert not result.is_approved
        assert result.is_rejected
        assert result.details == "Daily loss limit exceeded by 5%"

    def test_to_evaluation(self):
        result = PolicyResult(
            policy_name="test",
            policy_category=PolicyCategory.LEVERAGE,
            severity=PolicySeverity.CRITICAL,
            passed=False,
            score=10.0,
            message="Failed",
            details="Leverage too high",
        )
        evaluation = result.to_evaluation(weight=2.0)
        assert evaluation.policy_name == "test"
        assert evaluation.policy_category == PolicyCategory.LEVERAGE
        assert evaluation.score == 10.0
        assert evaluation.risk_contribution == (100.0 - 10.0) * 2.0


class TestPolicyEvaluation:
    def test_create(self):
        ev = PolicyEvaluation(
            policy_name="drawdown",
            policy_category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.CRITICAL,
            passed=True,
            score=95.0,
            risk_contribution=5.0,
            message="Within limits",
        )
        assert ev.policy_name == "drawdown"
        assert ev.risk_contribution == 5.0


class TestRiskResult:
    def test_default_approved(self):
        result = RiskResult(
            decision=RiskDecision.APPROVED,
            risk_score=15.0,
        )
        assert result.is_approved
        assert not result.is_rejected
        assert not result.is_deferred
        assert result.risk_score == 15.0
        assert result.summary.startswith("RiskDecision: APPROVED")

    def test_rejected_with_reasons(self):
        result = RiskResult(
            decision=RiskDecision.REJECTED,
            risk_score=85.0,
            rejection_reasons=("Daily loss limit exceeded", "Leverage too high"),
        )
        assert result.is_rejected
        assert not result.is_approved
        assert len(result.rejection_reasons) == 2
        assert "Daily loss" in result.summary

    def test_deferred(self):
        result = RiskResult(
            decision=RiskDecision.DEFERRED,
            risk_score=50.0,
            deferred_reasons=("Spread too wide for automated execution",),
        )
        assert result.is_deferred
        assert len(result.deferred_reasons) == 1

    def test_count_properties(self):
        passed = PolicyResult(
            policy_name="p1", policy_category=PolicyCategory.LOSS_LIMITS,
            severity=PolicySeverity.LOW, passed=True, score=100.0, message="ok",
        )
        failed = PolicyResult(
            policy_name="p2", policy_category=PolicyCategory.EXPOSURE,
            severity=PolicySeverity.HIGH, passed=False, score=10.0, message="fail",
        )
        result = RiskResult(
            decision=RiskDecision.REJECTED,
            risk_score=90.0,
            policy_results=(passed, failed),
        )
        assert result.approved_count == 1
        assert result.rejected_count == 1

    def test_emergency_mode(self):
        result = RiskResult(
            decision=RiskDecision.REJECTED,
            risk_score=100.0,
            is_emergency_mode=True,
            emergency_triggers=(EmergencyTrigger.BROKER_DISCONNECT,),
        )
        assert result.is_emergency_mode
        assert len(result.emergency_triggers) == 1


class TestPositionRisk:
    def test_create(self):
        pr = PositionRisk(
            symbol="EURUSD",
            size=Decimal("10000"),
            notional_value=Decimal("110000"),
            risk_amount=Decimal("500"),
            risk_pct=5.0,
            direction="long",
        )
        assert pr.symbol == "EURUSD"
        assert pr.direction == "long"
        assert pr.risk_pct == 5.0


class TestPortfolioRisk:
    def test_create(self):
        pr = PortfolioRisk(
            portfolio_heat=45.0,
            net_exposure=Decimal("50000"),
            long_exposure=Decimal("80000"),
            short_exposure=Decimal("30000"),
            gross_exposure=Decimal("110000"),
        )
        assert pr.portfolio_heat == 45.0
        assert pr.gross_exposure == Decimal("110000")

    def test_currency_exposure(self):
        pr = PortfolioRisk(
            currency_exposure={"USD": Decimal("50000"), "EUR": Decimal("30000")},
        )
        assert pr.currency_exposure["USD"] == Decimal("50000")


class TestDrawdownMetrics:
    def test_create(self):
        dm = DrawdownMetrics(
            current_drawdown=15.0,
            max_drawdown=25.0,
            intraday_drawdown=5.0,
            weekly_drawdown=10.0,
            monthly_drawdown=15.0,
            peak_balance=Decimal("100000"),
            current_balance=Decimal("85000"),
            recovery_factor=0.5,
            drawdown_duration_days=10,
        )
        assert dm.current_drawdown == 15.0
        assert dm.recovery_factor == 0.5
        assert not dm.is_recovery_mode


class TestAccountProtectionStatus:
    def test_default_unlocked(self):
        status = AccountProtectionStatus()
        assert status.can_trade
        assert not status.is_locked
        assert status.level == AccountProtectionLevel.NONE

    def test_locked(self):
        status = AccountProtectionStatus(
            level=AccountProtectionLevel.TRADING_LOCK,
            trading_locked=True,
        )
        assert not status.can_trade
        assert status.is_locked

    def test_cooldown_active(self):
        from datetime import timedelta
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        status = AccountProtectionStatus(
            cooldown_active=True,
            cooldown_until=future,
            cooldown_remaining_seconds=3600.0,
        )
        assert not status.can_trade


class TestEmergencyModeStatus:
    def test_inactive(self):
        status = EmergencyModeStatus()
        assert not status.active
        assert "INACTIVE" in status.summary

    def test_active(self):
        status = EmergencyModeStatus(
            active=True,
            triggers=(EmergencyTrigger.BROKER_DISCONNECT, EmergencyTrigger.MARKET_FEED_FAILURE),
            activated_at=datetime.now(timezone.utc),
        )
        assert status.active
        assert "ACTIVE" in status.summary
        assert "broker_disconnect" in status.summary


class TestRiskScore:
    def test_default(self):
        score = RiskScore()
        assert score.overall == 0.0
        assert score.is_safe
        assert not score.is_caution
        assert not score.is_dangerous

    def test_caution_zone(self):
        score = RiskScore(overall=45.0)
        assert score.is_caution
        assert not score.is_safe
        assert not score.is_dangerous

    def test_danger_zone(self):
        score = RiskScore(overall=75.0)
        assert score.is_dangerous
        assert not score.is_safe
        assert not score.is_caution

    def test_safe_zone(self):
        score = RiskScore(overall=15.0)
        assert score.is_safe
        assert not score.is_caution
        assert not score.is_dangerous

