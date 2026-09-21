"""Paper trading simulation control and reset endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import (
    AccountModel,
    AuditLogModel,
    OrderModel,
    PositionModel,
)

from ..dependencies import (
    get_current_active_user,
    get_db_session,
    get_paper_adapter,
    get_user_account,
    require_permission,
)
from ..schemas import (
    PaperConfigResponse,
    PaperResetRequest,
    PaperResetResponse,
    UpdatePaperConfigRequest,
)

logger = logging.getLogger("trading_engine.routes.paper")

router = APIRouter(prefix="/api/v1/trading/paper", tags=["Paper Trading Controls"])


@router.post(
    "/reset",
    response_model=PaperResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Paper Account",
    description="Resets paper trading account balance to initial capital, closes all active positions, and cancels all pending orders.",
)
async def reset_paper_account(
    request: PaperResetRequest,
    account: Annotated[AccountModel, Depends(get_user_account)],
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ORDER_CREATE))],
) -> PaperResetResponse:
    """Reset paper account balance and wipe simulation state."""
    now = datetime.now(timezone.utc)

    # 1. Close all active positions in DB for this account
    pos_stmt = (
        update(PositionModel)
        .where(
            PositionModel.account_id == account.id,
            PositionModel.is_open.is_(True),
        )
        .values(
            is_open=False,
            closed_at=now,
        )
    )
    pos_res = await session.execute(pos_stmt)
    positions_closed = pos_res.rowcount or 0

    # 2. Cancel all pending / submitted orders in DB
    ord_stmt = (
        update(OrderModel)
        .where(
            OrderModel.account_id == account.id,
            OrderModel.status.in_(["new", "validated", "submitted", "pending", "NEW", "VALIDATED", "SUBMITTED", "PENDING"]),
        )
        .values(
            status="CANCELLED",
            updated_at=now,
        )
    )
    ord_res = await session.execute(ord_stmt)
    orders_cancelled = ord_res.rowcount or 0

    # 3. Update account balance, equity, and margin
    account.balance = request.balance
    account.equity = request.balance
    account.margin = Decimal(0)
    account.margin_free = request.balance
    account.margin_level = 0.0

    # 4. Reset in-memory adapter state
    await adapter.reset_account(request.balance)

    # 5. Record audit log
    audit_entry = AuditLogModel(
        id=f"aud_{uuid.uuid4().hex[:16]}",
        organization_id=account.organization_id,
        event_type="paper_account.reset",
        component="trading_engine.paper_controls",
        actor=str(user["id"]),
        details={
            "account_id": account.id,
            "reset_balance": str(request.balance),
            "positions_closed": positions_closed,
            "orders_cancelled": orders_cancelled,
        },
        timestamp=now,
    )
    session.add(audit_entry)
    await session.flush()

    logger.info(
        "Paper account %s reset to %s by user %s (closed %s pos, cancelled %s ord)",
        account.id,
        request.balance,
        user["id"],
        positions_closed,
        orders_cancelled,
    )

    return PaperResetResponse(
        message="Paper account successfully reset",
        account_id=account.id,
        balance=account.balance,
        equity=account.equity,
        positions_closed=positions_closed,
        orders_cancelled=orders_cancelled,
    )


@router.get(
    "/config",
    response_model=PaperConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Paper Simulation Configuration",
    description="Returns current paper trading microstructure simulation parameters (spread, slippage, latency, etc.).",
)
async def get_paper_config(
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
) -> PaperConfigResponse:
    """Retrieve paper execution simulation parameters."""
    cfg = adapter.config
    return PaperConfigResponse(
        broker_name=cfg.broker_name,
        is_paper=cfg.is_paper,
        spread=cfg.spread,
        slippage_mean=cfg.slippage_mean,
        slippage_std=cfg.slippage_std,
        commission_rate=cfg.commission_rate,
        swap_long_rate=cfg.swap_long_rate,
        swap_short_rate=cfg.swap_short_rate,
        latency_ms_mean=cfg.latency_ms_mean,
        latency_ms_std=cfg.latency_ms_std,
        partial_fill_probability=cfg.partial_fill_probability,
        min_fill_ratio=cfg.min_fill_ratio,
        deterministic=cfg.deterministic,
        leverage=cfg.leverage,
    )


@router.patch(
    "/config",
    response_model=PaperConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Paper Simulation Configuration",
    description="Dynamically configures paper trading microstructure simulation parameters (e.g. deterministic mode, spread, slippage).",
)
async def update_paper_config(
    request: UpdatePaperConfigRequest,
    adapter: Annotated[PaperExecutionAdapter, Depends(get_paper_adapter)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.STRATEGY_CONFIGURE))],
) -> PaperConfigResponse:
    """Update paper execution simulation parameters."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    adapter.update_config(**updates)
    cfg = adapter.config
    return PaperConfigResponse(
        broker_name=cfg.broker_name,
        is_paper=cfg.is_paper,
        spread=cfg.spread,
        slippage_mean=cfg.slippage_mean,
        slippage_std=cfg.slippage_std,
        commission_rate=cfg.commission_rate,
        swap_long_rate=cfg.swap_long_rate,
        swap_short_rate=cfg.swap_short_rate,
        latency_ms_mean=cfg.latency_ms_mean,
        latency_ms_std=cfg.latency_ms_std,
        partial_fill_probability=cfg.partial_fill_probability,
        min_fill_ratio=cfg.min_fill_ratio,
        deterministic=cfg.deterministic,
        leverage=cfg.leverage,
    )
