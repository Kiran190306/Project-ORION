"""Trade execution history API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.persistence.models import AccountModel

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    get_user_account,
    require_permission,
)
from ..schemas import PaginatedResponse, PaginationParams, TradeResponse
from ..services.trade_service import TradeService

logger = logging.getLogger("trading_engine.routes.trades")

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])


@router.get(
    "/",
    response_model=PaginatedResponse[TradeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Trades",
    description="List executed trade fills for the authenticated user's account.",
)
async def list_trades(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    _perm: Annotated[Any, Depends(require_permission(Permission.TRADE_READ))],
    symbol: str | None = Query(None, description="Filter by instrument symbol"),
) -> PaginatedResponse[TradeResponse]:
    """List executed trades (fills) with pagination and filtering."""
    service = TradeService(session=session, account=account)
    return await service.list_trades(
        pagination=pagination,
        symbol=symbol,
    )


@router.get(
    "/{trade_id}",
    response_model=TradeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Trade",
    description="Retrieve a single trade/fill by ID with ownership verification.",
)
async def get_trade(
    trade_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.TRADE_READ))],
) -> TradeResponse:
    """Get single trade by ID."""
    service = TradeService(session=session, account=account)
    return await service.get_trade(trade_id)
