"""Onboarding route endpoints for tenant registration and initial provisioning."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from libraries.domain.security.rate_limit import RateLimitPolicies

from ..dependencies import get_onboarding_service, rate_limit
from ..schemas import OnboardingRegisterRequest, OnboardingResponse
from ..services.onboarding_service import OnboardingService

logger = logging.getLogger("trading_engine.routes.onboarding")

router = APIRouter(prefix="/api/v1/onboarding", tags=["Onboarding"])


@router.post(
    "/register",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Institutional Organization",
    description="Atomically registers a new customer user, creates an organization with OWNER role, provisions a default Free subscription, and initializes a $100,000 USD paper trading account.",
    dependencies=[Depends(rate_limit(RateLimitPolicies.ONBOARDING_REGISTER))],
)
async def register_organization(
    request: OnboardingRegisterRequest,
    http_request: Request,
    onboarding_service: Annotated[OnboardingService, Depends(get_onboarding_service)],
) -> OnboardingResponse:
    """Execute atomic institutional onboarding."""
    try:
        result = await onboarding_service.register_organization(
            username=request.username,
            email=request.email,
            password=request.password,
            organization_name=request.organization_name,
            organization_slug=request.organization_slug,
            full_name=request.full_name,
            user_agent=http_request.headers.get("User-Agent"),
        )
        return OnboardingResponse(
            user_id=result.user.id,
            username=result.user.username,
            email=result.user.email,
            organization_id=result.organization.id,
            organization_name=result.organization.name,
            organization_slug=result.organization.slug,
            role=result.membership.role.value,
            subscription_tier=result.subscription.plan_id.replace("plan-", "").upper(),
            account_id=result.account.id,
            account_number=result.account.account_number,
            initial_balance=result.account.balance,
            access_token=result.access_token,
            token_type="bearer",
            created_at=result.organization.created_at,
        )
    except ValueError as exc:
        msg = str(exc)
        if "already registered" in msg.lower() or "already in use" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        ) from exc
    except Exception as exc:
        logger.error("Onboarding failed unexpectedly: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register organization",
        ) from exc
