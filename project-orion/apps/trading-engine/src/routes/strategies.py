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
from libraries.infrastructure.persistence.models import (
    AccountModel,
    StrategyConfigModel,
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

# ─── Static Strategy Catalogue ──────────────────────────────────────────────

_STRATEGY_CATALOGUE: list[dict[str, Any]] = [
    {
        "id": "trend_following",
        "name": "Trend Following",
        "type": "trend_following",
        "description": "Follows market trends using moving averages and momentum indicators",
        "timeframes": ["M1", "M5", "M15", "H1", "H4", "D1"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "parameters": {
            "fast_ma_period": {"type": "integer", "default": 10, "min": 2, "max": 50},
            "slow_ma_period": {"type": "integer", "default": 30, "min": 5, "max": 200},
            "rsi_period": {"type": "integer", "default": 14, "min": 5, "max": 50},
            "rsi_overbought": {"type": "float", "default": 70.0, "min": 50.0, "max": 90.0},
            "rsi_oversold": {"type": "float", "default": 30.0, "min": 10.0, "max": 50.0},
        },
    },
    {
        "id": "mean_reversion",
        "name": "Mean Reversion",
        "type": "mean_reversion",
        "description": "Reverts to mean when price deviates significantly from average",
        "timeframes": ["M15", "H1", "H4"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "parameters": {
            "lookback_period": {"type": "integer", "default": 20, "min": 5, "max": 100},
            "std_dev_threshold": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0},
            "mean_type": {"type": "string", "default": "SMA", "options": ["SMA", "EMA", "WMA"]},
        },
    },
    {
        "id": "breakout",
        "name": "Breakout",
        "type": "breakout",
        "description": "Trades breakouts from consolidation patterns",
        "timeframes": ["H1", "H4", "D1"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "parameters": {
            "lookback_bars": {"type": "integer", "default": 20, "min": 5, "max": 100},
            "volume_threshold": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0},
            "atr_multiplier": {"type": "float", "default": 1.5, "min": 0.5, "max": 4.0},
        },
    },
    {
        "id": "reversal",
        "name": "Reversal",
        "type": "reversal",
        "description": "Identifies trend reversals using momentum divergences",
        "timeframes": ["M15", "H1", "H4"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "parameters": {
            "divergence_lookback": {"type": "integer", "default": 14, "min": 5, "max": 50},
            "confirmation_bars": {"type": "integer", "default": 3, "min": 1, "max": 10},
        },
    },
    {
        "id": "scalping",
        "name": "Scalping",
        "type": "scalping",
        "description": "Short-term trades on small price movements",
        "timeframes": ["M1", "M5"],
        "symbols": ["EUR/USD", "GBP/USD"],
        "parameters": {
            "pip_target": {"type": "float", "default": 5.0, "min": 1.0, "max": 20.0},
            "max_hold_minutes": {"type": "integer", "default": 15, "min": 1, "max": 60},
        },
    },
    {
        "id": "swing",
        "name": "Swing",
        "type": "swing",
        "description": "Medium-term trades on multi-day swings",
        "timeframes": ["H4", "D1"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "parameters": {
            "swing_lookback": {"type": "integer", "default": 10, "min": 3, "max": 30},
            "risk_reward_ratio": {"type": "float", "default": 2.0, "min": 1.0, "max": 5.0},
        },
    },
    {
        "id": "momentum",
        "name": "Momentum",
        "type": "momentum",
        "description": "Trades based on momentum continuation patterns",
        "timeframes": ["M5", "M15", "H1"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "parameters": {
            "momentum_period": {"type": "integer", "default": 14, "min": 5, "max": 50},
            "signal_threshold": {"type": "float", "default": 0.5, "min": 0.1, "max": 2.0},
        },
    },
    {
        "id": "carry_trade",
        "name": "Carry Trade",
        "type": "carry_trade",
        "description": "Exploits interest rate differentials between currency pairs",
        "timeframes": ["D1", "W1"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD"],
        "parameters": {
            "min_rate_differential": {"type": "float", "default": 0.5, "min": 0.1, "max": 3.0},
            "max_drawdown_pct": {"type": "float", "default": 5.0, "min": 1.0, "max": 20.0},
        },
    },
    {
        "id": "news_trading",
        "name": "News Trading",
        "type": "news",
        "description": "Trades around economic news events",
        "timeframes": ["M1", "M5"],
        "symbols": ["EUR/USD", "GBP/USD", "USD/JPY"],
        "parameters": {
            "pre_news_minutes": {"type": "integer", "default": 5, "min": 1, "max": 30},
            "post_news_minutes": {"type": "integer", "default": 15, "min": 5, "max": 60},
            "min_impact": {"type": "string", "default": "high", "options": ["low", "medium", "high"]},
        },
    },
]


def _find_strategy(strategy_id: str) -> dict[str, Any] | None:
    """Lookup a strategy from the catalogue by ID."""
    for s in _STRATEGY_CATALOGUE:
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
            for s in _STRATEGY_CATALOGUE
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


# ─── Per-Account Strategy Configuration ─────────────────────────────────────


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
