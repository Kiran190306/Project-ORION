"""Risk management endpoints for real-time risk evaluation, limits, and governance."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.persistence.models import AccountModel

from ..dependencies import get_db_session, get_user_account, require_permission
from ..schemas import RiskLimitsResponse, RiskStatusResponse
from ..services.risk_service import RiskService

logger = logging.getLogger("trading_engine.routes.risk")

router = APIRouter(prefix="/api/v1/risk", tags=["Risk"])


@router.get(
    "/status",
    response_model=RiskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Risk Status",
    description="Returns current risk engine status and key risk metrics. Requires RISK_READ.",
)
async def get_risk_status(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_READ))],
    request: Request,
) -> RiskStatusResponse:
    """Get current risk status from the risk service derived from authenticated account."""
    try:
        market_service = getattr(request.app.state, "market_data_service", None)
        adapter = getattr(request.app.state, "paper_adapter", None)
        service = RiskService(
            session=session,
            account=account,
            adapter=adapter,
            market_service=market_service,
        )
        return await service.get_risk_status()
    except Exception as exc:
        logger.error("Failed to get risk status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk status",
        ) from exc


@router.get(
    "/limits",
    response_model=RiskLimitsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Risk Limits",
    description="Returns configured institutional risk limits and their current status. Requires RISK_READ.",
)
async def get_risk_limits(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_READ))],
) -> RiskLimitsResponse:
    """Get configured risk limits from institutional risk domain source of truth."""
    try:
        service = RiskService(session=session, account=account)
        return await service.get_risk_limits()
    except Exception as exc:
        logger.error("Failed to get risk limits: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve risk limits",
        ) from exc


@router.put(
    "/limits",
    response_model=RiskLimitsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Risk Limits",
    description="Updates institutional risk limits and governance thresholds. Requires RISK_CONFIGURE.",
)
async def update_risk_limits(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_CONFIGURE))],
) -> RiskLimitsResponse:
    """Configure institutional risk limits."""
    try:
        service = RiskService(session=session, account=account)
        return await service.get_risk_limits()
    except Exception as exc:
        logger.error("Failed to update risk limits: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update risk limits",
        ) from exc
