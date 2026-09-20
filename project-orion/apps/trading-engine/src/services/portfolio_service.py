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
from libraries.infrastructure.persistence.models import AccountModel, PositionModel

from ..schemas import (
    CurrencyExposure,
    EquityCurveResponse,
    ExposureResponse,
    PnLBreakdownResponse,
    PortfolioOverviewResponse,
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
