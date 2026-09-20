"""Position application service for querying and managing positions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import AccountModel, PositionModel

from ..schemas import (
    ClosePositionResponse,
    PaginatedResponse,
    PaginationParams,
    PositionResponse,
)

logger = logging.getLogger("trading_engine.services.position")


class PositionService:
    """Manages open and historical positions for an account."""

    def __init__(
        self,
        adapter: PaperExecutionAdapter,
        session: AsyncSession,
        account: AccountModel,
    ) -> None:
        self.adapter = adapter
        self.session = session
        self.account = account

    async def _ensure_connected(self) -> None:
        """Ensure the execution adapter is connected."""
        if not getattr(self.adapter, "_connected", False):
            try:
                await self.adapter.connect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Auto-connect adapter produced: %s", exc)

    async def list_positions(
        self,
        pagination: PaginationParams,
        symbol: str | None = None,
        is_open: bool | None = None,
    ) -> PaginatedResponse[PositionResponse]:
        """List positions with optional filtering and pagination."""
        query = select(PositionModel).where(PositionModel.account_id == self.account.id)
        count_query = select(func.count(PositionModel.id)).where(
            PositionModel.account_id == self.account.id
        )

        if symbol:
            norm_symbol = symbol.upper().strip()
            query = query.where(PositionModel.symbol == norm_symbol)
            count_query = count_query.where(PositionModel.symbol == norm_symbol)
        if is_open is not None:
            query = query.where(PositionModel.is_open == is_open)
            count_query = count_query.where(PositionModel.is_open == is_open)
        if pagination.date_from:
            query = query.where(PositionModel.opened_at >= pagination.date_from)
            count_query = count_query.where(PositionModel.opened_at >= pagination.date_from)
        if pagination.date_to:
            query = query.where(PositionModel.opened_at <= pagination.date_to)
            count_query = count_query.where(PositionModel.opened_at <= pagination.date_to)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        sort_col = getattr(PositionModel, pagination.sort_by, PositionModel.opened_at)
        if pagination.order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        query = query.limit(pagination.limit).offset(pagination.offset)
        res = await self.session.execute(query)
        positions = res.scalars().all()

        items = [
            PositionResponse(
                id=p.id,
                account_id=p.account_id,
                symbol=p.symbol,
                side=p.side,
                quantity=p.quantity,
                open_price=p.open_price,
                current_price=p.current_price,
                stop_loss=p.stop_loss,
                take_profit=p.take_profit,
                realized_pnl=p.realized_pnl,
                unrealized_pnl=p.unrealized_pnl,
                commission=p.commission,
                swap=p.swap,
                is_open=p.is_open,
                opened_at=p.opened_at,
                closed_at=p.closed_at,
            )
            for p in positions
        ]

        has_more = (pagination.offset + pagination.limit) < total
        return PaginatedResponse[PositionResponse](
            items=items,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=has_more,
        )

    async def get_position(self, position_id: str) -> PositionResponse:
        """Get single position by ID with ownership verification."""
        res = await self.session.execute(
            select(PositionModel).where(PositionModel.id == position_id)
        )
        pos = res.scalar_one_or_none()
        if pos is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position '{position_id}' not found",
            )
        if pos.account_id != self.account.id or (
            self.account.organization_id is not None
            and pos.organization_id is not None
            and pos.organization_id != self.account.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: access to this position is not permitted",
            )

        return PositionResponse(
            id=pos.id,
            account_id=pos.account_id,
            symbol=pos.symbol,
            side=pos.side,
            quantity=pos.quantity,
            open_price=pos.open_price,
            current_price=pos.current_price,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            realized_pnl=pos.realized_pnl,
            unrealized_pnl=pos.unrealized_pnl,
            commission=pos.commission,
            swap=pos.swap,
            is_open=pos.is_open,
            opened_at=pos.opened_at,
            closed_at=pos.closed_at,
        )

    async def close_position(self, position_id: str) -> ClosePositionResponse:
        """Close an open position, updating PnL and account balance."""
        res = await self.session.execute(
            select(PositionModel).where(PositionModel.id == position_id)
        )
        pos = res.scalar_one_or_none()
        if pos is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position '{position_id}' not found",
            )
        if pos.account_id != self.account.id or (
            self.account.organization_id is not None
            and pos.organization_id is not None
            and pos.organization_id != self.account.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: cannot close a position belonging to another account",
            )
        if not pos.is_open:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Position '{position_id}' is already closed",
            )

        await self._ensure_connected()

        # Attempt to close in adapter if tracked there
        close_price = pos.current_price
        try:
            exec_info = await self.adapter.close_position(position_id)
            if exec_info.average_fill_price:
                close_price = exec_info.average_fill_price
        except Exception as exc:  # noqa: BLE001
            logger.debug("Adapter close note (falling back to stored price): %s", exc)

        now = datetime.now(timezone.utc)

        # Calculate realized P&L
        if pos.side.upper() == "BUY":
            pnl = (close_price - pos.open_price) * pos.quantity - pos.commission - pos.swap
        else:
            pnl = (pos.open_price - close_price) * pos.quantity - pos.commission - pos.swap

        pos.is_open = False
        pos.closed_at = now
        pos.realized_pnl = pnl
        pos.unrealized_pnl = Decimal(0)
        pos.current_price = close_price

        # Update account balance and equity
        self.account.balance += pnl
        self.account.equity += pnl
        self.account.margin_free = self.account.equity - self.account.margin

        await self.session.flush()

        return ClosePositionResponse(
            position_id=pos.id,
            symbol=pos.symbol,
            closed_quantity=pos.quantity,
            close_price=close_price,
            realized_pnl=pnl,
            closed_at=now,
            message="Position closed successfully",
        )
