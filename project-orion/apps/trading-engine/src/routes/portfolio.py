"""Portfolio analytics and performance endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import AccountModel

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_paper_adapter,
    get_user_account,
    require_permission,
)
from ..schemas import (
    EquityCurveResponse,
    ExposureResponse,
    PnLBreakdownResponse,
    PortfolioOverviewResponse,
)
from ..services.portfolio_service import PortfolioService

logger = logging.getLogger("trading_engine.routes.portfolio")

router = APIRouter(prefix="/api/v1/portfolio", tags=["Portfolio"])


@router.get(
    "/",
    response_model=PortfolioOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Portfolio Overview",
    description="Returns consolidated balance, equity, margin, and exposure metrics.",
)
async def get_portfolio_overview(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> PortfolioOverviewResponse:
    """Get portfolio overview."""
    service = PortfolioService(adapter=adapter, session=session, account=account)
    return await service.get_overview()


@router.get(
    "/equity",
    response_model=EquityCurveResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Equity Curve",
    description="Returns current equity, peak equity, and drawdown metrics.",
)
async def get_equity_curve(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> EquityCurveResponse:
    """Get equity curve summary."""
    service = PortfolioService(adapter=adapter, session=session, account=account)
    return await service.get_equity()


@router.get(
    "/pnl",
    response_model=PnLBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get PnL Breakdown",
    description="Returns realized, unrealized, gross profit/loss, commission, and swap breakdown.",
)
async def get_pnl_breakdown(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> PnLBreakdownResponse:
    """Get PnL breakdown."""
    service = PortfolioService(adapter=adapter, session=session, account=account)
    return await service.get_pnl()


@router.get(
    "/exposure",
    response_model=ExposureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Exposure",
    description="Returns net, gross, long, short, and per-currency exposure breakdowns.",
)
async def get_exposure(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> ExposureResponse:
    """Get exposure breakdown."""
    service = PortfolioService(adapter=adapter, session=session, account=account)
    return await service.get_exposure()
