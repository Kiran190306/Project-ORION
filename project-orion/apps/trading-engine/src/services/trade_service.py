"""Trade/fill history application service."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.infrastructure.persistence.models import (
    AccountModel,
    FillModel,
    OrderModel,
)

from ..schemas import PaginatedResponse, PaginationParams, TradeResponse

logger = logging.getLogger("trading_engine.services.trade")


class TradeService:
    """Manages trade execution history and fill queries."""

    def __init__(
        self,
        session: AsyncSession,
        account: AccountModel,
    ) -> None:
        self.session = session
        self.account = account

    async def list_trades(
        self,
        pagination: PaginationParams,
        symbol: str | None = None,
    ) -> PaginatedResponse[TradeResponse]:
        """List trades (fills) for the account with filtering and pagination."""
        query = (
            select(FillModel)
            .join(OrderModel, FillModel.order_id == OrderModel.id)
            .where(OrderModel.account_id == self.account.id)
        )
        count_query = (
            select(func.count(FillModel.id))
            .join(OrderModel, FillModel.order_id == OrderModel.id)
            .where(OrderModel.account_id == self.account.id)
        )

        if symbol:
            norm_symbol = symbol.upper().strip()
            query = query.where(FillModel.symbol == norm_symbol)
            count_query = count_query.where(FillModel.symbol == norm_symbol)
        if pagination.date_from:
            query = query.where(FillModel.timestamp >= pagination.date_from)
            count_query = count_query.where(FillModel.timestamp >= pagination.date_from)
        if pagination.date_to:
            query = query.where(FillModel.timestamp <= pagination.date_to)
            count_query = count_query.where(FillModel.timestamp <= pagination.date_to)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        sort_col = getattr(FillModel, pagination.sort_by, FillModel.timestamp)
        if pagination.order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        query = query.limit(pagination.limit).offset(pagination.offset)
        res = await self.session.execute(query)
        fills = res.scalars().all()

        items = [
            TradeResponse(
                trade_id=f.id,
                order_id=f.order_id,
                broker_fill_id=f.broker_fill_id,
                symbol=f.symbol,
                side=f.side,
                quantity=f.quantity,
                price=f.price,
                commission=f.commission,
                timestamp=f.timestamp,
                is_paper=True,
            )
            for f in fills
        ]

        has_more = (pagination.offset + pagination.limit) < total
        return PaginatedResponse[TradeResponse](
            items=items,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=has_more,
        )

    async def get_trade(self, trade_id: str) -> TradeResponse:
        """Get single trade by ID with ownership verification."""
        fill_res = await self.session.execute(
            select(FillModel).where(FillModel.id == trade_id)
        )
        fill = fill_res.scalar_one_or_none()
        if fill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade '{trade_id}' not found",
            )
        order_res = await self.session.execute(
            select(OrderModel).where(OrderModel.id == fill.order_id)
        )
        order = order_res.scalar_one_or_none()
        if (
            order is None
            or order.account_id != self.account.id
            or (
                self.account.organization_id is not None
                and fill.organization_id is not None
                and fill.organization_id != self.account.organization_id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: access to this trade is not permitted",
            )

        return TradeResponse(
            trade_id=fill.id,
            order_id=fill.order_id,
            broker_fill_id=fill.broker_fill_id,
            symbol=fill.symbol,
            side=fill.side,
            quantity=fill.quantity,
            price=fill.price,
            commission=fill.commission,
            timestamp=fill.timestamp,
            is_paper=True,
        )
