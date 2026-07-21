"""Tests for RiskStatistics."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.risk.models import PolicyCategory, RiskDecision
from libraries.domain.risk.statistics import RiskStatistics


class TestRiskStatistics:
    @pytest.mark.asyncio
    async def test_initial_state(self):
        stats = RiskStatistics()
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 0
        assert snapshot.total_approved == 0
        assert snapshot.total_rejected == 0
        assert snapshot.total_deferred == 0
        assert snapshot.approval_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_approval(self):
        stats = RiskStatistics()
        violations = {"policy1": True, "policy2": True}
        categories = {"policy1": PolicyCategory.LOSS_LIMITS, "policy2": PolicyCategory.EXPOSURE}

        await stats.record_evaluation(RiskDecision.APPROVED, 15.0, violations, categories)
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 1
        assert snapshot.total_approved == 1
        assert snapshot.total_rejected == 0
        assert snapshot.approval_rate == 1.0
        assert snapshot.average_risk_score == 15.0

    @pytest.mark.asyncio
    async def test_record_rejection(self):
        stats = RiskStatistics()
        violations = {"policy1": False, "policy2": True}
        categories = {"policy1": PolicyCategory.LOSS_LIMITS, "policy2": PolicyCategory.EXPOSURE}

        await stats.record_evaluation(RiskDecision.REJECTED, 85.0, violations, categories)
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 1
        assert snapshot.total_rejected == 1
        assert snapshot.total_approved == 0

    @pytest.mark.asyncio
    async def test_record_deferred(self):
        stats = RiskStatistics()
        violations = {"policy1": True}
        categories = {"policy1": PolicyCategory.EXPOSURE}

        await stats.record_evaluation(RiskDecision.DEFERRED, 50.0, violations, categories)
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 1
        assert snapshot.total_deferred == 1

    @pytest.mark.asyncio
    async def test_multiple_records(self):
        stats = RiskStatistics()
        for _ in range(10):
            await stats.record_evaluation(
                RiskDecision.APPROVED, 20.0,
                {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        for _ in range(5):
            await stats.record_evaluation(
                RiskDecision.REJECTED, 80.0,
                {"p1": False}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 15
        assert snapshot.total_approved == 10
        assert snapshot.total_rejected == 5
        assert snapshot.approval_rate == 10.0 / 15.0

    @pytest.mark.asyncio
    async def test_policy_violations_tracking(self):
        stats = RiskStatistics()
        await stats.record_evaluation(
            RiskDecision.REJECTED, 80.0,
            {"max_loss": False, "max_leverage": False},
            {"max_loss": PolicyCategory.LOSS_LIMITS, "max_leverage": PolicyCategory.LEVERAGE},
        )
        snapshot = await stats.get_snapshot()
        assert snapshot.policy_violations["max_loss"] == 1
        assert snapshot.policy_violations["max_leverage"] == 1

    @pytest.mark.asyncio
    async def test_category_violations(self):
        stats = RiskStatistics()
        await stats.record_evaluation(
            RiskDecision.REJECTED, 80.0,
            {"max_loss": False},
            {"max_loss": PolicyCategory.LOSS_LIMITS},
        )
        snapshot = await stats.get_snapshot()
        assert snapshot.category_violations["loss_limits"] == 1

    @pytest.mark.asyncio
    async def test_violation_accumulation(self):
        stats = RiskStatistics()
        for _ in range(3):
            await stats.record_evaluation(
                RiskDecision.REJECTED, 80.0,
                {"max_loss": False},
                {"max_loss": PolicyCategory.LOSS_LIMITS},
            )
        assert await stats.get_policy_violations("max_loss") == 3

    @pytest.mark.asyncio
    async def test_streak_tracking(self):
        stats = RiskStatistics()

        # 3 approvals
        for _ in range(3):
            await stats.record_evaluation(
                RiskDecision.APPROVED, 20.0,
                {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        snapshot = await stats.get_snapshot()
        assert snapshot.current_streak_approved == 3
        assert snapshot.current_streak_rejected == 0

        # 2 rejections
        for _ in range(2):
            await stats.record_evaluation(
                RiskDecision.REJECTED, 80.0,
                {"p1": False}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        snapshot = await stats.get_snapshot()
        assert snapshot.current_streak_approved == 0
        assert snapshot.current_streak_rejected == 2

    @pytest.mark.asyncio
    async def test_worst_streak(self):
        stats = RiskStatistics()
        # 5 rejections in a row
        for _ in range(5):
            await stats.record_evaluation(
                RiskDecision.REJECTED, 80.0,
                {"p1": False}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        snapshot = await stats.get_snapshot()
        assert snapshot.worst_streak_rejected == 5

    @pytest.mark.asyncio
    async def test_emergency_activation(self):
        stats = RiskStatistics()
        await stats.record_emergency_activation()
        await stats.record_emergency_activation()
        snapshot = await stats.get_snapshot()
        assert snapshot.emergency_activations == 2

    @pytest.mark.asyncio
    async def test_reset(self):
        stats = RiskStatistics()
        await stats.record_evaluation(
            RiskDecision.APPROVED, 20.0,
            {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
        )
        await stats.reset()
        snapshot = await stats.get_snapshot()
        assert snapshot.total_evaluations == 0
        assert snapshot.total_approved == 0

    @pytest.mark.asyncio
    async def test_reset_daily(self):
        stats = RiskStatistics()
        await stats.record_evaluation(
            RiskDecision.REJECTED, 80.0,
            {"p1": False}, {"p1": PolicyCategory.LOSS_LIMITS},
        )
        await stats.reset_daily()
        snapshot = await stats.get_snapshot()
        assert snapshot.daily_violations == 0
        assert snapshot.daily_evaluations == 0
        # Total should be preserved
        assert snapshot.total_evaluations > 0

    @pytest.mark.asyncio
    async def test_daily_weekly_rollover(self):
        stats = RiskStatistics()
        # Force an older date
        import datetime as dt
        stats._current_date = (datetime.now(timezone.utc) - dt.timedelta(days=2)).date()
        stats._daily_violations = 10
        stats._weekly_violations = 20
        stats._monthly_violations = 30

        # Check rollover
        await stats.record_evaluation(
            RiskDecision.APPROVED, 10.0,
            {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
        )
        snapshot = await stats.get_snapshot()
        # Daily should have reset
        assert snapshot.daily_violations <= 1

    @pytest.mark.asyncio
    async def test_average_risk_score(self):
        stats = RiskStatistics()
        for score in [10.0, 20.0, 30.0]:
            await stats.record_evaluation(
                RiskDecision.APPROVED, score,
                {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
            )
        snapshot = await stats.get_snapshot()
        assert snapshot.average_risk_score == 20.0  # (10+20+30)/3

    @pytest.mark.asyncio
    async def test_rejection_rate(self):
        stats = RiskStatistics()
        await stats.record_evaluation(
            RiskDecision.APPROVED, 20.0,
            {"p1": True}, {"p1": PolicyCategory.LOSS_LIMITS},
        )
        await stats.record_evaluation(
            RiskDecision.REJECTED, 80.0,
            {"p1": False}, {"p1": PolicyCategory.LOSS_LIMITS},
        )
        snapshot = await stats.get_snapshot()
        assert snapshot.rejection_rate == 0.5

