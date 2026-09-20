"""Trading endpoints for paper trade execution and status."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.domain.subscription.exceptions import (
    AssetNotEntitledError,
    DailyOrderQuotaExceededError,
    EntitlementError,
    SubscriptionInactiveError,
)
from libraries.infrastructure.persistence.models import AccountModel, AuditLogModel
from libraries.observability.metrics import MetricsRegistry

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_metrics_registry,
    get_paper_trading_service,
    get_user_account,
    require_permission,
)
from ..schemas import PaperTradeRequest, PaperTradeResponse
from ..services.entitlement_service import EntitlementService
from ..services.paper_trading import (
    PaperTradingError,
    PaperTradingNotReadyError,
    PaperTradingService,
)

logger = logging.getLogger("trading_engine.routes.trading")

router = APIRouter(prefix="/api/v1", tags=["Trading"])


@router.post(
    "/paper-trade",
    response_model=PaperTradeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Paper Trade",
    description="Submits an order to the simulated paper execution broker. Safe, deterministic, and uses no real capital.",
    responses={
        200: {"description": "Order submitted and executed on paper broker."},
        400: {"description": "Invalid trade parameters or trade rejected."},
        401: {"description": "Authentication credentials missing or invalid."},
        403: {"description": "Permission denied or asset not entitled under active subscription tier."},
        429: {"description": "Daily order quota exceeded."},
        503: {"description": "Paper broker adapter is not ready or connected."},
    },
)
async def execute_paper_trade(
    request: PaperTradeRequest,
    account: Annotated[AccountModel, Depends(get_user_account)],
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    metrics: Annotated[MetricsRegistry, Depends(get_metrics_registry)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_CREATE))],
) -> PaperTradeResponse:
    """Execute a paper trade through the domain execution pipeline to PaperExecutionAdapter."""
    # Enforce tier quotas and asset entitlement
    entitlement_service = EntitlementService(session)
    try:
        await entitlement_service.check_asset_access(
            account.organization_id, request.symbol
        )
        await entitlement_service.check_daily_order_quota(
            account.organization_id
        )
    except AssetNotEntitledError as exc:
        logger.warning(
            "Paper trade rejected: asset not entitled: symbol=%s org=%s",
            request.symbol,
            account.organization_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc
    except DailyOrderQuotaExceededError as exc:
        logger.warning(
            "Paper trade rejected: daily order quota exceeded: org=%s current=%s limit=%s",
            account.organization_id,
            exc.current,
            exc.limit,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=exc.message,
        ) from exc
    except SubscriptionInactiveError as exc:
        logger.warning(
            "Paper trade rejected: subscription inactive: org=%s status=%s",
            account.organization_id,
            exc.status,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc
    except EntitlementError as exc:
        logger.warning(
            "Paper trade rejected: entitlement error: org=%s detail=%s",
            account.organization_id,
            exc.message,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc

    decision = service.create_decision(
        symbol=request.symbol,
        direction=request.direction.value,
        confidence=request.confidence,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        position_size=request.position_size,
    )

    try:
        result = await service.execute(decision)
    except PaperTradingNotReadyError as exc:
        logger.warning("Paper trading service not ready: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PaperTradingError as exc:
        logger.warning("Paper trade failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    now = datetime.now(timezone.utc)

    # Record immutable audit log
    audit_entry = AuditLogModel(
        id=f"aud_{uuid.uuid4().hex[:16]}",
        organization_id=account.organization_id,
        event_type="paper_trade.executed",
        component="trading_engine.paper_trading",
        actor=str(user["id"]),
        details={
            "order_id": result.order_id,
            "symbol": result.symbol,
            "direction": result.direction,
            "fill_price": str(result.fill_price),
            "quantity": str(result.filled_quantity),
            "status": result.status,
            "account_id": account.id,
        },
        timestamp=now,
    )
    session.add(audit_entry)
    await session.flush()

    # Increment business metrics
    try:
        metrics.inc("paper_trades_total", 1.0)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Metrics emission skipped: %s", exc)

    return PaperTradeResponse(
        order_id=result.order_id,
        status=result.status,
        symbol=result.symbol,
        direction=result.direction,
        fill_price=result.fill_price,
        filled_quantity=result.filled_quantity,
        commission=result.commission,
        is_paper=True,
        executed_at=now,
        metadata=result.metadata or {},
    )

