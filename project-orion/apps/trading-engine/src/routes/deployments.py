"""Strategy Deployment Pipeline & Paper Incubator REST API endpoints.

Exposes institutional governance controls to promote, monitor, validate,
and review quantitative trading strategies in paper incubation.

EPIC-025 strictly operates in Paper Trading ($0.00 Capital at risk).
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission

from ..dependencies import (
    TenantContext,
    get_db_session,
    require_permission,
)
from ..schemas_deployment import (
    DeploymentDetailResponse,
    DeploymentListResponse,
    DeploymentSummaryResponse,
    PromoteFromExperimentRequest,
    PromoteFromOptimizationRequest,
    QualityGateReportSchema,
    TransitionDeploymentRequest,
)
from ..services.deployment_service import DeploymentPipelineService
from ..services.entitlement_service import EntitlementService

logger = logging.getLogger("trading_engine.routes.deployments")

router = APIRouter(prefix="/api/v1/deployments", tags=["Deployment Pipeline"])


def get_deployment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DeploymentPipelineService:
    """Dependency provider for DeploymentPipelineService."""
    entitlements = EntitlementService(session=session)
    return DeploymentPipelineService(
        session=session,
        entitlement_service=entitlements,
    )


def _resolve_org_id(tenant_context: TenantContext) -> str:
    """Resolve active tenant organization ID or sandbox fallback."""
    if tenant_context.organization_id:
        return tenant_context.organization_id
    return f"personal-{tenant_context.user_id}"


def _model_to_summary(d: Any) -> DeploymentSummaryResponse:
    """Map StrategyDeploymentModel to DeploymentSummaryResponse."""
    return DeploymentSummaryResponse(
        id=d.id,
        organization_id=d.organization_id,
        created_by=d.created_by,
        strategy_id=d.strategy_id,
        strategy_version=d.strategy_version,
        symbol=d.symbol,
        timeframe=d.timeframe,
        status=d.status,
        initial_capital=d.initial_capital,
        promotion_verdict=d.promotion_verdict,
        created_at=d.created_at,
        updated_at=d.updated_at,
        started_at=d.started_at,
        completed_at=d.completed_at,
        source_optimization_id=d.source_optimization_id,
        source_experiment_id=d.source_experiment_id,
    )


def _model_to_detail(d: Any) -> DeploymentDetailResponse:
    """Map StrategyDeploymentModel to DeploymentDetailResponse."""
    return DeploymentDetailResponse(
        id=d.id,
        organization_id=d.organization_id,
        created_by=d.created_by,
        strategy_id=d.strategy_id,
        strategy_version=d.strategy_version,
        symbol=d.symbol,
        timeframe=d.timeframe,
        status=d.status,
        parameters=d.parameters,
        evidence_chain=d.evidence_chain,
        initial_capital=d.initial_capital,
        quality_gate_policy=d.quality_gate_policy,
        quality_gate_results=d.quality_gate_results,
        incubation_config=d.incubation_config,
        incubation_metrics=d.incubation_metrics,
        benchmark_comparison=d.benchmark_comparison,
        backtest_benchmark=d.backtest_benchmark,
        promotion_verdict=d.promotion_verdict,
        transition_history=d.transition_history or [],
        started_at=d.started_at,
        completed_at=d.completed_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
        error_message=d.error_message,
        warnings=d.warnings,
        source_optimization_id=d.source_optimization_id,
        source_experiment_id=d.source_experiment_id,
    )


@router.post(
    "/promote/optimization",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Promote Optimization Candidate",
    description="Promote an optimization candidate into paper incubation with quality gate evaluation. Requires DEPLOYMENT_EXECUTE.",
)
async def promote_optimization_candidate(
    request: PromoteFromOptimizationRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_EXECUTE))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
) -> DeploymentDetailResponse:
    """Promote an optimization job candidate into paper deployment."""
    org_id = _resolve_org_id(tenant_context)
    deployment = await service.promote_from_optimization(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        request=request,
    )
    return _model_to_detail(deployment)


@router.post(
    "/promote/experiment",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Promote Research Experiment",
    description="Promote a completed backtest experiment into paper incubation. Requires DEPLOYMENT_EXECUTE.",
)
async def promote_research_experiment(
    request: PromoteFromExperimentRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_EXECUTE))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
) -> DeploymentDetailResponse:
    """Promote a research backtest experiment into paper deployment."""
    org_id = _resolve_org_id(tenant_context)
    deployment = await service.promote_from_experiment(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        request=request,
    )
    return _model_to_detail(deployment)


@router.get(
    "",
    response_model=DeploymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Strategy Deployments",
    description="List deployments for the organization with pagination and status filters. Requires DEPLOYMENT_READ.",
)
async def list_deployments(
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_READ))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status")] = None,
    strategy_filter: Annotated[str | None, Query(alias="strategy_id", description="Filter by strategy ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DeploymentListResponse:
    """List deployments with filtering and pagination."""
    org_id = _resolve_org_id(tenant_context)
    items, total = await service.list_deployments(
        organization_id=org_id,
        status_filter=status_filter,
        strategy_filter=strategy_filter,
        limit=limit,
        offset=offset,
    )
    return DeploymentListResponse(
        items=[_model_to_summary(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{deployment_id}",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Strategy Deployment Detail",
    description="Retrieve comprehensive deployment detail including quality gates, incubation metrics, and evidence chain. Requires DEPLOYMENT_READ.",
)
async def get_deployment(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_READ))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
) -> DeploymentDetailResponse:
    """Get single deployment by ID."""
    org_id = _resolve_org_id(tenant_context)
    deployment = await service.get_deployment(org_id, deployment_id)
    return _model_to_detail(deployment)


@router.post(
    "/{deployment_id}/pause",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause Incubating Deployment",
    description="Pause an active incubating deployment. Requires DEPLOYMENT_CANCEL.",
)
async def pause_deployment(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_CANCEL))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    request: TransitionDeploymentRequest | None = None,
) -> DeploymentDetailResponse:
    """Pause an incubating strategy deployment."""
    org_id = _resolve_org_id(tenant_context)
    reason = request.reason if request else "Paused by operator"
    deployment = await service.pause_deployment(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        deployment_id=deployment_id,
        reason=reason,
    )
    return _model_to_detail(deployment)


@router.post(
    "/{deployment_id}/resume",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume Paused Deployment",
    description="Resume a paused strategy deployment back to INCUBATING. Requires DEPLOYMENT_EXECUTE.",
)
async def resume_deployment(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_EXECUTE))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    request: TransitionDeploymentRequest | None = None,
) -> DeploymentDetailResponse:
    """Resume a paused deployment."""
    org_id = _resolve_org_id(tenant_context)
    reason = request.reason if request else "Resumed by operator"
    deployment = await service.resume_deployment(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        deployment_id=deployment_id,
        reason=reason,
    )
    return _model_to_detail(deployment)


@router.post(
    "/{deployment_id}/cancel",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Strategy Deployment",
    description="Cancel an active deployment and mark terminal state. Requires DEPLOYMENT_CANCEL.",
)
async def cancel_deployment(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_CANCEL))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    request: TransitionDeploymentRequest | None = None,
) -> DeploymentDetailResponse:
    """Cancel a strategy deployment."""
    org_id = _resolve_org_id(tenant_context)
    reason = request.reason if request else "Cancelled by operator"
    deployment = await service.cancel_deployment(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        deployment_id=deployment_id,
        reason=reason,
    )
    return _model_to_detail(deployment)


@router.post(
    "/{deployment_id}/validate",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Incubation & Validate",
    description="Evaluate paper incubation metrics against benchmark and policy. Transitions to PAPER_VALIDATED or INCUBATION_FAILED. Requires DEPLOYMENT_PROMOTE.",
)
async def validate_deployment(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_PROMOTE))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    request: TransitionDeploymentRequest | None = None,
) -> DeploymentDetailResponse:
    """Evaluate incubation and transition to PAPER_VALIDATED or INCUBATION_FAILED."""
    org_id = _resolve_org_id(tenant_context)
    reason = request.reason if request else "Incubation evaluation triggered"
    deployment = await service.validate_deployment(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        deployment_id=deployment_id,
        reason=reason,
    )
    return _model_to_detail(deployment)


@router.post(
    "/{deployment_id}/promote-candidate",
    response_model=DeploymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Promotion Candidate",
    description="Advance a PAPER_VALIDATED strategy to institutional PROMOTION_CANDIDATE review. Requires DEPLOYMENT_PROMOTE.",
)
async def promote_to_candidate(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_PROMOTE))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
    request: TransitionDeploymentRequest | None = None,
) -> DeploymentDetailResponse:
    """Mark validated deployment as PROMOTION_CANDIDATE. Terminal pipeline state."""
    org_id = _resolve_org_id(tenant_context)
    reason = request.reason if request else "Promoted to candidate review"
    deployment = await service.promote_to_candidate(
        organization_id=org_id,
        user_id=tenant_context.user_id,
        role=tenant_context.role,
        deployment_id=deployment_id,
        reason=reason,
    )
    return _model_to_detail(deployment)


@router.get(
    "/{deployment_id}/gates",
    response_model=QualityGateReportSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Quality Gate Report",
    description="Retrieve 5-gate quality evaluation details. Requires DEPLOYMENT_READ.",
)
async def get_quality_gates(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_READ))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
) -> QualityGateReportSchema:
    """Get quality gate results for deployment."""
    org_id = _resolve_org_id(tenant_context)
    deployment = await service.get_deployment(org_id, deployment_id)
    gates = deployment.quality_gate_results or {}
    return QualityGateReportSchema(
        all_passed=bool(gates.get("all_passed", False)),
        summary_verdict=str(gates.get("summary_verdict", "INSUFFICIENT_DATA")),
        gate_results=gates.get("gate_results", []),
        evaluated_at=str(gates.get("evaluated_at", "")),
    )


@router.get(
    "/{deployment_id}/metrics",
    status_code=status.HTTP_200_OK,
    summary="Get Incubation Metrics & Benchmark",
    description="Retrieve paper incubation metrics and benchmark fidelity comparisons. Requires DEPLOYMENT_READ.",
)
async def get_deployment_metrics(
    deployment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.DEPLOYMENT_READ))],
    service: Annotated[DeploymentPipelineService, Depends(get_deployment_service)],
) -> dict[str, Any]:
    """Get incubation metrics and benchmark comparison."""
    org_id = _resolve_org_id(tenant_context)
    deployment = await service.get_deployment(org_id, deployment_id)
    return {
        "deployment_id": deployment.id,
        "status": deployment.status,
        "incubation_metrics": deployment.incubation_metrics,
        "benchmark_comparison": deployment.benchmark_comparison,
        "backtest_benchmark": deployment.backtest_benchmark,
    }
