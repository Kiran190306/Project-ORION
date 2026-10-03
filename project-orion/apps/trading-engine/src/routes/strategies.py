"""Strategy management endpoints for listing, detail, and configuration.

Provides the static strategy catalogue plus per-account configuration
through the StrategyConfigModel database entity.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.domain.strategy.registry import StrategyRegistry
from libraries.infrastructure.persistence.models import (
    AccountModel,
    StrategyConfigModel,
    StrategyDeploymentModel,
)

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_user_account,
    require_permission,
)
from ..schemas import (
    AccountStrategyConfigResponse,
    StrategyConfigSchemaResponse,
    StrategyDetailResponse,
    StrategyInfo,
    StrategyListResponse,
    UpdateAccountStrategyRequest,
)

logger = logging.getLogger("trading_engine.routes.strategies")

router = APIRouter(prefix="/api/v1/strategies", tags=["Strategies"])

# ─── Strategy Catalogue ─────────────────────────────────────────────────────


def _build_strategy_catalogue() -> list[dict[str, Any]]:
    """Build the catalogue of active strategies directly from StrategyRegistry.

    Guarantees 100% parity between the exposed API catalogue and executable strategies.
    Only strategies that can actually be resolved and executed by StrategyRegistry
    are included.
    """
    catalogue: list[dict[str, Any]] = []
    for entry in StrategyRegistry.list_strategies():
        params: dict[str, Any] = {}
        for p in entry.parameters:
            p_def: dict[str, Any] = {
                "type": p.param_type,
                "default": p.default,
            }
            if p.min_value is not None:
                p_def["min"] = p.min_value
            if p.max_value is not None:
                p_def["max"] = p.max_value
            if p.options is not None:
                p_def["options"] = list(p.options)
            p_def["description"] = p.description
            params[p.name] = p_def

        catalogue.append(
            {
                "id": entry.strategy_id,
                "name": entry.name,
                "type": entry.strategy_id,
                "description": entry.description,
                "timeframes": list(entry.supported_timeframes),
                "symbols": list(entry.supported_instruments),
                "parameters": params,
            }
        )
    return catalogue


_STRATEGY_CATALOGUE: list[dict[str, Any]] = _build_strategy_catalogue()


def _find_strategy(strategy_id: str) -> dict[str, Any] | None:
    """Lookup a strategy from the catalogue by ID."""
    for s in _build_strategy_catalogue():
        if s["id"] == strategy_id:
            return s
    return None


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=StrategyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Available Strategies",
    description="Returns metadata for all available trading strategies.",
)
async def list_strategies(
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_READ))],
) -> StrategyListResponse:
    """List all available trading strategies with their metadata."""
    try:
        strategies = [
            StrategyInfo(
                id=s["id"],
                name=s["name"],
                type=s["type"],
                description=s["description"],
                timeframes=s["timeframes"],
                symbols=s["symbols"],
                is_active=True,
            )
            for s in _build_strategy_catalogue()
        ]

        return StrategyListResponse(
            strategies=strategies,
            total=len(strategies),
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to list strategies: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategy list",
        ) from exc


@router.get(
    "/{strategy_id}",
    response_model=StrategyDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Strategy Details",
    description="Returns detailed metadata and parameter definitions for a single strategy.",
)
async def get_strategy_detail(
    strategy_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_READ))],
) -> StrategyDetailResponse:
    """Get detailed metadata for a specific strategy."""
    strategy = _find_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )

    return StrategyDetailResponse(
        id=strategy["id"],
        name=strategy["name"],
        type=strategy["type"],
        description=strategy["description"],
        timeframes=strategy["timeframes"],
        symbols=strategy["symbols"],
        parameters=strategy.get("parameters", {}),
        is_active=True,
    )


@router.get(
    "/{strategy_id}/config-schema",
    response_model=StrategyConfigSchemaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Strategy Config Schema",
    description="Returns the JSON Schema defining configurable parameters for the strategy.",
)
async def get_strategy_config_schema(
    strategy_id: str,
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_READ))],
) -> StrategyConfigSchemaResponse:
    """Get the configurable parameter schema for a strategy."""
    strategy = _find_strategy(strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{strategy_id}' not found",
        )

    return StrategyConfigSchemaResponse(
        strategy_id=strategy["id"],
        name=strategy["name"],
        schema_definition=strategy.get("parameters", {}),
    )


async def _get_deployment_status(
    session: AsyncSession, org_id: str | None, strategy_id: str
) -> str | None:
    """Helper to query the latest deployment lifecycle status for a strategy."""
    if not org_id:
        return None
    stmt = (
        select(StrategyDeploymentModel.status)
        .where(
            StrategyDeploymentModel.organization_id == org_id,
            StrategyDeploymentModel.strategy_id == strategy_id,
        )
        .order_by(StrategyDeploymentModel.created_at.desc())
        .limit(1)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


# ─── Multi-Strategy & Per-Account Configuration ──────────────────────────────


@router.get(
    "/account/configs",
    response_model=list[AccountStrategyConfigResponse],
    status_code=status.HTTP_200_OK,
    summary="List Account Strategy Configurations",
    description="Returns all active and configured strategy configurations for the account/organization.",
)
async def list_account_strategy_configs(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_READ))],
) -> list[AccountStrategyConfigResponse]:
    """Get all configured strategies for the user's account and organization."""
    query = select(StrategyConfigModel)
    if account.organization_id is not None:
        query = query.where(
            (StrategyConfigModel.organization_id == account.organization_id)
            | (StrategyConfigModel.account_id == account.id)
        )
    else:
        query = query.where(
            (StrategyConfigModel.account_id == account.id)
            | (StrategyConfigModel.organization_id.is_(None))
        )
    result = await session.execute(
        query.order_by(
            StrategyConfigModel.is_active.desc(),
            StrategyConfigModel.updated_at.desc(),
        )
    )
    configs = result.scalars().all()

    responses: list[AccountStrategyConfigResponse] = []
    for cfg in configs:
        prefix = f"{account.id}_"
        raw_strat_id = cfg.id[len(prefix):] if cfg.id.startswith(prefix) else cfg.id
        strat_info = _find_strategy(raw_strat_id)
        dep_status = await _get_deployment_status(
            session, account.organization_id, raw_strat_id
        )
        responses.append(
            AccountStrategyConfigResponse(
                account_id=account.id,
                strategy_id=raw_strat_id,
                name=cfg.name or (strat_info["name"] if strat_info else raw_strat_id),
                timeframe=cfg.parameters.get("timeframe", "M15") if cfg.parameters else "M15",
                symbols=cfg.symbols or [],
                parameters=cfg.parameters or {},
                is_active=cfg.is_active,
                deployment_status=dep_status,
                updated_at=cfg.updated_at or datetime.now(timezone.utc),
            )
        )
    return responses


