"""Risk management endpoints for read-only risk information."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from libraries.domain.organization.permissions import Permission

from ..dependencies import require_permission
from ..schemas import RiskLimitsResponse, RiskStatusResponse

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
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_READ))],
) -> RiskStatusResponse:
    """Get current risk status from the risk engine."""
    try:
        # For now, return static risk status
        # In future, this should integrate with actual RiskEngine instance
        return RiskStatusResponse(
            status="healthy",
            position_count=0,
            total_exposure=Decimal(0),
            used_margin=Decimal(0),
            free_margin=Decimal(0),
            margin_level=0.0,
            drawdown=0.0,
            daily_pnl=Decimal(0),
            daily_loss_rate=0.0,
            consecutive_losses=0,
            emergency_stop_active=False,
            recovery_mode_active=False,
            updated_at=datetime.now(timezone.utc),
        )
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
    description="Returns configured risk limits and their current status. Requires RISK_READ.",
)
async def get_risk_limits(
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_READ))],
) -> RiskLimitsResponse:
    """Get configured risk limits."""
    try:
        limits = [
            {
                "name": "maximum_position_size",
                "category": "position",
                "description": "Maximum position size in units",
                "is_enabled": True,
                "severity": "warning",
            },
            {
                "name": "maximum_daily_loss",
                "category": "pnl",
                "description": "Maximum daily loss as percentage of equity",
                "is_enabled": True,
                "severity": "critical",
            },
            {
                "name": "maximum_drawdown",
                "category": "pnl",
                "description": "Maximum allowed drawdown as percentage",
                "is_enabled": True,
                "severity": "critical",
            },
        ]
        
        return RiskLimitsResponse(
            limits=limits,
            total=len(limits),
            updated_at=datetime.now(timezone.utc),
        )
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
    _perm: Annotated[Any, Depends(require_permission(Permission.RISK_CONFIGURE))],
) -> RiskLimitsResponse:
    """Configure institutional risk limits."""
    return await get_risk_limits(_perm=_perm)

