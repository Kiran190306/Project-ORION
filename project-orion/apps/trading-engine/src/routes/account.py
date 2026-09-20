"""Account management endpoints for paper trading accounts.

Protected by JWT authentication — all endpoints require a valid token.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from libraries.domain.organization.permissions import Permission
from libraries.infrastructure.execution.paper_execution import PaperExecutionConfig

from ..dependencies import (
    get_current_active_user,
    get_paper_trading_service,
    require_permission,
)
from ..schemas import AccountResponse, AccountSummary
from ..services.paper_trading import PaperTradingService

logger = logging.getLogger("trading_engine.routes.account")

router = APIRouter(prefix="/api/v1/account", tags=["Account"])


@router.get(
    "/summary",
    response_model=AccountSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Account Summary",
    description="Returns current account balance, equity, margin, and P&L for the paper trading account.",
)
async def get_account_summary(
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> AccountSummary:
    """Get current account summary for paper trading."""
    try:
        # Get account balance from paper adapter configuration
        # PaperExecutionConfig extends BrokerAdapterConfig and has balance field
        config = service.paper_adapter.config
        if isinstance(config, PaperExecutionConfig):
            balance = config.balance
        else:
            balance = Decimal("100000.00")  # Fallback default

        # For now, return basic summary
        # In future, this should integrate with Portfolio domain for real-time P&L
        return AccountSummary(
            balance=balance,
            equity=balance,  # Will be updated with real-time P&L
            available_cash=balance,  # Will be updated with margin calculation
            used_margin=Decimal(0),
            free_margin=balance,
            unrealized_pnl=Decimal(0),
            realized_pnl=Decimal(0),
            currency="USD",
            is_paper=True,
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to get account summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account summary",
        ) from exc


@router.get(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Account Details",
    description="Returns detailed account information including configuration and status.",
)
async def get_account(
    service: Annotated[PaperTradingService, Depends(get_paper_trading_service)],
    user: Annotated[dict[str, Any], Depends(get_current_active_user)],
    _perm: Annotated[Any, Depends(require_permission(Permission.ACCOUNT_READ))],
) -> AccountResponse:
    """Get detailed account information."""
    try:
        config = service.paper_adapter.config
        if isinstance(config, PaperExecutionConfig):
            balance = config.balance
            broker_name = config.broker_name
            is_live = not config.is_paper
        else:
            balance = Decimal("100000.00")
            broker_name = config.broker_name
            is_live = False

        return AccountResponse(
            account_id="paper-default",
            broker_name=broker_name,
            account_number="PAPER-001",
            balance=balance,
            equity=balance,
            currency="USD",
            leverage=100,
            is_live=is_live,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("Failed to get account details: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account details",
        ) from exc