@router.post(
    "/account/configs",
    response_model=AccountStrategyConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or Activate Account Strategy Configuration",
    description="Configures and activates a strategy for multi-strategy execution without deactivating existing active strategies.",
)
async def create_account_strategy_config(
    body: UpdateAccountStrategyRequest,
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_CONFIGURE))],
) -> AccountStrategyConfigResponse:
    """Add or update a strategy in the multi-strategy portfolio."""
    strategy = _find_strategy(body.strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{body.strategy_id}' not found in catalogue",
        )

    config_id = f"{account.id}_{body.strategy_id}"
    result = await session.execute(
        select(StrategyConfigModel).where(StrategyConfigModel.id == config_id)
    )
    config = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if config is None:
        config = StrategyConfigModel(
            id=config_id,
            organization_id=account.organization_id,
            account_id=account.id,
            name=strategy["name"],
            version="1.0",
            is_active=body.is_active,
            symbols=body.symbols or strategy["symbols"],
            parameters={"timeframe": body.timeframe, **body.parameters},
            description=strategy["description"],
        )
        session.add(config)
    else:
        config.organization_id = account.organization_id
        config.account_id = account.id
        config.is_active = body.is_active
        config.symbols = body.symbols or strategy["symbols"]
        config.parameters = {"timeframe": body.timeframe, **body.parameters}

    await session.flush()
    dep_status = await _get_deployment_status(
        session, account.organization_id, body.strategy_id
    )
    return AccountStrategyConfigResponse(
        account_id=account.id,
        strategy_id=body.strategy_id,
        name=strategy["name"],
        timeframe=body.timeframe,
        symbols=config.symbols or [],
        parameters=config.parameters or {},
        is_active=config.is_active,
        deployment_status=dep_status,
        updated_at=now,
    )


