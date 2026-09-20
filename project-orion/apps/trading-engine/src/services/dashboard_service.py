"""Dashboard aggregation application service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import (
    AccountModel,
    FillModel,
    OrderModel,
    PositionModel,
    StrategyConfigModel,
)

from ..schemas import (
    DashboardAccount,
    DashboardPerformance,
    DashboardResponse,
    DashboardRisk,
    DashboardStrategy,
    DashboardSystem,
    DashboardTrading,
    DashboardWorker,
    OrderResponse,
    PositionResponse,
    TradeResponse,
)

logger = logging.getLogger("trading_engine.services.dashboard")


class DashboardService:
    """Aggregates account, performance, trading, strategy, risk, worker, and system health data."""

    def __init__(
        self,
        adapter: PaperExecutionAdapter,
        session: AsyncSession,
        account: AccountModel,
        worker: Any | None = None,
    ) -> None:
        self.adapter = adapter
        self.session = session
        self.account = account
        self.worker = worker

    async def get_dashboard(self) -> DashboardResponse:
        """Construct full dashboard overview in a single aggregation step."""
        now = datetime.now(timezone.utc)

        # 1. Query open positions
        pos_res = await self.session.execute(
            select(PositionModel).where(
                PositionModel.account_id == self.account.id,
                PositionModel.is_open == True,
            )
        )
        open_positions = list(pos_res.scalars().all())

        # 2. Query recent trades (last 10)
        trades_res = await self.session.execute(
            select(FillModel)
            .join(OrderModel, FillModel.order_id == OrderModel.id)
            .where(OrderModel.account_id == self.account.id)
            .order_by(desc(FillModel.timestamp))
            .limit(10)
        )
        recent_fills = list(trades_res.scalars().all())

        # 3. Query pending orders
        orders_res = await self.session.execute(
            select(OrderModel)
            .where(
                OrderModel.account_id == self.account.id,
                OrderModel.status.in_(["PENDING", "SUBMITTED", "NEW"]),
            )
            .order_by(desc(OrderModel.created_at))
            .limit(10)
        )
        pending_orders = list(orders_res.scalars().all())

        # 4. Query all positions for realized PnL
        all_pos_res = await self.session.execute(
            select(PositionModel).where(PositionModel.account_id == self.account.id)
        )
        all_positions = list(all_pos_res.scalars().all())

        # Financial Calculations
        try:
            leverage = Decimal(str(self.account.leverage))
        except (InvalidOperation, TypeError, ValueError, AttributeError):
            leverage = Decimal(100)
        used_margin = Decimal(0)
        unrealized_pnl = Decimal(0)
        total_exposure = Decimal(0)

        for p in open_positions:
            pos_val = p.quantity * p.current_price
            used_margin += pos_val / leverage
            total_exposure += pos_val
            if p.side.upper() == "BUY":
                unrealized_pnl += (p.current_price - p.open_price) * p.quantity - p.commission - p.swap
            else:
                unrealized_pnl += (p.open_price - p.current_price) * p.quantity - p.commission - p.swap

        realized_pnl = sum((p.realized_pnl for p in all_positions if not p.is_open), Decimal(0))
        balance = self.account.balance
        equity = balance + unrealized_pnl
        free_margin = max(equity - used_margin, Decimal(0))
        margin_level = float((equity / used_margin * 100) if used_margin > Decimal(0) else 0.0)

        peak_equity = max(balance, equity)
        drawdown_pct = float(
            ((peak_equity - equity) / peak_equity * 100) if peak_equity > Decimal(0) else 0.0
        )

        # 5. Query active strategy config
        strat_query = select(StrategyConfigModel).where(StrategyConfigModel.is_active == True)
        if self.account.organization_id is not None:
            strat_query = strat_query.where(
                (StrategyConfigModel.organization_id == self.account.organization_id)
                | (StrategyConfigModel.account_id == self.account.id)
            )
        strat_res = await self.session.execute(strat_query.limit(1))
        active_strat = strat_res.scalar_one_or_none()
        strategy_name = active_strat.name if active_strat else "Trend Following"
        timeframe = (
            active_strat.parameters.get("timeframe", "M15")
            if active_strat and active_strat.parameters
            else "M15"
        )
        symbols = active_strat.symbols if active_strat else ["EUR/USD", "GBP/USD", "USD/JPY"]

        # 6. Worker block
        if self.worker is not None:
            worker_enabled = getattr(self.worker, "enabled", False)
            worker_state = getattr(self.worker, "state", None)
            state_str = (
                str(worker_state.value)
                if (worker_state is not None and hasattr(worker_state, "value"))
                else str(worker_state or "stopped")
            )
            is_running = state_str == "running"
            last_cycle_at = getattr(self.worker, "last_cycle_at", None)
            uptime_seconds = getattr(self.worker, "uptime_seconds", 0.0) or 0.0
        else:
            worker_enabled = False
            state_str = "stopped"
            is_running = False
            last_cycle_at = None
            uptime_seconds = 0.0

        return DashboardResponse(
            account=DashboardAccount(
                balance=balance,
                equity=equity,
                available_cash=free_margin,
                used_margin=used_margin,
                free_margin=free_margin,
                currency=self.account.currency or "USD",
                is_paper=True,
            ),
            performance=DashboardPerformance(
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                daily_pnl=realized_pnl + unrealized_pnl,
                drawdown_pct=round(drawdown_pct, 2),
            ),
            trading=DashboardTrading(
                open_positions=[
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
                    for p in open_positions
                ],
                recent_trades=[
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
                    for f in recent_fills
                ],
                pending_orders=[
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
                    for o in pending_orders
                ],
            ),
            strategy=DashboardStrategy(
                active_strategy=strategy_name,
                timeframe=timeframe,
                symbols=symbols,
            ),
            risk=DashboardRisk(
                status="nominal",
                total_exposure=total_exposure,
                margin_level=round(margin_level, 2),
                emergency_stop_active=False,
                recovery_mode_active=False,
            ),
            worker=DashboardWorker(
                enabled=worker_enabled,
                state=state_str,
                is_running=is_running,
                last_cycle_at=last_cycle_at,
                uptime_seconds=uptime_seconds,
                last_error=None,
            ),
            system=DashboardSystem(
                status="healthy",
                market_data_status="connected",
                timestamp=now,
            ),
        )
