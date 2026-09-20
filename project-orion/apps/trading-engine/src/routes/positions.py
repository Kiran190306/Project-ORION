"""Position management API endpoints for paper trading."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import AccountModel

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_pagination_params,
    get_paper_adapter,
    get_user_account,
    require_permission,
)
from ..schemas import (
    ClosePositionResponse,
    PaginatedResponse,
    PaginationParams,
    PositionResponse,
)
from ..services.position_service import PositionService

logger = logging.getLogger("trading_engine.routes.positions")

router = APIRouter(prefix="/api/v1/positions", tags=["Positions"])


@router.get(
    "/",
    response_model=PaginatedResponse[PositionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Positions",
    description="List open and historical positions for the authenticated user's account.",
)
async def list_positions(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    _perm: Annotated[Any, Depends(require_permission(Permission.POSITION_READ))],
    symbol: str | None = Query(None, description="Filter by instrument symbol"),
    is_open: bool | None = Query(None, description="Filter by open/closed status"),
) -> PaginatedResponse[PositionResponse]:
    """List positions with pagination and filtering."""
    service = PositionService(adapter=adapter, session=session, account=account)
    return await service.list_positions(
        pagination=pagination,
        symbol=symbol,
        is_open=is_open,
    )


@router.get(
    "/{position_id}",
    response_model=PositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Position",
    description="Retrieve a single position by ID with ownership verification.",
)
async def get_position(
    position_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.POSITION_READ))],
) -> PositionResponse:
    """Get single position by ID."""
    service = PositionService(adapter=adapter, session=session, account=account)
    return await service.get_position(position_id)


@router.post(
    "/{position_id}/close",
    response_model=ClosePositionResponse,
    status_code=status.HTTP_200_OK,
    summary="Close Position",
    description="Close an open paper trading position.",
)
async def close_position(
    position_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.POSITION_CLOSE))],
) -> ClosePositionResponse:
    """Close an open position."""
    service = PositionService(adapter=adapter, session=session, account=account)
    return await service.close_position(position_id)
