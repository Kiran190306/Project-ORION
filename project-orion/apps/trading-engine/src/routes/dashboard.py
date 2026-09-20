"""Consolidated dashboard API endpoint."""

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
    get_worker_coordinator,
    require_permission,
)
from ..schemas import DashboardResponse
from ..services.dashboard_service import DashboardService
from ..workers.coordinator import AutonomousWorkerCoordinator

logger = logging.getLogger("trading_engine.routes.dashboard")

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard",
    description="Returns the consolidated dashboard contract containing account, performance, trading, strategy, risk, worker, and system health blocks.",
)
async def get_dashboard(
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    worker: Annotated[AutonomousWorkerCoordinator | None, Depends(get_worker_coordinator)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> DashboardResponse:
    """Get consolidated trading dashboard."""
    service = DashboardService(
        adapter=adapter,
        session=session,
        account=account,
        worker=worker,
    )
    return await service.get_dashboard()
