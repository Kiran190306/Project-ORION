"""Entitlement application service enforcing plan quotas and instrument access."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.subscription.exceptions import (
    AccountQuotaExceededError,
    ActiveDeploymentLimitExceededError,
    AssetNotEntitledError,
    DailyOptimizationQuotaExceededError,
    DailyOrderQuotaExceededError,
    DailyResearchQuotaExceededError,
    MonthlyDeploymentQuotaExceededError,
    OptimizationCombinationLimitExceededError,
    ResearchHistoryLimitExceededError,
    SubscriptionInactiveError,
    WorkerQuotaExceededError,
)
from libraries.domain.subscription.models import (
    Entitlement,
    Plan,
    PlanCode,
    PlanLimits,
)
from libraries.infrastructure.persistence.models import AccountModel, OrderModel

from .subscription_service import SubscriptionService

logger = logging.getLogger("trading_engine.services.entitlement")

# Canonical default Free sandbox limits for fallback / personal accounts
DEFAULT_FREE_LIMITS = PlanLimits(
    max_accounts=1,
    max_daily_orders=100,
    max_workers=0,
    allowed_assets=("EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF"),
    retention_days=30,
)

DEFAULT_FREE_PLAN = Plan(
    id="plan-free",
    code=PlanCode.FREE,
    name="Free Sandbox",
    description="Default Free Sandbox tier",
    limits=DEFAULT_FREE_LIMITS,
)


class EntitlementService:
    """Service providing fail-closed tenant quota validation and entitlement checks."""

    def __init__(
        self,
        session: AsyncSession,
        subscription_service: SubscriptionService | None = None,
    ) -> None:
        self.session = session
        self.subscription_service = subscription_service or SubscriptionService(session)

    async def get_effective_entitlement(self, organization_id: str | None) -> Entitlement:
        """Resolve effective entitlements for an organization or fallback to sandbox limits."""
        if organization_id is None:
            return Entitlement(
                organization_id="",
                plan=DEFAULT_FREE_PLAN,
                subscription=None,
                limits=DEFAULT_FREE_LIMITS,
            )

        sub, plan = await self.subscription_service.get_subscription_and_plan(organization_id)
        if sub is None or plan is None:
            # Auto-provision default Free subscription for new organization
            sub = await self.subscription_service.assign_default_subscription(organization_id)
            plan = await self.subscription_service.get_plan(sub.plan_id)
            if plan is None:
                plan = DEFAULT_FREE_PLAN

        return Entitlement(
            organization_id=organization_id,
            plan=plan,
            subscription=sub,
            limits=plan.limits,
        )

    async def check_account_quota(
        self,
        organization_id: str | None,
        current_count: int | None = None,
    ) -> None:
        """Verify organization does not exceed maximum permitted accounts."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        if entitlement.limits.max_accounts < 0:
            return  # Unlimited

        if current_count is None:
            if organization_id is not None:
                stmt = select(func.count(AccountModel.id)).where(
                    AccountModel.organization_id == organization_id
                )
            else:
                stmt = select(func.count(AccountModel.id)).where(
                    AccountModel.organization_id.is_(None)
                )
            result = await self.session.execute(stmt)
            count = int(result.scalar() or 0)
        else:
            count = current_count

        if not entitlement.limits.is_account_allowed(count):
            raise AccountQuotaExceededError(
                current=count,
                limit=entitlement.limits.max_accounts,
            )

    async def check_daily_order_quota(
        self,
        organization_id: str | None,
        current_daily_orders: int | None = None,
    ) -> None:
        """Verify organization has not exceeded maximum permitted orders for today (UTC)."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        if entitlement.limits.max_daily_orders < 0:
            return  # Unlimited

        if current_daily_orders is None:
            now = datetime.now(timezone.utc)
            start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

            if organization_id is not None:
                stmt = select(func.count(OrderModel.id)).where(
                    OrderModel.organization_id == organization_id,
                    OrderModel.created_at >= start_of_day,
                )
            else:
                stmt = select(func.count(OrderModel.id)).where(
                    OrderModel.organization_id.is_(None),
                    OrderModel.created_at >= start_of_day,
                )
            result = await self.session.execute(stmt)
            orders_today = int(result.scalar() or 0)
        else:
            orders_today = current_daily_orders

        if not entitlement.limits.is_daily_order_allowed(orders_today):
            raise DailyOrderQuotaExceededError(
                current=orders_today,
                limit=entitlement.limits.max_daily_orders,
            )

    async def check_worker_quota(
        self,
        organization_id: str | None,
        active_worker_count: int = 0,
    ) -> None:
        """Verify organization is entitled to run autonomous trading workers."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        if not entitlement.limits.is_worker_allowed(active_worker_count):
            raise WorkerQuotaExceededError(
                plan_name=entitlement.plan.name,
                limit=entitlement.limits.max_workers,
            )

    async def check_asset_access(
        self,
        organization_id: str | None,
        symbol: str,
    ) -> None:
        """Verify instrument is permitted under organization's subscription plan."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        if not entitlement.limits.is_asset_allowed(symbol):
            raise AssetNotEntitledError(
                symbol=symbol,
                plan_name=entitlement.plan.name,
            )

    async def check_daily_research_quota(
        self,
        organization_id: str | None,
        requested_days: int = 1,
    ) -> None:
        """Verify organization has not exceeded daily research experiment quotas or history limits."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        # Plan-based research limits
        plan_code = entitlement.plan.code
        if plan_code == PlanCode.FREE:
            max_daily_experiments = 10
            max_history_days = 30
        elif plan_code == PlanCode.PRO:
            max_daily_experiments = 50
            max_history_days = 180
        elif plan_code == PlanCode.BUSINESS:
            max_daily_experiments = 200
            max_history_days = 365
        else:  # ENTERPRISE
            max_daily_experiments = -1
            max_history_days = 3650

        if max_history_days > 0 and requested_days > max_history_days:
            raise ResearchHistoryLimitExceededError(
                requested_days=requested_days,
                limit_days=max_history_days,
            )

        if max_daily_experiments < 0:
            return  # Unlimited

        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        from libraries.infrastructure.persistence.models import ResearchExperimentModel

        if organization_id is not None:
            stmt = select(func.count(ResearchExperimentModel.id)).where(
                ResearchExperimentModel.organization_id == organization_id,
                ResearchExperimentModel.created_at >= start_of_day,
            )
        else:
            stmt = select(func.count(ResearchExperimentModel.id)).where(
                ResearchExperimentModel.created_at >= start_of_day,
            )
        result = await self.session.execute(stmt)
        experiments_today = int(result.scalar() or 0)

        if experiments_today >= max_daily_experiments:
            raise DailyResearchQuotaExceededError(
                current=experiments_today,
                limit=max_daily_experiments,
            )

    async def check_optimization_quota(
        self,
        organization_id: str | None,
        combinations_count: int,
    ) -> None:
        """Verify organization does not exceed parameter combination limits or daily optimization jobs."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        plan_code = entitlement.plan.code
        if plan_code == PlanCode.FREE:
            max_combinations = 50
            max_daily_optimizations = 5
        elif plan_code == PlanCode.PRO:
            max_combinations = 300
            max_daily_optimizations = 25
        elif plan_code == PlanCode.BUSINESS:
            max_combinations = 1000
            max_daily_optimizations = 100
        else:
            max_combinations = 5000
            max_daily_optimizations = 500

        # Check combination limit
        if combinations_count > max_combinations:
            raise OptimizationCombinationLimitExceededError(
                requested=combinations_count,
                limit=max_combinations,
            )

        # Check daily optimization runs
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

        from libraries.infrastructure.persistence.models.optimization import (
            OptimizationJobModel,
        )

        if organization_id is not None:
            stmt = select(func.count(OptimizationJobModel.id)).where(
                OptimizationJobModel.organization_id == organization_id,
                OptimizationJobModel.created_at >= start_of_day,
            )
        else:
            stmt = select(func.count(OptimizationJobModel.id)).where(
                OptimizationJobModel.created_at >= start_of_day,
            )
        result = await self.session.execute(stmt)
        optimizations_today = int(result.scalar() or 0)

        if optimizations_today >= max_daily_optimizations:
            raise DailyOptimizationQuotaExceededError(
                current=optimizations_today,
                limit=max_daily_optimizations,
            )

    async def check_deployment_quota(
        self,
        organization_id: str | None,
    ) -> None:
        """Verify organization does not exceed active or monthly deployment quotas."""
        entitlement = await self.get_effective_entitlement(organization_id)

        if entitlement.subscription is not None and not entitlement.subscription.is_active:
            raise SubscriptionInactiveError(entitlement.subscription.status.value)

        plan_code = entitlement.plan.code
        if plan_code == PlanCode.FREE:
            max_active_deployments = 1
            max_monthly_deployments = 3
        elif plan_code == PlanCode.PRO:
            max_active_deployments = 5
            max_monthly_deployments = 25
        elif plan_code == PlanCode.BUSINESS:
            max_active_deployments = 15
            max_monthly_deployments = 100
        else:
            max_active_deployments = 50
            max_monthly_deployments = 500

        from libraries.infrastructure.persistence.models.deployment import (
            StrategyDeploymentModel,
        )

        active_statuses = ("PENDING_GATES", "GATES_PASSED", "INCUBATING", "PAUSED")

        # 1. Check active concurrent deployments
        if organization_id is not None:
            active_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.organization_id == organization_id,
                StrategyDeploymentModel.status.in_(active_statuses),
            )
        else:
            active_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.status.in_(active_statuses),
            )
        active_res = await self.session.execute(active_stmt)
        active_count = int(active_res.scalar() or 0)

        if active_count >= max_active_deployments:
            raise ActiveDeploymentLimitExceededError(
                current=active_count,
                limit=max_active_deployments,
            )

        # 2. Check monthly promotions count
        now = datetime.now(timezone.utc)
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        if organization_id is not None:
            monthly_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.organization_id == organization_id,
                StrategyDeploymentModel.created_at >= start_of_month,
            )
        else:
            monthly_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.created_at >= start_of_month,
            )
        monthly_res = await self.session.execute(monthly_stmt)
        monthly_count = int(monthly_res.scalar() or 0)

        if monthly_count >= max_monthly_deployments:
            raise MonthlyDeploymentQuotaExceededError(
                current=monthly_count,
                limit=max_monthly_deployments,
            )

    async def get_usage_summary(self, organization_id: str | None) -> dict[str, Any]:
        """Aggregate current resource utilization against plan quota thresholds."""
        entitlement = await self.get_effective_entitlement(organization_id)

        # Accounts count
        if organization_id is not None:
            acc_stmt = select(func.count(AccountModel.id)).where(
                AccountModel.organization_id == organization_id
            )
        else:
            acc_stmt = select(func.count(AccountModel.id)).where(
                AccountModel.organization_id.is_(None)
            )
        acc_result = await self.session.execute(acc_stmt)
        accounts_count = int(acc_result.scalar() or 0)

        # Orders today (UTC)
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        if organization_id is not None:
            ord_stmt = select(func.count(OrderModel.id)).where(
                OrderModel.account_id.in_(
                    select(AccountModel.id).where(
                        AccountModel.organization_id == organization_id
                    )
                ),
                OrderModel.created_at >= start_of_day,
            )
        else:
            ord_stmt = select(func.count(OrderModel.id)).where(
                OrderModel.created_at >= start_of_day
            )
        ord_result = await self.session.execute(ord_stmt)
        orders_today = int(ord_result.scalar() or 0)

        # Research experiments today (UTC)
        from libraries.infrastructure.persistence.models.research import (
            ResearchExperimentModel,
        )

        if organization_id is not None:
            res_stmt = select(func.count(ResearchExperimentModel.id)).where(
                ResearchExperimentModel.organization_id == organization_id,
                ResearchExperimentModel.created_at >= start_of_day,
            )
        else:
            res_stmt = select(func.count(ResearchExperimentModel.id)).where(
                ResearchExperimentModel.created_at >= start_of_day,
            )
        res_result = await self.session.execute(res_stmt)
        research_today = int(res_result.scalar() or 0)

        # Optimization jobs today (UTC)
        from libraries.infrastructure.persistence.models.optimization import (
            OptimizationJobModel,
        )

        if organization_id is not None:
            opt_stmt = select(func.count(OptimizationJobModel.id)).where(
                OptimizationJobModel.organization_id == organization_id,
                OptimizationJobModel.created_at >= start_of_day,
            )
        else:
            opt_stmt = select(func.count(OptimizationJobModel.id)).where(
                OptimizationJobModel.created_at >= start_of_day,
            )
        opt_result = await self.session.execute(opt_stmt)
        optimizations_today = int(opt_result.scalar() or 0)

        # Deployments active and monthly count
        from libraries.infrastructure.persistence.models.deployment import (
            StrategyDeploymentModel,
        )

        active_statuses = ("PENDING_GATES", "GATES_PASSED", "INCUBATING", "PAUSED")
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        if organization_id is not None:
            dep_act_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.organization_id == organization_id,
                StrategyDeploymentModel.status.in_(active_statuses),
            )
            dep_mth_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.organization_id == organization_id,
                StrategyDeploymentModel.created_at >= start_of_month,
            )
        else:
            dep_act_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.status.in_(active_statuses),
            )
            dep_mth_stmt = select(func.count(StrategyDeploymentModel.id)).where(
                StrategyDeploymentModel.created_at >= start_of_month,
            )
        dep_act_res = await self.session.execute(dep_act_stmt)
        deployments_active = int(dep_act_res.scalar() or 0)
        dep_mth_res = await self.session.execute(dep_mth_stmt)
        deployments_monthly = int(dep_mth_res.scalar() or 0)

        plan_code = entitlement.plan.code
        if plan_code == PlanCode.FREE:
            max_daily_experiments = 10
            max_history_days = 30
            max_daily_optimizations = 5
            max_combinations = 50
            max_active_deployments = 1
            max_monthly_deployments = 3
        elif plan_code == PlanCode.PRO:
            max_daily_experiments = 50
            max_history_days = 180
            max_daily_optimizations = 25
            max_combinations = 300
            max_active_deployments = 5
            max_monthly_deployments = 25
        elif plan_code == PlanCode.BUSINESS:
            max_daily_experiments = 200
            max_history_days = 365
            max_daily_optimizations = 100
            max_combinations = 1000
            max_active_deployments = 15
            max_monthly_deployments = 100
        else:
            max_daily_experiments = -1
            max_history_days = 3650
            max_daily_optimizations = 500
            max_combinations = 5000
            max_active_deployments = 50
            max_monthly_deployments = 500

        return {
            "organization_id": organization_id,
            "plan_code": entitlement.plan.code.value,
            "plan_name": entitlement.plan.name,
            "subscription_status": entitlement.subscription.status.value if entitlement.subscription else "SANDBOX",
            "quotas": {
                "accounts": {
                    "used": accounts_count,
                    "limit": entitlement.limits.max_accounts,
                    "is_unlimited": entitlement.limits.max_accounts < 0,
                },
                "daily_orders": {
                    "used": orders_today,
                    "limit": entitlement.limits.max_daily_orders,
                    "is_unlimited": entitlement.limits.max_daily_orders < 0,
                },
                "research_experiments": {
                    "used": research_today,
                    "limit": max_daily_experiments,
                    "is_unlimited": max_daily_experiments < 0,
                    "max_history_days": max_history_days,
                },
                "optimization_jobs": {
                    "used": optimizations_today,
                    "limit": max_daily_optimizations,
                    "max_combinations": max_combinations,
                    "is_unlimited": max_daily_optimizations < 0,
                },
                "deployments": {
                    "active_used": deployments_active,
                    "active_limit": max_active_deployments,
                    "monthly_used": deployments_monthly,
                    "monthly_limit": max_monthly_deployments,
                    "is_unlimited": max_active_deployments < 0,
                },
                "workers": {
                    "used": 0,
                    "limit": entitlement.limits.max_workers,
                    "is_unlimited": entitlement.limits.max_workers < 0,
                },
                "allowed_assets": list(entitlement.limits.allowed_assets),
                "retention_days": entitlement.limits.retention_days,
            },
        }
