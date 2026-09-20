"""Worker status and control endpoints.

Protected by JWT authentication — worker controls require superuser.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.domain.subscription.exceptions import WorkerQuotaExceededError

from ..dependencies import (
    TenantContext,
    get_current_active_user,
    get_db_session,
    get_worker_coordinator,
    require_permission,
)
from ..schemas import WorkerMetricsResponse, WorkerStatusResponse
from ..services.entitlement_service import EntitlementService
from ..workers.coordinator import AutonomousWorkerCoordinator
from ..workers.lifecycle import WorkerState

logger = logging.getLogger("trading_engine.routes.worker")

router = APIRouter(prefix="/api/v1/worker", tags=["Worker"])


@router.get(
    "/status",
    response_model=WorkerStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Status",
    description="Returns the current status of the autonomous trading worker. Requires WORKER_READ.",
)
async def get_worker_status(
    worker: Annotated[AutonomousWorkerCoordinator | None, Depends(get_worker_coordinator)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.WORKER_READ))],
) -> WorkerStatusResponse:
    """Get current worker status."""
    if worker is None:
        return WorkerStatusResponse(
            enabled=False,
            state="stopped",
            is_running=False,
            last_cycle_at=None,
            next_cycle_at=None,
            last_error=None,
            uptime_seconds=0,
            updated_at=datetime.now(timezone.utc),
        )

    try:
        return WorkerStatusResponse(
            enabled=worker.enabled,
            state=worker.state.value,
            is_running=worker.state == WorkerState.RUNNING,
            last_cycle_at=worker.last_cycle_at,
            next_cycle_at=None,  # Scheduler doesn't expose next cycle time
            last_error=None,  # Not exposed by coordinator
            uptime_seconds=0.0,  # Not exposed by coordinator
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to get worker status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve worker status",
        ) from exc


@router.get(
    "/metrics",
    response_model=WorkerMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Worker Metrics",
    description="Returns operational metrics for the autonomous trading worker. Requires WORKER_READ.",
)
async def get_worker_metrics(
    worker: Annotated[AutonomousWorkerCoordinator | None, Depends(get_worker_coordinator)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.WORKER_READ))],
) -> WorkerMetricsResponse:
    """Get worker operational metrics."""
    if worker is None:
        return WorkerMetricsResponse(
            cycles_started=0,
            cycles_completed=0,
            cycles_failed=0,
            market_poll_failures=0,
            orders_submitted=0,
            risk_rejections=0,
            execution_failures=0,
            uptime_seconds=0,
            updated_at=datetime.now(timezone.utc),
        )

    try:
        return WorkerMetricsResponse(
            cycles_started=0,  # Not exposed by coordinator
            cycles_completed=worker.cycles_completed,
            cycles_failed=worker.cycles_failed,
            market_poll_failures=0,  # Not exposed by coordinator
            orders_submitted=0,  # Not exposed by coordinator
            risk_rejections=0,  # Not exposed by coordinator
            execution_failures=0,  # Not exposed by coordinator
            uptime_seconds=worker.uptime_seconds or 0.0,
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to get worker metrics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve worker metrics",
        ) from exc


@router.post(
    "/start",
    status_code=status.HTTP_200_OK,
    summary="Start Worker",
    description="Starts the autonomous trading worker if it is currently stopped. Requires WORKER_START.",
)
async def start_worker(
    worker: Annotated[AutonomousWorkerCoordinator | None, Depends(get_worker_coordinator)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.WORKER_START))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    """Start the autonomous worker. Requires WORKER_START permission and valid plan tier."""
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker coordinator is not available",
        )

    # If tenant organization is specified, verify worker entitlement quota
    if tenant_context.organization_id is not None:
        entitlement_svc = EntitlementService(session)
        try:
            await entitlement_svc.check_worker_quota(tenant_context.organization_id)
        except WorkerQuotaExceededError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=exc.message,
            ) from exc

    try:
        await worker.start()
        return {"status": "started", "message": "Worker started successfully"}
    except Exception as exc:
        logger.error("Failed to start worker: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start worker: {exc}",
        ) from exc


@router.post(
    "/stop",
    status_code=status.HTTP_200_OK,
    summary="Stop Worker",
    description="Stops the autonomous trading worker gracefully. Requires WORKER_STOP.",
)
async def stop_worker(
    worker: Annotated[AutonomousWorkerCoordinator | None, Depends(get_worker_coordinator)],
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.WORKER_STOP))],
) -> dict[str, str]:
    """Stop the autonomous worker. Requires WORKER_STOP permission."""
    if worker is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker coordinator is not available",
        )

    try:
        await worker.stop()
        return {"status": "stopped", "message": "Worker stopped successfully"}
    except Exception as exc:
        logger.error("Failed to stop worker: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop worker: {exc}",
        ) from exc
