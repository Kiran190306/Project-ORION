"""Subscription application service for managing tenant plan subscriptions."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.subscription.models import (
    Plan,
    PlanCode,
    PlanLimits,
    Subscription,
    SubscriptionStatus,
)
from libraries.domain.subscription.repository import (
    PlanRepository,
    SubscriptionRepository,
)
from libraries.infrastructure.persistence.repositories.subscription_repository import (
    SQLAlchemyPlanRepository,
    SQLAlchemySubscriptionRepository,
)

logger = logging.getLogger("trading_engine.services.subscription")

CANONICAL_PLANS: list[Plan] = [
    Plan(
        id="plan-free",
        code=PlanCode.FREE,
        name="Free Sandbox",
        description="Free Sandbox tier with basic paper trading capabilities",
        limits=PlanLimits(
            max_accounts=1,
            max_daily_orders=100,
            max_workers=0,
            allowed_assets=("EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"),
            retention_days=30,
        ),
        is_active=True,
    ),
    Plan(
        id="plan-pro",
        code=PlanCode.PRO,
        name="Pro Trader",
        description="Professional paper trading with expanded assets and autonomous worker",
        limits=PlanLimits(
            max_accounts=3,
            max_daily_orders=2500,
            max_workers=1,
            allowed_assets=(
                "EUR/USD",
                "GBP/USD",
                "USD/JPY",
                "USD/CHF",
                "AUD/USD",
                "USD/CAD",
                "NZD/USD",
                "EUR/GBP",
                "EUR/JPY",
                "GBP/JPY",
                "AUD/JPY",
                "EUR/CHF",
            ),
            retention_days=365,
        ),
        is_active=True,
    ),
    Plan(
        id="plan-business",
        code=PlanCode.BUSINESS,
        name="Business / Prop Desk",
        description="Multi-account prop desk tier with all currency pairs and 5 workers",
        limits=PlanLimits(
            max_accounts=10,
            max_daily_orders=50000,
            max_workers=5,
            allowed_assets=("*",),
            retention_days=1825,
        ),
        is_active=True,
    ),
    Plan(
        id="plan-enterprise",
        code=PlanCode.ENTERPRISE,
        name="Enterprise Institutional",
        description="Unlimited enterprise capacity with maximum data retention and support",
        limits=PlanLimits(
            max_accounts=-1,
            max_daily_orders=-1,
            max_workers=-1,
            allowed_assets=("*",),
            retention_days=2555,
        ),
        is_active=True,
    ),
]


class SubscriptionService:
    """Application service coordinating subscription lifecycle and tier assignments."""

    def __init__(
        self,
        session: AsyncSession,
        plan_repo: PlanRepository | None = None,
        sub_repo: SubscriptionRepository | None = None,
    ) -> None:
        self.session = session
        self.plan_repo = plan_repo or SQLAlchemyPlanRepository(session)
        self.sub_repo = sub_repo or SQLAlchemySubscriptionRepository(session)

    async def _ensure_canonical_plans(self) -> None:
        """Seed canonical plans if they are missing (e.g. in test environments)."""
        free_plan = await self.plan_repo.get_plan_by_code(PlanCode.FREE)
        if free_plan is None:
            for plan in CANONICAL_PLANS:
                existing = await self.plan_repo.get_plan(plan.id)
                if existing is None:
                    await self.plan_repo.create_plan(plan)

    async def get_active_subscription(
        self,
        organization_id: str,
    ) -> tuple[Subscription | None, Plan | None]:
        """Fetch active or trialing subscription and corresponding plan for an organization."""
        sub = await self.sub_repo.get_active_subscription_by_org(organization_id)
        if sub is None:
            return None, None

        plan = await self.plan_repo.get_plan(sub.plan_id)
        return sub, plan

    async def get_subscription_and_plan(
        self,
        organization_id: str,
    ) -> tuple[Subscription | None, Plan | None]:
        """Fetch latest subscription and corresponding plan for an organization regardless of status."""
        sub = await self.sub_repo.get_latest_subscription_by_org(organization_id)
        if sub is None:
            return None, None

        plan = await self.plan_repo.get_plan(sub.plan_id)
        return sub, plan

    async def assign_default_subscription(self, organization_id: str) -> Subscription:
        """Provision a default FREE Sandbox subscription for an organization."""
        # Verify if a subscription already exists
        existing, _ = await self.get_subscription_and_plan(organization_id)
        if existing is not None:
            return existing

        free_plan = await self.plan_repo.get_plan_by_code(PlanCode.FREE)
        if free_plan is None:
            # Plan lookup fallback by ID
            free_plan = await self.plan_repo.get_plan("plan-free")
        if free_plan is None:
            await self._ensure_canonical_plans()
            free_plan = await self.plan_repo.get_plan_by_code(PlanCode.FREE)
            if free_plan is None:
                raise ValueError("Free subscription plan ('plan-free' / 'FREE') not found in system.")

        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=f"sub_{uuid.uuid4().hex[:16]}",
            organization_id=organization_id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=None,
            cancel_at_period_end=False,
            created_at=now,
            updated_at=now,
            meta_data={"provisioned_by": "default_assignment"},
        )
        created = await self.sub_repo.create_subscription(sub)
        logger.info(
            "Assigned default FREE subscription %s to organization %s",
            created.id,
            organization_id,
        )
        return created

    async def get_plan_by_code(self, code: PlanCode | str) -> Plan | None:
        """Fetch a plan by code."""
        plan = await self.plan_repo.get_plan_by_code(code)
        if plan is None:
            await self._ensure_canonical_plans()
            plan = await self.plan_repo.get_plan_by_code(code)
        return plan

    async def get_plan(self, plan_id: str) -> Plan | None:
        """Fetch a plan by ID."""
        return await self.plan_repo.get_plan(plan_id)

    async def list_plans(self) -> list[Plan]:
        """List all active subscription plans."""
        plans = await self.plan_repo.list_active_plans()
        if not plans:
            await self._ensure_canonical_plans()
            plans = await self.plan_repo.list_active_plans()
        return plans

    async def change_plan(
        self,
        organization_id: str,
        new_plan_code: PlanCode | str,
    ) -> Subscription:
        """Change organization's plan tier (upgrade or downgrade)."""
        target_plan = await self.plan_repo.get_plan_by_code(new_plan_code)
        if target_plan is None:
            raise ValueError(f"Plan '{new_plan_code}' not found.")

        current_sub, _ = await self.get_active_subscription(organization_id)
        now = datetime.now(timezone.utc)

        if current_sub is None:
            # Create new subscription
            new_sub = Subscription(
                id=f"sub_{uuid.uuid4().hex[:16]}",
                organization_id=organization_id,
                plan_id=target_plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=now,
                current_period_end=None,
                cancel_at_period_end=False,
                created_at=now,
                updated_at=now,
                meta_data={"upgraded_from": None},
            )
            return await self.sub_repo.create_subscription(new_sub)

        # Update existing active subscription
        updated_sub = Subscription(
            id=current_sub.id,
            organization_id=current_sub.organization_id,
            plan_id=target_plan.id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=current_sub.current_period_start,
            current_period_end=current_sub.current_period_end,
            cancel_at_period_end=False,
            created_at=current_sub.created_at,
            updated_at=now,
            meta_data={
                **current_sub.meta_data,
                "previous_plan_id": current_sub.plan_id,
                "changed_at": now.isoformat(),
            },
        )
        return await self.sub_repo.update_subscription(updated_sub)

    async def cancel_subscription(self, organization_id: str) -> Subscription:
        """Cancel an organization's active subscription."""
        current_sub, _ = await self.get_active_subscription(organization_id)
        if current_sub is None:
            raise ValueError(f"No active subscription found for organization '{organization_id}'.")

        now = datetime.now(timezone.utc)
        cancelled = Subscription(
            id=current_sub.id,
            organization_id=current_sub.organization_id,
            plan_id=current_sub.plan_id,
            status=SubscriptionStatus.CANCELLED,
            current_period_start=current_sub.current_period_start,
            current_period_end=now,
            cancel_at_period_end=True,
            created_at=current_sub.created_at,
            updated_at=now,
            meta_data={**current_sub.meta_data, "cancelled_at": now.isoformat()},
        )
        return await self.sub_repo.update_subscription(cancelled)
