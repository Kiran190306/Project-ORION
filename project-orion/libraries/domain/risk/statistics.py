"""Risk Statistics - tracks risk evaluation metrics.

Monitors:
- Risk Approvals / Rejections / Deferrals
- Policy Violations per policy
- Average Risk Score (overall and per category)
- Daily / Weekly / Monthly violation counts
- Emergency mode activations
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from libraries.domain.risk.models import PolicyCategory, RiskDecision


@dataclass(frozen=True, slots=True)
class RiskStatsSnapshot:
    """Snapshot of risk statistics at a point in time."""

    total_evaluations: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_deferred: int = 0
    approval_rate: float = 0.0
    rejection_rate: float = 0.0
    average_risk_score: float = 0.0
    policy_violations: dict[str, int] = field(default_factory=dict)
    category_violations: dict[str, int] = field(default_factory=dict)
    daily_evaluations: int = 0
    daily_approved: int = 0
    daily_rejected: int = 0
    daily_violations: int = 0
    weekly_violations: int = 0
    monthly_violations: int = 0
    emergency_activations: int = 0
    current_streak_approved: int = 0
    current_streak_rejected: int = 0
    worst_streak_rejected: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskStatistics:
    """Tracks risk evaluation statistics.

    Thread-safe via asyncio.Lock. Maintains running counters and
    per-period rollups.
    """

    def __init__(self, max_records: int = 10000) -> None:
        self._lock = asyncio.Lock()
        self._records: list[dict[str, Any]] = []
        self._max_records = max_records

        # Running counters
        self._total_evaluations = 0
        self._total_approved = 0
        self._total_rejected = 0
        self._total_deferred = 0
        self._total_risk_score = 0.0

        # Violation tracking
        self._policy_violations: dict[str, int] = {}
        self._category_violations: dict[str, int] = {}

        # Streak tracking
        self._current_streak_approved = 0
        self._current_streak_rejected = 0
        self._worst_streak_rejected = 0

        # Emergency mode tracking
        self._emergency_activations = 0

        # Periodic tracking
        self._current_date: date = datetime.now(timezone.utc).date()
        self._daily_evaluations = 0
        self._daily_approved = 0
        self._daily_rejected = 0
        self._daily_violations = 0
        self._weekly_violations = 0
        self._monthly_violations = 0

    async def record_evaluation(
        self,
        decision: RiskDecision,
        risk_score: float,
        policy_violations: dict[str, bool],
        policy_categories: dict[str, PolicyCategory],
    ) -> None:
        """Record a risk evaluation.

        Args:
            decision: The final decision.
            risk_score: The overall risk score (0–100).
            policy_violations: {policy_name: passed} dict.
            policy_categories: {policy_name: category} dict.
        """
        async with self._lock:
            self._check_date_rollover()

            self._total_evaluations += 1
            self._total_risk_score += risk_score
            self._daily_evaluations += 1

            if decision == RiskDecision.APPROVED:
                self._total_approved += 1
                self._daily_approved += 1
                self._current_streak_approved += 1
                self._current_streak_rejected = 0
            elif decision == RiskDecision.REJECTED:
                self._total_rejected += 1
                self._daily_rejected += 1
                self._current_streak_rejected += 1
                self._current_streak_approved = 0
                self._worst_streak_rejected = max(
                    self._worst_streak_rejected, self._current_streak_rejected
                )
            elif decision == RiskDecision.DEFERRED:
                self._total_deferred += 1

            # Track violations per policy
            for policy_name, passed in policy_violations.items():
                if not passed:
                    self._policy_violations[policy_name] = (
                        self._policy_violations.get(policy_name, 0) + 1
                    )
                    self._daily_violations += 1
                    self._weekly_violations += 1
                    self._monthly_violations += 1

                    category = policy_categories.get(policy_name)
                    if category is not None:
                        cat_key = category.value
                        self._category_violations[cat_key] = (
                            self._category_violations.get(cat_key, 0) + 1
                        )

    async def record_emergency_activation(self) -> None:
        """Record an emergency mode activation."""
        async with self._lock:
            self._emergency_activations += 1

    async def get_snapshot(self) -> RiskStatsSnapshot:
        """Return a snapshot of current statistics.

        Returns:
            RiskStatsSnapshot with current values.
        """
        async with self._lock:
            self._check_date_rollover()

            total = self._total_evaluations
            approval_rate = self._total_approved / total if total > 0 else 0.0
            rejection_rate = self._total_rejected / total if total > 0 else 0.0
            avg_score = self._total_risk_score / total if total > 0 else 0.0

            return RiskStatsSnapshot(
                total_evaluations=self._total_evaluations,
                total_approved=self._total_approved,
                total_rejected=self._total_rejected,
                total_deferred=self._total_deferred,
                approval_rate=round(approval_rate, 4),
                rejection_rate=round(rejection_rate, 4),
                average_risk_score=round(avg_score, 2),
                policy_violations=dict(self._policy_violations),
                category_violations=dict(self._category_violations),
                daily_evaluations=self._daily_evaluations,
                daily_approved=self._daily_approved,
                daily_rejected=self._daily_rejected,
                daily_violations=self._daily_violations,
                weekly_violations=self._weekly_violations,
                monthly_violations=self._monthly_violations,
                emergency_activations=self._emergency_activations,
                current_streak_approved=self._current_streak_approved,
                current_streak_rejected=self._current_streak_rejected,
                worst_streak_rejected=self._worst_streak_rejected,
            )

    async def get_policy_violations(self, policy_name: str) -> int:
        """Get violation count for a specific policy.

        Args:
            policy_name: Policy name.

        Returns:
            Number of violations.
        """
        async with self._lock:
            return self._policy_violations.get(policy_name, 0)

    async def reset(self) -> None:
        """Reset all statistics."""
        async with self._lock:
            self._records.clear()
            self._total_evaluations = 0
            self._total_approved = 0
            self._total_rejected = 0
            self._total_deferred = 0
            self._total_risk_score = 0.0
            self._policy_violations.clear()
            self._category_violations.clear()
            self._current_streak_approved = 0
            self._current_streak_rejected = 0
            self._worst_streak_rejected = 0
            self._emergency_activations = 0
            self._daily_evaluations = 0
            self._daily_approved = 0
            self._daily_rejected = 0
            self._daily_violations = 0
            self._weekly_violations = 0
            self._monthly_violations = 0

    async def reset_daily(self) -> None:
        """Reset daily counters."""
        async with self._lock:
            self._daily_evaluations = 0
            self._daily_approved = 0
            self._daily_rejected = 0
            self._daily_violations = 0

    async def reset_weekly(self) -> None:
        """Reset weekly counters."""
        async with self._lock:
            self._weekly_violations = 0

    async def reset_monthly(self) -> None:
        """Reset monthly counters."""
        async with self._lock:
            self._monthly_violations = 0

    def _check_date_rollover(self) -> None:
        """Reset daily counter if a new day has started."""
        today = datetime.now(timezone.utc).date()
        if today > self._current_date:
            # Check if we crossed a week boundary
            if today.isocalendar()[1] != self._current_date.isocalendar()[1]:
                self._weekly_violations = 0
            # Check if we crossed a month boundary
            if today.month != self._current_date.month:
                self._monthly_violations = 0

            self._daily_evaluations = 0
            self._daily_approved = 0
            self._daily_rejected = 0
            self._daily_violations = 0
            self._current_date = today