@router.delete(
    "/account/configs/{strategy_id}",
    response_model=AccountStrategyConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate Strategy Configuration",
    description="Deactivates a specific strategy configuration from active execution.",
)
async def deactivate_account_strategy_config(
    strategy_id: str,
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_CONFIGURE))],
) -> AccountStrategyConfigResponse:
    """Deactivate an active strategy in the portfolio."""
    config_id = f"{account.id}_{strategy_id}"
    result = await session.execute(
        select(StrategyConfigModel).where(StrategyConfigModel.id == config_id)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration for strategy '{strategy_id}' not found",
        )
    config.is_active = False
    await session.flush()
    dep_status = await _get_deployment_status(
        session, account.organization_id, strategy_id
    )
    return AccountStrategyConfigResponse(
        account_id=account.id,
        strategy_id=strategy_id,
        name=config.name,
        timeframe=config.parameters.get("timeframe", "M15") if config.parameters else "M15",
        symbols=config.symbols or [],
        parameters=config.parameters or {},
        is_active=False,
        deployment_status=dep_status,
        updated_at=config.updated_at or datetime.now(timezone.utc),
    )


@router.get(
    "/account/config",
    response_model=AccountStrategyConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Account Strategy Configuration",
    description="Returns the currently active strategy configuration for the authenticated user's account.",
)
async def get_account_strategy_config(
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_READ))],
) -> AccountStrategyConfigResponse:
    """Get the active strategy configuration for the user's account."""
    query = select(StrategyConfigModel).where(StrategyConfigModel.is_active == True)
    if account.organization_id is not None:
        query = query.where(
            (StrategyConfigModel.organization_id == account.organization_id)
            | (StrategyConfigModel.account_id == account.id)
        )
    else:
        query = query.where(
            (StrategyConfigModel.account_id == account.id)
            | (StrategyConfigModel.organization_id.is_(None))
        )
    result = await session.execute(query.limit(1))
    config = result.scalar_one_or_none()

    if config is None:
        # Return a sensible default when no strategy is configured
        return AccountStrategyConfigResponse(
            account_id=account.id,
            strategy_id="trend_following",
            timeframe="M15",
            symbols=["EUR/USD", "GBP/USD", "USD/JPY"],
            parameters={},
            is_active=False,
            updated_at=datetime.now(timezone.utc),
        )

    return AccountStrategyConfigResponse(
        account_id=account.id,
        strategy_id=config.id,
        timeframe=config.parameters.get("timeframe", "M15") if config.parameters else "M15",
        symbols=config.symbols or [],
        parameters=config.parameters or {},
        is_active=config.is_active,
        updated_at=config.updated_at or datetime.now(timezone.utc),
    )


@router.put(
    "/account/config",
    response_model=AccountStrategyConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Account Strategy Configuration",
    description="Updates the active strategy configuration for the authenticated user's account.",
)
async def update_account_strategy_config(
    body: UpdateAccountStrategyRequest,
    account: Annotated[AccountModel, Depends(get_user_account)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_CONFIGURE))],
) -> AccountStrategyConfigResponse:
    """Update the strategy configuration for the user's account."""
    # Validate that the strategy exists in catalogue
    strategy = _find_strategy(body.strategy_id)
    if strategy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy '{body.strategy_id}' not found in catalogue",
        )

    # Deactivate only active strategy configs for this account/organization
    deact_query = select(StrategyConfigModel).where(StrategyConfigModel.is_active == True)
    if account.organization_id is not None:
        deact_query = deact_query.where(
            (StrategyConfigModel.organization_id == account.organization_id)
            | (StrategyConfigModel.account_id == account.id)
        )
    else:
        deact_query = deact_query.where(StrategyConfigModel.account_id == account.id)
    result = await session.execute(deact_query)
    for existing in result.scalars().all():
        existing.is_active = False

    # Upsert strategy config
    config_id = f"{account.id}_{body.strategy_id}"
    result = await session.execute(
        select(StrategyConfigModel).where(StrategyConfigModel.id == config_id)
    )
    config = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if config is None:
        config = StrategyConfigModel(
            id=config_id,
            organization_id=account.organization_id,
            account_id=account.id,
            name=strategy["name"],
            version="1.0",
            is_active=body.is_active,
            symbols=body.symbols or strategy["symbols"],
            parameters={
                "timeframe": body.timeframe,
                **body.parameters,
            },
            description=strategy["description"],
        )
        session.add(config)
    else:
        config.organization_id = account.organization_id
        config.account_id = account.id
        config.is_active = body.is_active
        config.symbols = body.symbols or strategy["symbols"]
        config.parameters = {
            "timeframe": body.timeframe,
            **body.parameters,
        }

    await session.flush()

    return AccountStrategyConfigResponse(
        account_id=account.id,
        strategy_id=body.strategy_id,
        timeframe=body.timeframe,
        symbols=config.symbols or [],
        parameters=config.parameters or {},
        is_active=config.is_active,
        updated_at=now,
    )
