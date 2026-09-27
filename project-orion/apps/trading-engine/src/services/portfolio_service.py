"""Portfolio application service for financial metrics, equity, PnL, and exposure."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import (
    AccountModel,
    OrderModel,
    PositionModel,
    StrategyConfigModel,
    StrategyDeploymentModel,
)

from ..schemas import (
    CurrencyExposure,
    EquityCurveResponse,
    ExposureResponse,
    MultiStrategyPortfolioResponse,
    PnLBreakdownResponse,
    PortfolioOverviewResponse,
    StrategyPortfolioItem,
)

logger = logging.getLogger("trading_engine.services.portfolio")


class PortfolioService:
    """Calculates portfolio overview, equity curves, PnL breakdown, and exposures."""

    def __init__(
        self,
        adapter: PaperExecutionAdapter,
        session: AsyncSession,
        account: AccountModel,
    ) -> None:
        self.adapter = adapter
        self.session = session
        self.account = account

    async def _get_open_positions(self) -> list[PositionModel]:
        res = await self.session.execute(
            select(PositionModel).where(
                PositionModel.account_id == self.account.id,
                PositionModel.is_open == True,
            )
        )
        return list(res.scalars().all())

    async def _get_all_positions(self) -> list[PositionModel]:
        res = await self.session.execute(
            select(PositionModel).where(PositionModel.account_id == self.account.id)
        )
        return list(res.scalars().all())

    async def get_overview(self) -> PortfolioOverviewResponse:
        """Get consolidated portfolio overview metrics."""
        now = datetime.now(timezone.utc)
        open_positions = await self._get_open_positions()
        all_positions = await self._get_all_positions()

        try:
            leverage = Decimal(str(self.account.leverage))
        except (InvalidOperation, TypeError, ValueError, AttributeError):
            leverage = Decimal(100)
        used_margin = Decimal(0)
        unrealized_pnl = Decimal(0)
        long_exp = Decimal(0)
        short_exp = Decimal(0)

        for p in open_positions:
            pos_val = p.quantity * p.current_price
            used_margin += pos_val / leverage
            if p.side.upper() == "BUY":
                unrealized_pnl += (p.current_price - p.open_price) * p.quantity - p.commission - p.swap
                long_exp += pos_val
            else:
                unrealized_pnl += (p.open_price - p.current_price) * p.quantity - p.commission - p.swap
                short_exp += pos_val

        realized_pnl = sum((p.realized_pnl for p in all_positions if not p.is_open), Decimal(0))
        balance = self.account.balance
        equity = balance + unrealized_pnl
        free_margin = max(equity - used_margin, Decimal(0))
        margin_level = float((equity / used_margin * 100) if used_margin > Decimal(0) else 0.0)

        gross_exposure = long_exp + short_exp
        net_exposure = long_exp - short_exp

        return PortfolioOverviewResponse(
            balance=balance,
            equity=equity,
            used_margin=used_margin,
            free_margin=free_margin,
            margin_level=round(margin_level, 2),
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            net_exposure=net_exposure,
            gross_exposure=gross_exposure,
            open_positions_count=len(open_positions),
            currency=self.account.currency or "USD",
            is_paper=True,
            updated_at=now,
        )

    async def get_equity(self) -> EquityCurveResponse:
        """Get equity and drawdown metrics."""
        overview = await self.get_overview()
        peak_equity = max(overview.balance, overview.equity)
        current_drawdown = float(
            ((peak_equity - overview.equity) / peak_equity * 100) if peak_equity > Decimal(0) else 0.0
        )

        return EquityCurveResponse(
            balance=overview.balance,
            equity=overview.equity,
            peak_equity=peak_equity,
            current_drawdown=round(current_drawdown, 2),
            max_drawdown=round(current_drawdown, 2),
            currency=self.account.currency or "USD",
            updated_at=datetime.now(timezone.utc),
        )

    async def get_pnl(self) -> PnLBreakdownResponse:
        """Get comprehensive PnL breakdown."""
        all_positions = await self._get_all_positions()
        now = datetime.now(timezone.utc)

        gross_profit = Decimal(0)
        gross_loss = Decimal(0)
        total_commission = Decimal(0)
        total_swap = Decimal(0)
        realized_pnl = Decimal(0)
        unrealized_pnl = Decimal(0)

        for p in all_positions:
            total_commission += p.commission
            total_swap += p.swap
            if p.is_open:
                if p.side.upper() == "BUY":
                    pnl = (p.current_price - p.open_price) * p.quantity
                else:
                    pnl = (p.open_price - p.current_price) * p.quantity
                unrealized_pnl += pnl - p.commission - p.swap
            else:
                realized_pnl += p.realized_pnl
                if p.realized_pnl > Decimal(0):
                    gross_profit += p.realized_pnl
                else:
                    gross_loss += abs(p.realized_pnl)

        net_pnl = realized_pnl + unrealized_pnl

        return PnLBreakdownResponse(
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            commission=total_commission,
            swap=total_swap,
            fees=Decimal(0),
            net_pnl=net_pnl,
            currency=self.account.currency or "USD",
            updated_at=now,
        )

    async def get_exposure(self) -> ExposureResponse:
        """Get aggregate and currency-specific exposure breakdown."""
        now = datetime.now(timezone.utc)
        open_positions = await self._get_open_positions()

        long_exp = Decimal(0)
        short_exp = Decimal(0)
        curr_map: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"long": Decimal(0), "short": Decimal(0), "count": 0}
        )

        for p in open_positions:
            pos_val = p.quantity * p.current_price
            base_curr = p.symbol.split("/")[0] if "/" in p.symbol else p.symbol[:3]
            curr_map[base_curr]["count"] += 1

            if p.side.upper() == "BUY":
                long_exp += pos_val
                curr_map[base_curr]["long"] += pos_val
            else:
                short_exp += pos_val
                curr_map[base_curr]["short"] += pos_val

        gross_exp = long_exp + short_exp
        net_exp = long_exp - short_exp

        currency_exposures = [
            CurrencyExposure(
                currency=curr,
                long_exposure=data["long"],
                short_exposure=data["short"],
                net_exposure=data["long"] - data["short"],
                position_count=data["count"],
            )
            for curr, data in curr_map.items()
        ]

        return ExposureResponse(
            net_exposure=net_exp,
            gross_exposure=gross_exp,
            long_exposure=long_exp,
            short_exposure=short_exp,
            currency_exposures=currency_exposures,
            updated_at=now,
        )

    async def get_strategy_breakdown(self) -> MultiStrategyPortfolioResponse:
        """Calculate multi-strategy execution and allocation breakdown."""
        now = datetime.now(timezone.utc)
        # 1. Fetch all strategy configs for account/organization
        cfg_query = select(StrategyConfigModel)
        if self.account.organization_id is not None:
            cfg_query = cfg_query.where(
                (StrategyConfigModel.organization_id == self.account.organization_id)
                | (StrategyConfigModel.account_id == self.account.id)
            )
        else:
            cfg_query = cfg_query.where(
                (StrategyConfigModel.account_id == self.account.id)
                | (StrategyConfigModel.organization_id.is_(None))
            )
        cfg_res = await self.session.execute(cfg_query)
        configs = list(cfg_res.scalars().all())

        # 2. Fetch all deployments for organization
        deployments_map: dict[str, StrategyDeploymentModel] = {}
        if self.account.organization_id:
            dep_query = (
                select(StrategyDeploymentModel)
                .where(
                    StrategyDeploymentModel.organization_id == self.account.organization_id
                )
                .order_by(StrategyDeploymentModel.created_at.desc())
            )
            dep_res = await self.session.execute(dep_query)
            for dep in dep_res.scalars().all():
                if dep.strategy_id not in deployments_map:
                    deployments_map[dep.strategy_id] = dep

        # 3. Fetch all positions and orders for this account
        all_positions = await self._get_all_positions()
        ord_query = select(OrderModel).where(OrderModel.account_id == self.account.id)
        ord_res = await self.session.execute(ord_query)
        all_orders = list(ord_res.scalars().all())

        # Group positions by strategy_id
        pos_by_strategy: dict[str, list[PositionModel]] = defaultdict(list)
        for p in all_positions:
            meta = p.meta_data if isinstance(p.meta_data, dict) else {}
            s_id = meta.get("strategy_id") or "unassigned"
            pos_by_strategy[s_id].append(p)

        # Group orders by strategy_id
        ord_by_strategy: dict[str, list[OrderModel]] = defaultdict(list)
        for o in all_orders:
            s_id = o.strategy_id or "unassigned"
            ord_by_strategy[s_id].append(o)

        # All known strategy IDs
        all_strategy_ids: set[str] = set()
        config_by_id: dict[str, StrategyConfigModel] = {}
        prefix = f"{self.account.id}_"
        for c in configs:
            raw_id = c.id[len(prefix):] if c.id.startswith(prefix) else c.id
            all_strategy_ids.add(raw_id)
            config_by_id[raw_id] = c

        for s_id in deployments_map:
            all_strategy_ids.add(s_id)
        for s_id in pos_by_strategy:
            if s_id != "unassigned":
                all_strategy_ids.add(s_id)
        for s_id in ord_by_strategy:
            if s_id != "unassigned":
                all_strategy_ids.add(s_id)

        items: list[StrategyPortfolioItem] = []
        tot_unrealized = Decimal(0)
        tot_realized = Decimal(0)
        tot_open_pos = 0

        for s_id in sorted(all_strategy_ids):
            cfg = config_by_id.get(s_id)
            dep = deployments_map.get(s_id)
            positions = pos_by_strategy.get(s_id, [])
            orders = ord_by_strategy.get(s_id, [])

            is_active = cfg.is_active if cfg else (dep.status in ("INCUBATING", "GATES_PASSED") if dep else False)
            dep_status = dep.status if dep else ("CONFIGURED" if is_active else None)

            strat_name = (cfg.name if cfg else None) or (s_id.replace("_", " ").title())
            symbols = cfg.symbols if (cfg and cfg.symbols) else ([dep.symbol] if (dep and dep.symbol) else [])
            timeframe = (
                cfg.parameters.get("timeframe", "M15")
                if (cfg and cfg.parameters)
                else (dep.timeframe if dep else "M15")
            )

            # Calculate strategy metrics
            open_positions = [p for p in positions if p.is_open]
            closed_positions = [p for p in positions if not p.is_open]
            gross_exposure = sum((p.quantity * p.current_price for p in open_positions), Decimal(0))
            strat_unrealized = sum((p.unrealized_pnl for p in open_positions), Decimal(0))
            strat_realized = sum((p.realized_pnl for p in closed_positions), Decimal(0))

            tot_open_pos += len(open_positions)
            tot_unrealized += strat_unrealized
            tot_realized += strat_realized

            win_rate = None
            if len(closed_positions) > 0:
                winning = sum(1 for p in closed_positions if p.realized_pnl > Decimal(0))
                win_rate = round((winning / len(closed_positions)) * 100.0, 2)

            last_act = None
            if positions:
                latest_pos = max((p.updated_at or p.opened_at for p in positions if p.opened_at))
                last_act = latest_pos
            if orders:
                latest_ord = max((o.updated_at or o.created_at for o in orders if o.created_at))
                if last_act is None or latest_ord > last_act:
                    last_act = latest_ord

            items.append(
                StrategyPortfolioItem(
                    strategy_id=s_id,
                    strategy_name=strat_name,
                    is_active=is_active,
                    deployment_status=dep_status,
                    timeframe=timeframe,
                    symbols=symbols,
                    open_positions_count=len(open_positions),
                    total_orders_count=len(orders),
                    gross_exposure=gross_exposure,
                    unrealized_pnl=strat_unrealized,
                    realized_pnl=strat_realized,
                    win_rate=win_rate,
                    last_activity_at=last_act,
                )
            )

        # Include unassigned/manual bucket if any unassigned orders or positions exist
        unassigned_pos = pos_by_strategy.get("unassigned", [])
        unassigned_ord = ord_by_strategy.get("unassigned", [])
        if unassigned_pos or unassigned_ord:
            u_open = [p for p in unassigned_pos if p.is_open]
            u_closed = [p for p in unassigned_pos if not p.is_open]
            u_gross = sum((p.quantity * p.current_price for p in u_open), Decimal(0))
            u_unrealized = sum((p.unrealized_pnl for p in u_open), Decimal(0))
            u_realized = sum((p.realized_pnl for p in u_closed), Decimal(0))
            tot_open_pos += len(u_open)
            tot_unrealized += u_unrealized
            tot_realized += u_realized
            items.append(
                StrategyPortfolioItem(
                    strategy_id="manual",
                    strategy_name="Manual / Terminal Trades",
                    is_active=True,
                    deployment_status="DISCRETIONARY",
                    timeframe="N/A",
                    symbols=[],
                    open_positions_count=len(u_open),
                    total_orders_count=len(unassigned_ord),
                    gross_exposure=u_gross,
                    unrealized_pnl=u_unrealized,
                    realized_pnl=u_realized,
                    win_rate=(
                        round((sum(1 for p in u_closed if p.realized_pnl > Decimal(0)) / len(u_closed)) * 100.0, 2)
                        if u_closed
                        else None
                    ),
                    last_activity_at=None,
                )
            )

        return MultiStrategyPortfolioResponse(
            strategies=items,
            total_active_strategies=sum(
                1 for s in items if s.is_active and s.strategy_id != "manual"
            ),
            total_open_positions=tot_open_pos,
            total_unrealized_pnl=tot_unrealized,
            total_realized_pnl=tot_realized,
            currency="USD",
            is_paper=True,
            updated_at=now,
        )

