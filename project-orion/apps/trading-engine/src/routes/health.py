"""Health check endpoints for process liveness and dependency readiness."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from libraries.infrastructure.health import HealthCheckRegistry, HealthStatus

from ..dependencies import get_health_registry
from ..schemas import HealthCheckDetail, HealthResponse, LivenessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Liveness Probe",
    description="Returns 200 if the process is alive and accepting connections.",
)
async def health_live() -> LivenessResponse:
    """Process/application liveness probe only."""
    return LivenessResponse(status="alive")


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Infrastructure Readiness Probe",
    description="Verifies PostgreSQL and Redis connectivity. Returns 503 if any required dependency is unavailable.",
    responses={
        200: {"description": "All infrastructure dependencies are healthy and ready."},
        503: {"description": "One or more infrastructure dependencies are unavailable."},
    },
)
async def health_ready(
    health_registry: Annotated[HealthCheckRegistry, Depends(get_health_registry)],
) -> JSONResponse:
    """Verify required infrastructure dependencies (PostgreSQL + Redis)."""
    results = await health_registry.run_readiness()
    summary = health_registry.get_summary(results)

    check_details = [
        HealthCheckDetail(
            name=r.name,
            status=r.status,
            message=r.message,
            duration_ms=round(r.duration_ms, 2),
            checked_at=r.checked_at,
        )
        for r in results
    ]

    overall_status = summary["status"]
    response_body = HealthResponse(
        status=overall_status,
        checks=check_details,
    )

    # Return 200 only if overall status is healthy. Return 503 if unhealthy or degraded.
    http_status = (
        status.HTTP_200_OK
        if overall_status == HealthStatus.HEALTHY
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        status_code=http_status,
        content=response_body.model_dump(),
    )
