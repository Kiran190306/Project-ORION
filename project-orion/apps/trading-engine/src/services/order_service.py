"""Order application service for managing order lifecycle, execution, and history."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.execution.models import (
    BrokerOrderId,
    Order,
    OrderId,
    OrderSide,
    OrderType,
)
from libraries.domain.subscription.exceptions import (
    AssetNotEntitledError,
    DailyOrderQuotaExceededError,
    EntitlementError,
    SubscriptionInactiveError,
)
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import (
    AccountModel,
    ExecutionReportModel,
    FillModel,
    OrderModel,
    PositionModel,
)

from ..schemas import (
    CancelOrderResponse,
    CreateOrderRequest,
    OrderResponse,
    PaginatedResponse,
    PaginationParams,
)
from .entitlement_service import EntitlementService

logger = logging.getLogger("trading_engine.services.order")


class OrderService:
    """Orchestrates order creation, querying, and cancellation."""

    def __init__(
        self,
        adapter: PaperExecutionAdapter,
        session: AsyncSession,
        account: AccountModel,
        entitlement_service: EntitlementService | None = None,
    ) -> None:
        self.adapter = adapter
        self.session = session
        self.account = account
        self.entitlement_service = entitlement_service or EntitlementService(session)

    async def _ensure_connected(self) -> None:
        """Ensure the execution adapter is connected."""
        if not getattr(self.adapter, "_connected", False):
            try:
                await self.adapter.connect()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Auto-connect adapter produced: %s", exc)

    async def create_order(self, request: CreateOrderRequest) -> OrderResponse:
        """Create and submit a paper trading order."""
        # Enforce subscription tier entitlements and quotas before paper execution
        if self.entitlement_service is not None:
            try:
                await self.entitlement_service.check_asset_access(
                    self.account.organization_id, request.symbol
                )
                await self.entitlement_service.check_daily_order_quota(
                    self.account.organization_id
                )
            except AssetNotEntitledError as exc:
                logger.warning(
                    "Order rejected: asset not entitled: symbol=%s org=%s",
                    request.symbol,
                    self.account.organization_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=exc.message,
                ) from exc
            except DailyOrderQuotaExceededError as exc:
                logger.warning(
                    "Order rejected: daily order quota exceeded: org=%s current=%s limit=%s",
                    self.account.organization_id,
                    exc.current,
                    exc.limit,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=exc.message,
                ) from exc
            except SubscriptionInactiveError as exc:
                logger.warning(
                    "Order rejected: subscription inactive: org=%s status=%s",
                    self.account.organization_id,
                    exc.status,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=exc.message,
                ) from exc
            except EntitlementError as exc:
                logger.warning(
                    "Order rejected: entitlement error: org=%s detail=%s",
                    self.account.organization_id,
                    exc.message,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=exc.message,
                ) from exc

        await self._ensure_connected()

        # Pre-trade margin check (when account balance is configured)
        leverage = Decimal(str(self.account.leverage or 100))
        ref_price = request.price or Decimal("1.20000")
        required_margin = (request.quantity * ref_price) / leverage
        if (
            self.account.balance > Decimal(0)
            and self.account.margin_free > Decimal(0)
            and required_margin > self.account.margin_free
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order rejected: insufficient free margin (required: {required_margin:.2f}, free: {self.account.margin_free:.2f})",
            )

        order_id_str = f"ord_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)

        # Map side
        side = OrderSide.BUY if request.side.value.upper() == "BUY" else OrderSide.SELL

        # Map order type
        req_type = request.order_type.value.upper()
        if req_type == "MARKET":
            order_type = OrderType.MARKET
        elif req_type == "LIMIT":
            order_type = OrderType.LIMIT
        elif req_type == "STOP":
            order_type = OrderType.STOP
        elif req_type == "TRAILING_STOP":
            order_type = OrderType.TRAILING_STOP
        else:
            order_type = OrderType.MARKET

        domain_order = Order(
            order_id=OrderId(order_id_str),
            decision_id=f"dec_{uuid.uuid4().hex[:12]}",
            execution_id=f"exe_{uuid.uuid4().hex[:12]}",
            symbol=request.symbol,
            side=side,
            order_type=order_type,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            trailing_distance=getattr(request, "trailing_distance", None),
        )

        try:
            exec_info = await self.adapter.submit_order(domain_order)
        except Exception as exc:
            logger.error("Order submission failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to submit order: {exc}",
            ) from exc

        broker_order_id = str(exec_info.broker_order_id) if exec_info.broker_order_id else None
        status_val = exec_info.status.value.upper()

        order_model = OrderModel(
            id=order_id_str,
            organization_id=self.account.organization_id,
            broker_order_id=broker_order_id,
            account_id=self.account.id,
            symbol=request.symbol,
            side=request.side.value.upper(),
            order_type=request.order_type.value.upper(),
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            status=status_val,
            filled_quantity=exec_info.filled_quantity,
            average_fill_price=exec_info.average_fill_price,
            strategy_id=request.strategy_id,
            meta_data={"trailing_distance": str(request.trailing_distance)} if getattr(request, "trailing_distance", None) else {},
            created_at=now,
            updated_at=now,
        )
        self.session.add(order_model)

        # Record fills
        for fill in exec_info.fills:
            fill_model = FillModel(
                id=f"fill_{uuid.uuid4().hex[:16]}",
                organization_id=self.account.organization_id,
                order_id=order_id_str,
                broker_fill_id=str(fill.broker_fill_id) if fill.broker_fill_id else fill.fill_id,
                symbol=request.symbol,
                side=request.side.value.upper(),
                quantity=fill.quantity,
                price=fill.price,
                commission=fill.commission,
                timestamp=now,
            )
            self.session.add(fill_model)

        # Record execution audit report
        exec_report = ExecutionReportModel(
            id=f"rep_{uuid.uuid4().hex[:16]}",
            order_id=order_id_str,
            status=status_val,
            latency_ms=0.0,
            slippage_pips=0.0,
            timestamp=now,
        )
        self.session.add(exec_report)

        # Position netting & balance accounting when fills occur
        if exec_info.filled_quantity > Decimal(0):
            fill_price = exec_info.average_fill_price or Decimal("1.20000")
            fill_qty = exec_info.filled_quantity
            side_str = request.side.value.upper()

            # Deduct commission from cash balance
            if exec_info.commission > Decimal(0):
                self.account.balance -= exec_info.commission
                self.account.equity -= exec_info.commission

            # Check existing open position for this account and symbol
            pos_stmt = select(PositionModel).where(
                PositionModel.account_id == self.account.id,
                PositionModel.symbol == request.symbol,
                PositionModel.is_open.is_(True),
            )
            pos_res = await self.session.execute(pos_stmt)
            existing_pos = pos_res.scalar_one_or_none()

            if existing_pos is None:
                # 1. No open position: open new position
                pos_id = f"pos_{uuid.uuid4().hex[:16]}"
                position_model = PositionModel(
                    id=pos_id,
                    organization_id=self.account.organization_id,
                    account_id=self.account.id,
                    symbol=request.symbol,
                    side=side_str,
                    quantity=fill_qty,
                    open_price=fill_price,
                    current_price=fill_price,
                    stop_loss=request.stop_loss,
                    take_profit=request.take_profit,
                    realized_pnl=Decimal(0),
                    unrealized_pnl=Decimal(0),
                    commission=exec_info.commission,
                    swap=Decimal(0),
                    is_open=True,
                    opened_at=now,
                    meta_data={
                        "order_id": order_id_str,
                        "trailing_distance": str(request.trailing_distance) if getattr(request, "trailing_distance", None) else None,
                    },
                )
                self.session.add(position_model)
                self.account.margin += required_margin
            elif existing_pos.side == side_str:
                # 2. Same direction: accumulate position with weighted average entry price
                new_qty = existing_pos.quantity + fill_qty
                new_open_price = ((existing_pos.open_price * existing_pos.quantity) + (fill_price * fill_qty)) / new_qty
                existing_pos.quantity = new_qty
                existing_pos.open_price = new_open_price
                existing_pos.current_price = fill_price
                existing_pos.commission += exec_info.commission
                if request.stop_loss is not None:
                    existing_pos.stop_loss = request.stop_loss
                if request.take_profit is not None:
                    existing_pos.take_profit = request.take_profit
                self.account.margin += required_margin
            else:
                # 3. Opposite direction: netting / reduction / closure
                if fill_qty < existing_pos.quantity:
                    closed_qty = fill_qty
                    if existing_pos.side == "BUY":
                        realized_pnl = (fill_price - existing_pos.open_price) * closed_qty
                    else:
                        realized_pnl = (existing_pos.open_price - fill_price) * closed_qty

                    existing_pos.quantity -= closed_qty
                    existing_pos.realized_pnl += realized_pnl
                    existing_pos.current_price = fill_price
                    self.account.balance += realized_pnl
                    self.account.equity += realized_pnl

                    released_margin = (closed_qty * existing_pos.open_price) / leverage
                    self.account.margin = max(Decimal(0), self.account.margin - released_margin)
                elif fill_qty == existing_pos.quantity:
                    if existing_pos.side == "BUY":
                        realized_pnl = (fill_price - existing_pos.open_price) * existing_pos.quantity
                    else:
                        realized_pnl = (existing_pos.open_price - fill_price) * existing_pos.quantity

                    existing_pos.is_open = False
                    existing_pos.closed_at = now
                    existing_pos.realized_pnl += realized_pnl
                    existing_pos.current_price = fill_price
                    self.account.balance += realized_pnl
                    self.account.equity += realized_pnl

                    released_margin = (existing_pos.quantity * existing_pos.open_price) / leverage
                    self.account.margin = max(Decimal(0), self.account.margin - released_margin)
                else:
                    # Reversal
                    closed_qty = existing_pos.quantity
                    residual_qty = fill_qty - existing_pos.quantity

                    if existing_pos.side == "BUY":
                        realized_pnl = (fill_price - existing_pos.open_price) * closed_qty
                    else:
                        realized_pnl = (existing_pos.open_price - fill_price) * closed_qty

                    existing_pos.is_open = False
                    existing_pos.closed_at = now
                    existing_pos.realized_pnl += realized_pnl
                    existing_pos.current_price = fill_price
                    self.account.balance += realized_pnl
                    self.account.equity += realized_pnl

                    old_margin = (closed_qty * existing_pos.open_price) / leverage
                    self.account.margin = max(Decimal(0), self.account.margin - old_margin)

                    # Open residual position in opposite direction
                    pos_id = f"pos_{uuid.uuid4().hex[:16]}"
                    position_model = PositionModel(
                        id=pos_id,
                        organization_id=self.account.organization_id,
                        account_id=self.account.id,
                        symbol=request.symbol,
                        side=side_str,
                        quantity=residual_qty,
                        open_price=fill_price,
                        current_price=fill_price,
                        stop_loss=request.stop_loss,
                        take_profit=request.take_profit,
                        realized_pnl=Decimal(0),
                        unrealized_pnl=Decimal(0),
                        commission=Decimal(0),
                        swap=Decimal(0),
                        is_open=True,
                        opened_at=now,
                        meta_data={"order_id": order_id_str},
                    )
                    self.session.add(position_model)
                    new_margin = (residual_qty * fill_price) / leverage
                    self.account.margin += new_margin

            # Recalculate free margin and margin level
            self.account.margin_free = max(Decimal(0), self.account.equity - self.account.margin)
            if self.account.margin > Decimal(0):
                self.account.margin_level = float((self.account.equity / self.account.margin) * Decimal(100))

        await self.session.flush()

        return OrderResponse(
            id=order_id_str,
            broker_order_id=broker_order_id,
            account_id=self.account.id,
            symbol=request.symbol,
            side=request.side.value.upper(),
            order_type=request.order_type.value.upper(),
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            trailing_distance=getattr(request, "trailing_distance", None),
            status=status_val,
            filled_quantity=exec_info.filled_quantity,
            average_fill_price=exec_info.average_fill_price,
            strategy_id=request.strategy_id,
            is_paper=True,
            created_at=now,
            updated_at=now,
            meta_data={},
        )

    async def list_orders(
        self,
        pagination: PaginationParams,
        symbol: str | None = None,
        status_filter: str | None = None,
    ) -> PaginatedResponse[OrderResponse]:
        """List orders for the user's account with filtering and pagination."""
        query = select(OrderModel).where(OrderModel.account_id == self.account.id)
        count_query = select(func.count(OrderModel.id)).where(
            OrderModel.account_id == self.account.id
        )

        if symbol:
            norm_symbol = symbol.upper().strip()
            query = query.where(OrderModel.symbol == norm_symbol)
            count_query = count_query.where(OrderModel.symbol == norm_symbol)
        if status_filter:
            norm_status = status_filter.upper().strip()
            query = query.where(OrderModel.status == norm_status)
            count_query = count_query.where(OrderModel.status == norm_status)
        if pagination.date_from:
            query = query.where(OrderModel.created_at >= pagination.date_from)
            count_query = count_query.where(OrderModel.created_at >= pagination.date_from)
        if pagination.date_to:
            query = query.where(OrderModel.created_at <= pagination.date_to)
            count_query = count_query.where(OrderModel.created_at <= pagination.date_to)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        sort_col = getattr(OrderModel, pagination.sort_by, OrderModel.created_at)
        if pagination.order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        query = query.limit(pagination.limit).offset(pagination.offset)
        res = await self.session.execute(query)
        orders = res.scalars().all()

        items = [
            OrderResponse(
                id=o.id,
                broker_order_id=o.broker_order_id,
                account_id=o.account_id,
                symbol=o.symbol,
                side=o.side,
                order_type=o.order_type,
                quantity=o.quantity,
                price=o.price,
                stop_price=o.stop_price,
                stop_loss=o.stop_loss,
                take_profit=o.take_profit,
                status=o.status,
                filled_quantity=o.filled_quantity,
                average_fill_price=o.average_fill_price,
                strategy_id=o.strategy_id,
                is_paper=True,
                created_at=o.created_at,
                updated_at=o.updated_at,
                meta_data=o.meta_data or {},
            )
            for o in orders
        ]

        has_more = (pagination.offset + pagination.limit) < total
        return PaginatedResponse[OrderResponse](
            items=items,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
            has_more=has_more,
        )

    async def get_order(self, order_id: str) -> OrderResponse:
        """Get a single order by ID with ownership verification."""
        res = await self.session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = res.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )
        if order.account_id != self.account.id or (
            self.account.organization_id is not None
            and order.organization_id is not None
            and order.organization_id != self.account.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: access to this order is not permitted",
            )

        return OrderResponse(
            id=order.id,
            broker_order_id=order.broker_order_id,
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
            status=order.status,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            strategy_id=order.strategy_id,
            is_paper=True,
            created_at=order.created_at,
            updated_at=order.updated_at,
            meta_data=order.meta_data or {},
        )

    async def cancel_order(self, order_id: str) -> CancelOrderResponse:
        """Cancel a pending order with ownership verification."""
        res = await self.session.execute(
            select(OrderModel).where(OrderModel.id == order_id)
        )
        order = res.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found",
            )
        if order.account_id != self.account.id or (
            self.account.organization_id is not None
            and order.organization_id is not None
            and order.organization_id != self.account.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: cannot cancel an order from another account",
            )

        if order.status.upper() in ("FILLED", "CANCELLED", "REJECTED", "EXPIRED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status '{order.status}'",
            )

        if order.broker_order_id:
            await self._ensure_connected()
            try:
                await self.adapter.cancel_order(BrokerOrderId(order.broker_order_id))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Adapter order cancellation note: %s", exc)

        order.status = "CANCELLED"
        order.updated_at = datetime.now(timezone.utc)
        await self.session.flush()

        return CancelOrderResponse(
            order_id=order.id,
            status="CANCELLED",
            message="Order cancelled successfully",
        )
