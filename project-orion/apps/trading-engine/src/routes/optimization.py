"""Quantitative strategy optimization and walk-forward research REST API endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission

from ..dependencies import TenantContext, get_db_session, require_permission
from ..schemas_optimization import (
    OptimizationJobDetailResponse,
    OptimizationJobSummaryResponse,
    OptimizationRunRequest,
    RegimeBreakdownResponse,
    SensitivityHeatmapResponse,
    StrategyDefaultSpaceResponse,
    WalkForwardAnalysisResponse,
    WalkForwardRunRequest,
)
from ..services.optimization_service import OptimizationService

logger = logging.getLogger("trading_engine.routes.optimization")

router = APIRouter(prefix="/api/v1/optimization", tags=["Optimization"])


def get_optimization_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OptimizationService:
    """Dependency provider for OptimizationService."""
    return OptimizationService(session=session)


def _resolve_org_id(tenant_context: TenantContext) -> str:
    """Resolve active tenant organization ID or sandbox fallback."""
    if tenant_context.organization_id:
        return tenant_context.organization_id
    return f"personal-{tenant_context.user_id}"


@router.get(
    "/spaces/{strategy_id}",
    response_model=StrategyDefaultSpaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Default Parameter Space",
    description="Retrieve canonical parameter bounds and default search grid for a registered strategy. Requires OPTIMIZATION_READ.",
)
async def get_default_space(
    strategy_id: str,
    _perm: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> StrategyDefaultSpaceResponse:
    """Get default parameter ranges and bounds for an archetype."""
    return service.get_default_space(strategy_id)


@router.post(
    "/run",
    response_model=OptimizationJobDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch Parameter Optimization Sweep",
    description="Run a deterministic Grid Search or Random Search sweep over a defined parameter space. Requires OPTIMIZATION_EXECUTE.",
)
async def run_optimization(
    request: OptimizationRunRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_EXECUTE))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> OptimizationJobDetailResponse:
    """Launch and execute an optimization sweep."""
    org_id = _resolve_org_id(tenant_context)
    return await service.run_optimization(
        request=request,
        organization_id=org_id,
        user_id=tenant_context.user_id,
    )


@router.post(
    "/walk-forward",
    response_model=OptimizationJobDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Launch Walk-Forward Analysis",
    description="Execute chronological multi-window Walk-Forward Analysis (WFA) with strict IS/OOS segregation. Requires OPTIMIZATION_EXECUTE.",
)
async def run_walk_forward(
    request: WalkForwardRunRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_EXECUTE))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> OptimizationJobDetailResponse:
    """Launch and execute a Walk-Forward Analysis study."""
    org_id = _resolve_org_id(tenant_context)
    return await service.run_walk_forward(
        request=request,
        organization_id=org_id,
        user_id=tenant_context.user_id,
    )


@router.get(
    "/jobs",
    response_model=list[OptimizationJobSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Optimization Jobs",
    description="List historical optimization and walk-forward studies for the tenant. Requires OPTIMIZATION_READ.",
)
async def list_jobs(
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
    strategy_id: str | None = Query(default=None, description="Filter by strategy archetype"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[OptimizationJobSummaryResponse]:
    """List tenant optimization studies."""
    org_id = _resolve_org_id(tenant_context)
    return await service.list_jobs(
        organization_id=org_id,
        strategy_id=strategy_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=OptimizationJobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Optimization Job Details",
    description="Retrieve full details, candidate leaderboard, and metrics for an optimization study. Requires OPTIMIZATION_READ.",
)
async def get_job(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> OptimizationJobDetailResponse:
    """Get single optimization study."""
    org_id = _resolve_org_id(tenant_context)
    return await service.get_job(job_id=job_id, organization_id=org_id)


@router.post(
    "/jobs/{job_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel Optimization Job",
    description="Cooperatively cancel an in-progress optimization or walk-forward job. Requires OPTIMIZATION_CANCEL.",
)
async def cancel_job(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_CANCEL))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> dict[str, Any]:
    """Cancel running optimization."""
    org_id = _resolve_org_id(tenant_context)
    success = await service.cancel_job(job_id=job_id, organization_id=org_id)
    return {"job_id": job_id, "cancelled": success}


@router.get(
    "/jobs/{job_id}/heatmap",
    response_model=SensitivityHeatmapResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get 2D Parameter Heatmap",
    description="Retrieve 2D sensitivity matrix across the primary two parameters. Requires OPTIMIZATION_READ.",
)
async def get_heatmap(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> SensitivityHeatmapResponse | None:
    """Get 2D parameter sensitivity surface heatmap."""
    org_id = _resolve_org_id(tenant_context)
    job = await service.get_job(job_id=job_id, organization_id=org_id)
    return job.heatmap


@router.get(
    "/jobs/{job_id}/walk-forward",
    response_model=WalkForwardAnalysisResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get Walk-Forward Results",
    description="Retrieve Walk-Forward Analysis window results, WFE score, and OOS forward curve. Requires OPTIMIZATION_READ.",
)
async def get_walk_forward(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> WalkForwardAnalysisResponse | None:
    """Get walk-forward breakdown."""
    org_id = _resolve_org_id(tenant_context)
    job = await service.get_job(job_id=job_id, organization_id=org_id)
    return job.walk_forward_result


@router.get(
    "/jobs/{job_id}/regimes",
    response_model=list[RegimeBreakdownResponse] | None,
    status_code=status.HTTP_200_OK,
    summary="Get Market Regime Breakdown",
    description="Retrieve strategy performance partitioned into market regime segments. Requires OPTIMIZATION_READ.",
)
async def get_regimes(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_READ))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
) -> list[RegimeBreakdownResponse] | None:
    """Get market regime breakdown."""
    org_id = _resolve_org_id(tenant_context)
    job = await service.get_job(job_id=job_id, organization_id=org_id)
    return job.regime_breakdowns


@router.get(
    "/jobs/{job_id}/export",
    status_code=status.HTTP_200_OK,
    summary="Export Optimization Results",
    description="Export evaluated candidate leaderboard as CSV or JSON format. Requires OPTIMIZATION_EXPORT.",
)
async def export_job(
    job_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.OPTIMIZATION_EXPORT))],
    service: Annotated[OptimizationService, Depends(get_optimization_service)],
    format_type: str = Query(default="json", alias="format", description="'json' or 'csv'"),
) -> Response:
    """Export optimization results."""
    org_id = _resolve_org_id(tenant_context)
    content = await service.export_job(job_id=job_id, organization_id=org_id, format_type=format_type)

    if format_type.lower() == "csv":
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={job_id}_candidates.csv"},
        )

    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={job_id}.json"},
    )
