"""Risk management application service.

Provides real, deterministic risk evaluations, portfolio risk aggregation,
limit rule checks, and circuit-breaker states derived from the authenticated account.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.risk.models import PolicySeverity
from libraries.domain.risk.policy import create_default_policies
from libraries.domain.risk.profile import RiskProfileConfig
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter
from libraries.infrastructure.persistence.models import AccountModel, PositionModel

from ..schemas import RiskLimitsResponse, RiskStatusResponse

logger = logging.getLogger("trading_engine.services.risk")


class RiskService:
    """Enterprise risk service orchestrating risk checks and metrics calculation."""

    def __init__(
        self,
        session: AsyncSession,
        account: AccountModel,
        adapter: PaperExecutionAdapter | None = None,
        market_service: Any | None = None,
    ) -> None:
        self.session = session
        self.account = account
        self.adapter = adapter
        self.market_service = market_service

    async def get_risk_status(self) -> RiskStatusResponse:
        """Calculate real risk metrics for the authenticated account."""
        now = datetime.now(timezone.utc)

        # 1. Query open positions for the authenticated account
        pos_stmt = select(PositionModel).where(
            PositionModel.account_id == self.account.id,
            PositionModel.is_open == True,
        )
        pos_res = await self.session.execute(pos_stmt)
        open_positions = list(pos_res.scalars().all())

        # 2. Check market data and update current prices if live feed is available
        market_degraded = False
        if self.market_service is not None and open_positions:
            for p in open_positions:
                try:
                    quote = await self.market_service.get_quote(p.symbol)
                    if quote and hasattr(quote, "mid"):
                        p.current_price = Decimal(str(quote.mid))
                except Exception as exc:
                    logger.debug("Live quote unavailable for %s: %s", p.symbol, exc)
                    if p.current_price <= Decimal(0):
                        market_degraded = True

        # 3. Position and exposure calculations
        try:
            leverage = Decimal(str(self.account.leverage))
            if leverage <= Decimal(0):
                leverage = Decimal(100)
        except (InvalidOperation, TypeError, ValueError, AttributeError):
            leverage = Decimal(100)

        used_margin = Decimal(0)
        unrealized_pnl = Decimal(0)
        long_exposure = Decimal(0)
        short_exposure = Decimal(0)

        for p in open_positions:
            pos_val = p.quantity * p.current_price
            used_margin += pos_val / leverage
            if p.side.upper() == "BUY":
                long_exposure += pos_val
                unrealized_pnl += (
                    (p.current_price - p.open_price) * p.quantity - p.commission - p.swap
                )
            else:
                short_exposure += pos_val
                unrealized_pnl += (
                    (p.open_price - p.current_price) * p.quantity - p.commission - p.swap
                )

        gross_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        total_exposure = gross_exposure
        position_count = len(open_positions)

        balance = self.account.balance or Decimal(0)
        equity = balance + unrealized_pnl
        free_margin = max(equity - used_margin, Decimal(0))
        margin_level = (
            float(equity / used_margin * 100) if used_margin > Decimal(0) else 0.0
        )

        peak_equity = max(balance, equity)
        drawdown = (
            float((peak_equity - equity) / peak_equity * 100)
            if peak_equity > Decimal(0)
            else 0.0
        )

        # 4. Query closed positions for trade history loss metrics
        closed_stmt = select(PositionModel).where(
            PositionModel.account_id == self.account.id,
            PositionModel.is_open == False,
        )
        closed_res = await self.session.execute(closed_stmt)
        closed_positions = list(closed_res.scalars().all())

        realized_pnl = sum((p.realized_pnl for p in closed_positions), Decimal(0))
        daily_pnl = realized_pnl + unrealized_pnl

        # Calculate consecutive losses
        consecutive_losses = 0
        sorted_closed = sorted(
            closed_positions,
            key=lambda x: x.closed_at or x.opened_at,
            reverse=True,
        )
        for p in sorted_closed:
            if p.realized_pnl < Decimal(0):
                consecutive_losses += 1
            else:
                break

        daily_loss_rate = (
            float(abs(daily_pnl) / balance * 100)
            if (daily_pnl < Decimal(0) and balance > Decimal(0))
            else 0.0
        )

        # 5. Circuit breaker & risk policy evaluation against institutional thresholds
        cfg = RiskProfileConfig.balanced()
        emergency_stop_active = False
        recovery_mode_active = False

        if drawdown >= cfg.hard_stop_loss_pct or daily_loss_rate >= cfg.max_daily_loss_pct:
            emergency_stop_active = True
        elif (
            drawdown >= cfg.soft_stop_loss_pct
            or consecutive_losses >= cfg.max_consecutive_losses
            or (margin_level > 0 and margin_level <= cfg.margin_call_threshold_pct)
        ):
            recovery_mode_active = True

        if emergency_stop_active:
            status_str = "critical"
            circuit_breaker_state = "TRIGGERED"
        elif recovery_mode_active:
            status_str = "warning"
            circuit_breaker_state = "RECOVERY"
        elif market_degraded:
            status_str = "degraded"
            circuit_breaker_state = "NORMAL"
        else:
            status_str = "healthy"
            circuit_breaker_state = "NORMAL"

        return RiskStatusResponse(
            status=status_str,
            position_count=position_count,
            total_exposure=total_exposure,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            used_margin=used_margin,
            free_margin=free_margin,
            margin_level=round(margin_level, 2),
            drawdown=round(drawdown, 2),
            daily_pnl=daily_pnl,
            unrealized_pnl=unrealized_pnl,
            daily_loss_rate=round(daily_loss_rate, 2),
            consecutive_losses=consecutive_losses,
            emergency_stop_active=emergency_stop_active,
            recovery_mode_active=recovery_mode_active,
            circuit_breaker_state=circuit_breaker_state,
            updated_at=now,
        )

    async def get_risk_limits(self) -> RiskLimitsResponse:
        """Return institutional risk policies and limit thresholds from domain source of truth."""
        cfg = RiskProfileConfig.balanced()
        policies = create_default_policies(cfg)

        threshold_map: dict[str, Any] = {
            "maximum_position_size": f"{cfg.max_position_size_pct}% equity",
            "maximum_daily_loss": f"{cfg.max_daily_loss_pct}% equity",
            "maximum_weekly_loss": f"{cfg.max_weekly_loss_pct}% equity",
            "maximum_monthly_loss": f"{cfg.max_monthly_loss_pct}% equity",
            "maximum_drawdown": f"{cfg.max_drawdown_pct}% peak",
            "maximum_consecutive_losses": cfg.max_consecutive_losses,
            "maximum_exposure": f"{cfg.max_total_exposure_pct}% capital",
            "maximum_symbol_exposure": f"{cfg.max_symbol_exposure_pct}% capital",
            "maximum_currency_exposure": f"{cfg.max_currency_exposure_pct}% capital",
            "maximum_leverage": f"{cfg.max_leverage}:1",
            "maximum_open_positions": cfg.max_open_positions,
            "margin_protection": f"{cfg.margin_call_threshold_pct}% min margin level",
            "spread_protection": f"{cfg.max_spread_pips} pips max",
            "volatility_protection": f"{cfg.max_volatility} normalized sigma",
            "liquidity_protection": f"{cfg.min_liquidity_score} min score",
            "slippage_protection": f"{cfg.max_slippage_pips} pips max",
            "news_protection": "Active Pre/Post Event",
            "trading_hours_protection": "Active (Market Open Required)",
            "weekend_protection": "Enforced (No Weekend Holds)",
            "holiday_protection": "Enforced (Calendar Synchronized)",
            "soft_stop": f"{cfg.soft_stop_loss_pct}% soft threshold",
            "hard_stop": f"{cfg.hard_stop_loss_pct}% hard stop liquidation",
            "trading_lock": "Active on Risk Breach",
            "cooldown_timer": f"{cfg.cooldown_after_loss_minutes} min cooldown",
            "recovery_mode": "Active",
            "broker_health_protection": "Active (Latency/Heartbeat)",
            "market_data_quality_protection": "Active (Staleness/Spike Guard)",
            "emergency_stop": "Active (Auto Circuit Breaker)",
        }

        limits = []
        for p in policies:
            sev = (
                p.severity.name.lower()
                if hasattr(p.severity, "name")
                else "critical" if p.severity >= PolicySeverity.CRITICAL else "warning"
            )
            cat = p.category.value if hasattr(p.category, "value") else str(p.category)
            limits.append(
                {
                    "name": p.name,
                    "category": cat,
                    "description": p.description,
                    "is_enabled": p.enabled,
                    "severity": sev,
                    "value": threshold_map.get(p.name, "Active"),
                }
            )

        return RiskLimitsResponse(
            limits=limits,
            total=len(limits),
            updated_at=datetime.now(timezone.utc),
        )
