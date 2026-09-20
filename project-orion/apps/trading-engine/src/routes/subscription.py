"""Subscription and entitlement API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from libraries.domain.organization.permissions import Permission
from libraries.domain.subscription.models import PlanCode

from ..dependencies import (
    TenantContext,
    get_current_active_user,
    get_entitlement_service,
    get_subscription_service,
    require_permission,
)
from ..services.entitlement_service import EntitlementService
from ..services.subscription_service import SubscriptionService

logger = logging.getLogger("trading_engine.routes.subscription")

router = APIRouter(prefix="/api/v1", tags=["Subscriptions"])


class PlanLimitsResponse(BaseModel):
    max_accounts: int
    max_daily_orders: int
    max_workers: int
    allowed_assets: list[str]
    retention_days: int


class PlanResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    limits: PlanLimitsResponse
    is_active: bool


class SubscriptionResponse(BaseModel):
    id: str | None = None
    organization_id: str | None = None
    plan: PlanResponse
    status: str
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False


class ChangePlanRequest(BaseModel):
    plan_code: str = Field(description="Target plan tier (FREE, PRO, BUSINESS, ENTERPRISE)")


@router.get(
    "/plans",
    response_model=list[PlanResponse],
    status_code=status.HTTP_200_OK,
    summary="List Subscription Plans",
    description="Returns all active subscription tiers and quota specifications.",
)
async def list_plans(
    sub_service: Annotated[SubscriptionService, Depends(get_subscription_service)],
    _perm: Annotated[Any, Depends(require_permission(Permission.SUBSCRIPTION_READ))],
) -> list[PlanResponse]:
    """List available subscription plans."""
    plans = await sub_service.list_plans()
    return [
        PlanResponse(
            id=p.id,
            code=p.code.value,
            name=p.name,
            description=p.description,
            limits=PlanLimitsResponse(
                max_accounts=p.limits.max_accounts,
                max_daily_orders=p.limits.max_daily_orders,
                max_workers=p.limits.max_workers,
                allowed_assets=list(p.limits.allowed_assets),
                retention_days=p.limits.retention_days,
            ),
            is_active=p.is_active,
        )
        for p in plans
    ]


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Subscription",
    description="Returns active subscription details for the tenant organization or sandbox defaults.",
)
async def get_subscription(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_READ))],
    sub_service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Get active subscription for current organization or default sandbox tier."""
    org_id = tenant_context.organization_id
    if org_id is None:
        free_plan = await sub_service.get_plan_by_code(PlanCode.FREE)
        if free_plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default Free plan not initialized.",
            )
        return SubscriptionResponse(
            id=None,
            organization_id=None,
            plan=PlanResponse(
                id=free_plan.id,
                code=free_plan.code.value,
                name=free_plan.name,
                description=free_plan.description,
                limits=PlanLimitsResponse(
                    max_accounts=free_plan.limits.max_accounts,
                    max_daily_orders=free_plan.limits.max_daily_orders,
                    max_workers=free_plan.limits.max_workers,
                    allowed_assets=list(free_plan.limits.allowed_assets),
                    retention_days=free_plan.limits.retention_days,
                ),
                is_active=free_plan.is_active,
            ),
            status="active",
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
        )

    sub, plan = await sub_service.get_active_subscription(org_id)
    if sub is None or plan is None:
        # Provision default
        sub = await sub_service.assign_default_subscription(org_id)
        plan = await sub_service.get_plan(sub.plan_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Plan lookup failed after provisioning.",
            )

    return SubscriptionResponse(
        id=sub.id,
        organization_id=sub.organization_id,
        plan=PlanResponse(
            id=plan.id,
            code=plan.code.value,
            name=plan.name,
            description=plan.description,
            limits=PlanLimitsResponse(
                max_accounts=plan.limits.max_accounts,
                max_daily_orders=plan.limits.max_daily_orders,
                max_workers=plan.limits.max_workers,
                allowed_assets=list(plan.limits.allowed_assets),
                retention_days=plan.limits.retention_days,
            ),
            is_active=plan.is_active,
        ),
        status=sub.status.value,
        current_period_start=sub.current_period_start.isoformat(),
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
        cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.get(
    "/entitlements",
    status_code=status.HTTP_200_OK,
    summary="Get Organization Entitlements",
    description="Returns effective quota thresholds and current utilization summary.",
)
async def get_entitlements(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_READ))],
    entitlement_service: Annotated[EntitlementService, Depends(get_entitlement_service)],
) -> dict[str, Any]:
    """Get effective quotas and resource usage for current tenant context."""
    return await entitlement_service.get_usage_summary(tenant_context.organization_id)


@router.post(
    "/subscription/change-plan",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Subscription Plan",
    description="Upgrade or change subscription plan tier for the tenant organization. Requires SUBSCRIPTION_MANAGE.",
)
async def change_plan(
    request: ChangePlanRequest,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.SUBSCRIPTION_MANAGE))],
    sub_service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Change subscription plan tier."""
    org_id = tenant_context.organization_id
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header 'X-Organization-ID' is required to manage subscriptions.",
        )

    try:
        plan_code = PlanCode.from_str(request.plan_code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        sub = await sub_service.change_plan(org_id, plan_code)
        plan = await sub_service.get_plan(sub.plan_id)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Plan lookup failed after tier change.",
            )
        return SubscriptionResponse(
            id=sub.id,
            organization_id=sub.organization_id,
            plan=PlanResponse(
                id=plan.id,
                code=plan.code.value,
                name=plan.name,
                description=plan.description,
                limits=PlanLimitsResponse(
                    max_accounts=plan.limits.max_accounts,
                    max_daily_orders=plan.limits.max_daily_orders,
                    max_workers=plan.limits.max_workers,
                    allowed_assets=list(plan.limits.allowed_assets),
                    retention_days=plan.limits.retention_days,
                ),
                is_active=plan.is_active,
            ),
            status=sub.status.value,
            current_period_start=sub.current_period_start.isoformat(),
            current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None,
            cancel_at_period_end=sub.cancel_at_period_end,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
