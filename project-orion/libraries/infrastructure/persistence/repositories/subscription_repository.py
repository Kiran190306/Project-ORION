"""SQLAlchemy implementation of PlanRepository and SubscriptionRepository protocols."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.subscription.models import (
    Plan,
    PlanCode,
    Subscription,
    SubscriptionStatus,
)
from libraries.domain.subscription.repository import (
    PlanRepository,
    SubscriptionRepository,
)
from libraries.infrastructure.persistence.models.subscription import (
    PlanModel,
    SubscriptionModel,
)

logger = logging.getLogger("infrastructure.persistence.repositories.subscription")


class SQLAlchemyPlanRepository(PlanRepository):
    """Async SQLAlchemy persistence repository for SaaS subscription plans."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_plan(self, plan_id: str) -> Plan | None:
        """Fetch a plan by its primary identifier."""
        stmt = select(PlanModel).where(PlanModel.id == plan_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_plan_by_code(self, code: PlanCode | str) -> Plan | None:
        """Fetch a plan by its unique plan code."""
        code_str = code.value if isinstance(code, PlanCode) else str(code).upper()
        stmt = select(PlanModel).where(PlanModel.code == code_str)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_active_plans(self) -> list[Plan]:
        """List all active subscription plans ordered by accounts limit."""
        stmt = select(PlanModel).where(PlanModel.is_active.is_(True)).order_by(PlanModel.max_accounts)
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [m.to_domain() for m in models]

    async def create_plan(self, plan: Plan) -> Plan:
        """Persist a new subscription plan."""
        model = PlanModel(
            id=plan.id,
            code=plan.code.value,
            name=plan.name,
            description=plan.description,
            max_accounts=plan.limits.max_accounts,
            max_daily_orders=plan.limits.max_daily_orders,
            max_workers=plan.limits.max_workers,
            allowed_assets=list(plan.limits.allowed_assets),
            retention_days=plan.limits.retention_days,
            is_active=plan.is_active,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model.to_domain()


class SQLAlchemySubscriptionRepository(SubscriptionRepository):
    """Async SQLAlchemy persistence repository for tenant subscriptions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_subscription(self, subscription: Subscription) -> Subscription:
        """Persist a new subscription for an organization."""
        model = SubscriptionModel(
            id=subscription.id,
            organization_id=subscription.organization_id,
            plan_id=subscription.plan_id,
            status=subscription.status.value,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            meta_data=subscription.meta_data,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return model.to_domain()

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        """Fetch a subscription by its primary identifier."""
        stmt = select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def get_active_subscription_by_org(self, organization_id: str) -> Subscription | None:
        """Fetch the current active or trialing subscription for an organization."""
        stmt = (
            select(SubscriptionModel)
            .where(
                SubscriptionModel.organization_id == organization_id,
                SubscriptionModel.status.in_([SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value]),
            )
            .order_by(SubscriptionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return model.to_domain() if model else None

    async def get_latest_subscription_by_org(self, organization_id: str) -> Subscription | None:
        """Fetch the most recent subscription for an organization regardless of status."""
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.organization_id == organization_id)
            .order_by(SubscriptionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        model = result.scalars().first()
        return model.to_domain() if model else None

    async def list_subscriptions_by_org(self, organization_id: str) -> list[Subscription]:
        """List all subscriptions for an organization ordered by creation time descending."""
        stmt = (
            select(SubscriptionModel)
            .where(SubscriptionModel.organization_id == organization_id)
            .order_by(SubscriptionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [m.to_domain() for m in models]

    async def update_subscription(self, subscription: Subscription) -> Subscription:
        """Update an existing subscription's status, period, or metadata."""
        stmt = select(SubscriptionModel).where(SubscriptionModel.id == subscription.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        model.plan_id = subscription.plan_id
        model.status = subscription.status.value
        model.current_period_start = subscription.current_period_start
        model.current_period_end = subscription.current_period_end
        model.cancel_at_period_end = subscription.cancel_at_period_end
        model.meta_data = subscription.meta_data
        model.updated_at = subscription.updated_at
        await self._session.flush()
        return model.to_domain()
