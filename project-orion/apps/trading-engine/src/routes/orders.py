"""Order management API endpoints for paper trading."""

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
    CancelOrderResponse,
    CreateOrderRequest,
    OrderResponse,
    PaginatedResponse,
    PaginationParams,
)
from ..services.order_service import OrderService

logger = logging.getLogger("trading_engine.routes.orders")

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Order",
    description="Submit a new paper trading order (market, limit, or stop).",
)
async def create_order(
    request: CreateOrderRequest,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_CREATE))],
) -> OrderResponse:
    """Submit a paper trading order."""
    service = OrderService(adapter=adapter, session=session, account=account)
    return await service.create_order(request)


@router.get(
    "/",
    response_model=PaginatedResponse[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List Orders",
    description="List orders for the authenticated user's account with pagination and filtering.",
)
async def list_orders(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_READ))],
    symbol: str | None = Query(None, description="Filter by instrument symbol"),
    status_filter: str | None = Query(None, alias="status", description="Filter by order status"),
) -> PaginatedResponse[OrderResponse]:
    """List orders with pagination and filtering."""
    service = OrderService(adapter=adapter, session=session, account=account)
    return await service.list_orders(
        pagination=pagination,
        symbol=symbol,
        status_filter=status_filter,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Order",
    description="Retrieve a single order by ID with ownership verification.",
)
async def get_order(
    order_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_READ))],
) -> OrderResponse:
    """Get single order by ID."""
    service = OrderService(adapter=adapter, session=session, account=account)
    return await service.get_order(order_id)


@router.post(
    "/{order_id}/cancel",
    response_model=CancelOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Order",
    description="Cancel a pending paper trading order.",
)
async def cancel_order(
    order_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_CANCEL))],
) -> CancelOrderResponse:
    """Cancel an active paper trading order."""
    service = OrderService(adapter=adapter, session=session, account=account)
    return await service.cancel_order(order_id)
