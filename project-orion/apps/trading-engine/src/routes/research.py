"""Institutional Strategy Lab and Backtesting Research API routes."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from libraries.domain.organization.permissions import Permission
from libraries.domain.strategy.registry import UnknownStrategyError
from libraries.domain.subscription.exceptions import (
    DailyResearchQuotaExceededError,
    ResearchHistoryLimitExceededError,
)

from ..dependencies import (
    TenantContext,
    get_research_service,
    require_permission,
)
from ..schemas_research import (
    CompareExperimentsRequest,
    CreateExperimentRequest,
    ExperimentComparisonResponse,
    ExperimentDetailResponse,
    ExperimentEquityResponse,
    ExperimentSummaryResponse,
    ExperimentTradesResponse,
    StrategyCatalogueItemResponse,
)
from ..services.research_service import ResearchService

logger = logging.getLogger("trading_engine.routes.research")

router = APIRouter(prefix="/api/v1/research", tags=["Research"])


def _resolve_org_id(tenant_context: TenantContext) -> str:
    """Resolve active tenant organization ID or sandbox fallback."""
    if tenant_context.organization_id:
        return tenant_context.organization_id
    return f"personal-{tenant_context.user_id}"


@router.get(
    "/strategies",
    response_model=list[StrategyCatalogueItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered Strategy Catalogue",
    description="Returns all registered strategy archetypes, parameter bounds, and supported instruments/timeframes.",
)
async def list_strategies(
    _perm: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> list[StrategyCatalogueItemResponse]:
    """List registered research strategies."""
    items = await research_service.list_available_strategies()
    return [StrategyCatalogueItemResponse(**item) for item in items]


@router.get(
    "/strategies/{strategy_id}",
    response_model=StrategyCatalogueItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Registered Strategy Specification",
    description="Returns detailed parameters, constraints, and metadata for a specific strategy archetype.",
)
async def get_strategy(
    strategy_id: str,
    _perm: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> StrategyCatalogueItemResponse:
    """Get strategy archetype detail."""
    try:
        detail = await research_service.get_strategy_detail(strategy_id)
        return StrategyCatalogueItemResponse(**detail)
    except (KeyError, UnknownStrategyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/experiments",
    response_model=ExperimentSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and Run Deterministic Research Experiment",
    description="Initiates a deterministic backtest simulation, enforcing quota, leakage guard, and risk accounting.",
)
async def create_experiment(
    request: CreateExperimentRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_EXECUTE))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentSummaryResponse:
    """Execute a backtest simulation and return summary results."""
    org_id = _resolve_org_id(tenant_context)
    try:
        model = await research_service.create_and_run_experiment(
            organization_id=org_id,
            user_id=tenant_context.user_id,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=Decimal(str(request.initial_capital)),
            parameters=request.parameters,
            spread_pips=Decimal(str(request.spread_pips)),
            adverse_slippage_pips=Decimal(str(request.adverse_slippage_pips)),
            commission_per_lot=Decimal(str(request.commission_per_lot)),
        )
        return ExperimentSummaryResponse.model_validate(model)
    except (DailyResearchQuotaExceededError, ResearchHistoryLimitExceededError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=getattr(exc, "message", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Error executing research experiment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment simulation failed: {exc}",
        ) from exc


@router.get(
    "/experiments",
    response_model=list[ExperimentSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Research Experiments",
    description="Returns paginated list of completed and in-progress research experiments for active tenant.",
)
async def list_experiments(
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by experiment status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Max items to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> list[ExperimentSummaryResponse]:
    """List tenant research experiments."""
    org_id = _resolve_org_id(tenant_context)
    items, _ = await research_service.list_experiments(
        organization_id=org_id,
        limit=limit,
        offset=offset,
        status=status_filter,
    )
    return [ExperimentSummaryResponse.model_validate(item) for item in items]


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Research Experiment Detail",
    description="Returns configuration, status, summary metrics, and advisories for a single experiment.",
)
async def get_experiment(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentDetailResponse:
    """Retrieve full experiment detail."""
    org_id = _resolve_org_id(tenant_context)
    try:
        exp = await research_service.get_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
        )
        return ExperimentDetailResponse.model_validate(exp)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/experiments/{experiment_id}/cancel",
    response_model=ExperimentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Research Experiment",
    description="Cancels an in-flight research experiment for active tenant.",
)
async def cancel_experiment(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_CANCEL))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentSummaryResponse:
    """Cancel a running experiment."""
    org_id = _resolve_org_id(tenant_context)
    try:
        exp = await research_service.cancel_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
            user_id=tenant_context.user_id,
        )
        return ExperimentSummaryResponse.model_validate(exp)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/experiments/{experiment_id}/results",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Experiment Results & Metrics",
    description="Returns quantitative performance statistics, drawdown analytics, and overfitting warnings.",
)
async def get_experiment_results(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> dict[str, Any]:
    """Get metrics and warnings for completed experiment."""
    org_id = _resolve_org_id(tenant_context)
    try:
        exp = await research_service.get_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
        )
        return {
            "experiment_id": exp.id,
            "status": exp.status,
            "metrics": exp.metrics or {},
            "warnings": exp.warnings or [],
            "execution_time_seconds": exp.execution_time_seconds,
            "error_message": exp.error_message,
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/experiments/{experiment_id}/equity-curve",
    response_model=ExperimentEquityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Experiment Equity Curve",
    description="Returns downsampled time-series equity points and drawdown trajectory for charting.",
)
async def get_experiment_equity_curve(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentEquityResponse:
    """Get downsampled equity curve points."""
    org_id = _resolve_org_id(tenant_context)
    try:
        exp = await research_service.get_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
        )
        return ExperimentEquityResponse(
            experiment_id=exp.id,
            initial_capital=float(exp.initial_capital),
            points=exp.equity_curve or [],
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/experiments/{experiment_id}/trades",
    response_model=ExperimentTradesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Experiment Trade Journal",
    description="Returns complete ledger of simulated trade executions with entry/exit timestamps, prices, and P&L.",
)
async def get_experiment_trades(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentTradesResponse:
    """Get trade execution ledger."""
    org_id = _resolve_org_id(tenant_context)
    try:
        exp = await research_service.get_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
        )
        trades = exp.trades or []
        return ExperimentTradesResponse(
            experiment_id=exp.id,
            total_trades=len(trades),
            trades=trades,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/experiments/compare",
    response_model=ExperimentComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Completed Experiments",
    description="Compares 2 to 5 experiments side-by-side with normalized performance metrics and percentage equity curves.",
)
async def compare_experiments(
    request: CompareExperimentsRequest,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_READ))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
) -> ExperimentComparisonResponse:
    """Compare multiple experiments."""
    org_id = _resolve_org_id(tenant_context)
    try:
        result = await research_service.compare_experiments(
            experiment_ids=request.experiment_ids,
            organization_id=org_id,
        )
        return ExperimentComparisonResponse(**result)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/experiments/{experiment_id}/export",
    summary="Export Experiment Dataset",
    description="Downloads backtest metrics, simulation parameters, and full trade ledger in CSV or JSON format.",
)
async def export_experiment(
    experiment_id: str,
    tenant_context: Annotated[TenantContext, Depends(require_permission(Permission.RESEARCH_EXPORT))],
    research_service: Annotated[ResearchService, Depends(get_research_service)],
    export_format: Annotated[str, Query(alias="format", pattern="^(csv|json)$")] = "csv",
) -> Response:
    """Export experiment results to file download."""
    org_id = _resolve_org_id(tenant_context)
    try:
        content, media_type, filename = await research_service.export_experiment(
            experiment_id=experiment_id,
            organization_id=org_id,
            export_format=export_format,
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
