"""Portfolio Manager — primary facade for portfolio and position management.

Integrates all sub-managers into a single composable unit.
Supports dependency injection of all components.

Responsible for:
- Position management (open, close, modify)
- Balance tracking
- Equity tracking
- Margin management
- Exposure tracking
- Trade journaling
- Portfolio analytics
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.portfolio.analytics import PortfolioAnalytics, PortfolioAnalyticsEngine
from libraries.domain.portfolio.balance_manager import BalanceManager
from libraries.domain.portfolio.equity_manager import EquityManager
from libraries.domain.portfolio.exceptions import (
    DuplicatePositionError,
    InvalidPositionStateError,
    PositionNotFoundError,
    PositionSizeError,
)
from libraries.domain.portfolio.exposure_manager import ExposureManager
from libraries.domain.portfolio.journal import JournalEntryType, TradeJournal
from libraries.domain.portfolio.margin_manager import MarginManager
from libraries.domain.portfolio.models import (
    AccountSnapshot,
    DrawdownSnapshot,
    MarginCallThresholds,
    PnLBreakdown,
    PortfolioSnapshot,
    Position,
    PositionSide,
    PositionStatus,
    PositionSummary,
)
from libraries.domain.portfolio.position_manager import PositionManager


@dataclass(frozen=True, slots=True)
class PortfolioManagerConfig:
    """Configuration for the PortfolioManager."""

    initial_balance: Decimal = Decimal("10000")
    initial_equity: Decimal = Decimal("10000")
    max_leverage: Decimal = Decimal("100")
    account_currency: str = "USD"
    margin_call_level: float = 100.0
    stop_out_level: float = 50.0
    track_journal: bool = True
    track_analytics: bool = True


class PortfolioManager:
    """Primary facade for portfolio and position management.

    Integrates:
    - PositionManager
    - BalanceManager
    - EquityManager
    - MarginManager
    - ExposureManager
    - TradeJournal
    - PortfolioAnalyticsEngine

    Thread-safe via asyncio.Lock on the PortfolioManager level.
    All methods return immutable data objects.
    """

    def __init__(
        self,
        config: PortfolioManagerConfig | None = None,
        position_manager: PositionManager | None = None,
        balance_manager: BalanceManager | None = None,
        equity_manager: EquityManager | None = None,
        margin_manager: MarginManager | None = None,
        exposure_manager: ExposureManager | None = None,
        journal: TradeJournal | None = None,
        analytics: PortfolioAnalyticsEngine | None = None,
    ) -> None:
        self._config = config or PortfolioManagerConfig()
        self._lock = asyncio.Lock()

        # Sub-managers
        self._position_manager = position_manager or PositionManager()
        self._balance_manager = balance_manager or BalanceManager(
            initial_balance=self._config.initial_balance,
            currency=self._config.account_currency,
            max_leverage=self._config.max_leverage,
        )
        self._equity_manager = equity_manager or EquityManager(
            initial_equity=self._config.initial_balance,
            currency=self._config.account_currency,
        )
        self._margin_manager = margin_manager or MarginManager(
            thresholds=MarginCallThresholds(
                margin_call_level=self._config.margin_call_level,
                stop_out_level=self._config.stop_out_level,
            ),
            currency=self._config.account_currency,
        )
        self._exposure_manager = exposure_manager or ExposureManager()
        self._journal = journal or TradeJournal()
        self._analytics = analytics or PortfolioAnalyticsEngine()

    # ─── Properties ──────────────────────────────────────────

    @property
    def config(self) -> PortfolioManagerConfig:
        return self._config

    @property
    def position_manager(self) -> PositionManager:
        return self._position_manager

    @property
    def balance_manager(self) -> BalanceManager:
        return self._balance_manager

    @property
    def equity_manager(self) -> EquityManager:
        return self._equity_manager

    @property
    def margin_manager(self) -> MarginManager:
        return self._margin_manager

    @property
    def exposure_manager(self) -> ExposureManager:
        return self._exposure_manager

    @property
    def journal(self) -> TradeJournal:
        return self._journal

    @property
    def analytics(self) -> PortfolioAnalyticsEngine:
        return self._analytics

    # ─── Position Operations ─────────────────────────────────

    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: Decimal,
        entry_price: Decimal,
        *,
        position_id: str | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        decision_id: str = "",
        execution_id: str = "",
        strategy: str = "",
        currency: str = "USD",
        broker: str = "",
        leverage: Decimal = Decimal("1"),
        commission: Decimal = Decimal("0"),
        swap: Decimal = Decimal("0"),
        fees: Decimal = Decimal("0"),
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Open a new position with full portfolio integration.

        Updates: positions, exposure, margin, equity, journal, analytics.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            quantity: Position size.
            entry_price: Entry price.
            position_id: Optional custom position ID.
            stop_loss: Optional stop loss.
            take_profit: Optional take profit.
            decision_id: Decision ID.
            execution_id: Execution ID.
            strategy: Strategy name.
            currency: Position currency.
            broker: Broker name.
            leverage: Leverage multiplier.
            commission: Commission.
            swap: Swap.
            fees: Fees.
            tags: Position tags.
            metadata: Additional metadata.

        Returns:
            The newly created Position.
        """
        notional_value = entry_price * quantity

        # Calculate margin
        required_margin = await self._margin_manager.calculate_required_margin(
            notional_value=notional_value,
            leverage=leverage,
        )

        position = await self._position_manager.open_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            position_id=position_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
            decision_id=decision_id,
            execution_id=execution_id,
            strategy=strategy,
            currency=currency,
            broker=broker,
            leverage=leverage,
            commission=commission,
            swap=swap,
            fees=fees,
            margin_used=required_margin,
            tags=tags,
            metadata=metadata,
        )

        # Update exposure
        await self._exposure_manager.add_exposure(
            symbol=symbol,
            side=side,
            notional_value=notional_value,
            currency=currency,
        )

        # Register margin
        await self._margin_manager.register_position_margin(
            position_id=position.position_id,
            margin=required_margin,
        )

        # Update equity
        balance = await self._balance_manager.get_balance()
        await self._equity_manager.update(
            balance=balance,
            unrealized_pnl=Decimal("0"),
        )

        # Journal
        if self._config.track_journal:
            await self._journal.record(
                entry_type=JournalEntryType.POSITION_OPENED,
                position_id=position.position_id,
                symbol=symbol,
                side=side.value,
                quantity=quantity,
                price=entry_price,
                commission=commission,
                swap=swap,
                fees=fees,
                strategy=strategy,
                decision_id=decision_id,
                execution_id=execution_id,
                tags=tags,
                details={"leverage": str(leverage), "margin": str(required_margin)},
            )

        return position

    async def close_position(
        self,
        position_id: str,
        close_price: Decimal,
        close_reason: str = "",
        *,
        commission: Decimal = Decimal("0"),
        swap: Decimal = Decimal("0"),
        fees: Decimal = Decimal("0"),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Close a position with full portfolio integration.

        Updates: positions, balance, exposure, margin, equity, journal, analytics.

        Returns:
            Closed Position.
        """
        position = await self._position_manager.close_position(
            position_id=position_id,
            close_price=close_price,
            close_reason=close_reason,
            commission=commission,
            swap=swap,
            fees=fees,
            metadata=metadata,
        )

        # Update balance with realized P&L
        pnl = position.realized_pnl
        if pnl != 0:
            new_balance = (await self._balance_manager.get_balance()) + (
                pnl - commission - swap - fees
            )
            await self._balance_manager.update_balance(new_balance)

        # Remove exposure
        notional_value = position.initial_quantity * position.entry_price
        await self._exposure_manager.remove_exposure(
            symbol=position.symbol,
            side=position.side,
            notional_value=notional_value,
            currency=position.currency,
        )

        # Unregister margin
        await self._margin_manager.unregister_position_margin(position_id)

        # Update equity — must account for remaining open positions' unrealized P&L
        balance = await self._balance_manager.get_balance()
        all_open = await self._position_manager.get_open_positions()
        total_unrealized = sum(p.unrealized_pnl for p in all_open)
        await self._equity_manager.update(
            balance=balance,
            unrealized_pnl=total_unrealized,
        )

        # Journal
        if self._config.track_journal:
            entry_type = (
                JournalEntryType.TRADE_PROFIT
                if pnl > 0
                else JournalEntryType.TRADE_LOSS if pnl < 0 else JournalEntryType.POSITION_CLOSED
            )
            await self._journal.record(
                entry_type=entry_type,
                position_id=position_id,
                symbol=position.symbol,
                side=position.side.value,
                quantity=position.initial_quantity,
                price=close_price,
                pnl=pnl,
                commission=commission,
                swap=swap,
                fees=fees,
                balance=balance,
                reason=close_reason,
                strategy=position.strategy,
                decision_id=position.decision_id,
                execution_id=position.execution_id,
            )

        # Analytics
        if self._config.track_analytics:
            is_win = pnl > 0
            is_loss = pnl < 0
            await self._analytics.record_trade(
                pnl=float(pnl),
                is_win=is_win,
                is_loss=is_loss,
            )

        return position

    async def partially_close_position(
        self,
        position_id: str,
        close_quantity: Decimal,
        close_price: Decimal,
        close_reason: str = "",
        *,
        commission: Decimal = Decimal("0"),
        swap: Decimal = Decimal("0"),
        fees: Decimal = Decimal("0"),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Partially close a position with portfolio integration."""
        position = await self._position_manager.partially_close_position(
            position_id=position_id,
            close_quantity=close_quantity,
            close_price=close_price,
            close_reason=close_reason,
            commission=commission,
            swap=swap,
            fees=fees,
            metadata=metadata,
        )

        # Update exposure
        partial_notional = close_quantity * position.entry_price
        await self._exposure_manager.remove_exposure(
            symbol=position.symbol,
            side=position.side,
            notional_value=partial_notional,
            currency=position.currency,
        )

        # Update equity — account for remaining unrealized P&L on the position
        balance = await self._balance_manager.get_balance()
        all_open = await self._position_manager.get_open_positions()
        total_unrealized = sum(p.unrealized_pnl for p in all_open)
        await self._equity_manager.update(
            balance=balance,
            unrealized_pnl=total_unrealized,
        )

        # Journal
        if self._config.track_journal:
            await self._journal.record(
                entry_type=JournalEntryType.POSITION_MODIFIED,
                position_id=position_id,
                symbol=position.symbol,
                side=position.side.value,
                quantity=close_quantity,
                price=close_price,
                commission=commission,
                swap=swap,
                fees=fees,
                reason=close_reason,
            )

        return position

    async def increase_position(
        self,
        position_id: str,
        additional_quantity: Decimal,
        entry_price: Decimal,
        *,
        commission: Decimal = Decimal("0"),
        swap: Decimal = Decimal("0"),
        fees: Decimal = Decimal("0"),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Increase position size with exposure and journal updates."""
        position = await self._position_manager.increase_position(
            position_id=position_id,
            additional_quantity=additional_quantity,
            entry_price=entry_price,
            commission=commission,
            swap=swap,
            fees=fees,
            metadata=metadata,
        )

        # Update exposure
        additional_notional = additional_quantity * entry_price
        await self._exposure_manager.add_exposure(
            symbol=position.symbol,
            side=position.side,
            notional_value=additional_notional,
            currency=position.currency,
        )

        if self._config.track_journal:
            await self._journal.record(
                entry_type=JournalEntryType.POSITION_MODIFIED,
                position_id=position_id,
                symbol=position.symbol,
                side=position.side.value,
                quantity=additional_quantity,
                price=entry_price,
                reason="position_increased",
            )

        return position

    # ─── Account Operations ──────────────────────────────────

    async def deposit(self, amount: Decimal, reason: str = "") -> AccountSnapshot:
        """Deposit funds.

        Args:
            amount: Amount to deposit.
            reason: Reason for deposit.

        Returns:
            AccountSnapshot.
        """
        snap = await self._balance_manager.deposit(amount, reason)
        await self._equity_manager.update(balance=snap.balance)
        return await self.get_account_snapshot()

    async def withdraw(self, amount: Decimal, reason: str = "") -> AccountSnapshot:
        """Withdraw funds.

        Args:
            amount: Amount to withdraw.
            reason: Reason for withdrawal.

        Returns:
            AccountSnapshot.
        """
        snap = await self._balance_manager.withdraw(amount, reason)
        await self._equity_manager.update(balance=snap.balance)
        return await self.get_account_snapshot()

    # ─── Price Updates ───────────────────────────────────────

    async def update_price(self, symbol: str, price: Decimal) -> list[Position]:
        """Update current price for all positions of a symbol.

        This updates unrealized P&L for open positions.

        Args:
            symbol: Trading symbol.
            price: Current market price.

        Returns:
            List of updated positions.
        """
        positions = await self._position_manager.get_positions_by_symbol(symbol)
        updated: list[Position] = []
        for pos in positions:
            if pos.is_active:
                updated_pos = await self._position_manager.update_position_price(
                    position_id=pos.position_id,
                    current_price=price,
                )
                updated.append(updated_pos)

        # Always update equity with ALL open positions' unrealized P&L
        balance = await self._balance_manager.get_balance()
        all_open = await self._position_manager.get_open_positions()
        total_unrealized = sum(p.unrealized_pnl for p in all_open)
        await self._equity_manager.update(
            balance=balance,
            unrealized_pnl=total_unrealized,
        )

        return updated

    # ─── Snapshot Queries ────────────────────────────────────

    async def get_portfolio_snapshot(self) -> PortfolioSnapshot:
        """Get complete portfolio snapshot."""
        account = await self.get_account_snapshot()
        all_positions = await self._position_manager.get_all_positions()
        open_positions = await self._position_manager.get_open_positions()
        closed_positions = await self._position_manager.get_closed_positions()

        total_realized = sum(p.realized_pnl for p in all_positions)
        total_unrealized = sum(p.unrealized_pnl for p in all_positions)
        total_commission = sum(p.commission for p in all_positions)
        total_swap = sum(p.swap for p in all_positions)
        total_fees = sum(p.fees for p in all_positions)

        exposure = await self._exposure_manager.get_snapshot()

        return PortfolioSnapshot(
            account=account,
            positions=tuple(all_positions),
            open_positions=tuple(open_positions),
            closed_positions=tuple(closed_positions),
            total_realized_pnl=total_realized,
            total_unrealized_pnl=total_unrealized,
            total_commission=total_commission,
            total_swap=total_swap,
            total_fees=total_fees,
            net_exposure=exposure.net_exposure,
            gross_exposure=exposure.gross_exposure,
            long_exposure=exposure.long_exposure,
            short_exposure=exposure.short_exposure,
            position_count=len(all_positions),
            open_position_count=len(open_positions),
            currency_exposures=exposure.currency_exposures,
        )

    async def get_account_snapshot(self) -> AccountSnapshot:
        """Get current account snapshot."""
        async with self._lock:
            balance = await self._balance_manager.get_balance()
            equity = await self._equity_manager.get_equity()
            used_margin = await self._margin_manager.get_used_margin()
            free_margin = await self._margin_manager.get_free_margin(equity)
            margin_level = await self._margin_manager.get_margin_level(equity)
            buying_power = await self._balance_manager.get_buying_power(
                used_margin=used_margin,
                equity=equity,
            )
            available = await self._balance_manager.get_available_funds(
                used_margin=used_margin,
                equity=equity,
            )

            # Calculate effective leverage
            exposure = await self._exposure_manager.get_gross_exposure()
            leverage = float(exposure / equity) if equity > 0 else 0.0

            return AccountSnapshot(
                balance=balance,
                equity=equity,
                free_margin=free_margin,
                used_margin=used_margin,
                margin_level=(
                    round(margin_level, 2) if margin_level != float("inf") else float("inf")
                ),
                available_funds=available,
                buying_power=buying_power,
                leverage=round(leverage, 2),
                currency=self._config.account_currency,
            )

    async def get_account_summary(self) -> dict[str, Any]:
        """Get a human-readable account summary.

        Returns:
            Dictionary with key account metrics.
        """
        account = await self.get_account_snapshot()
        return {
            "balance": float(account.balance),
            "equity": float(account.equity),
            "free_margin": float(account.free_margin),
            "used_margin": float(account.used_margin),
            "margin_level": account.margin_level,
            "margin_utilization_pct": account.margin_utilization_pct,
            "buying_power": float(account.buying_power),
            "leverage": account.leverage,
            "is_margin_call": account.is_margin_call,
            "is_stop_out": account.is_stop_out,
            "currency": account.currency,
        }

    async def get_drawdown(self) -> DrawdownSnapshot:
        """Get drawdown snapshot.

        Returns:
            DrawdownSnapshot.
        """
        equity = await self._equity_manager.get_equity()
        peak = await self._equity_manager.get_peak_equity()
        current_dd = float((peak - equity) / peak * 100) if peak > 0 else 0.0
        max_dd = await self._analytics.get_max_drawdown()
        total_pnl = float(equity - self._config.initial_balance)
        recovery = total_pnl / max_dd if max_dd > 0 else 0.0

        return DrawdownSnapshot(
            current_drawdown=round(abs(current_dd), 2),
            max_drawdown=round(max_dd, 2),
            peak_equity=peak,
            current_equity=equity,
            recovery_factor=round(recovery, 4),
        )

    async def get_pnl_breakdown(self) -> PnLBreakdown:
        """Get P&L breakdown.

        Returns:
            PnLBreakdown.
        """
        all_positions = await self._position_manager.get_all_positions()
        open_positions = await self._position_manager.get_open_positions()

        realized = sum(p.realized_pnl for p in all_positions)
        unrealized = sum(p.unrealized_pnl for p in open_positions)
        commission = sum(p.commission for p in all_positions)
        swap = sum(p.swap for p in all_positions)
        fees = sum(p.fees for p in all_positions)

        wins = [p.realized_pnl for p in all_positions if p.realized_pnl > 0]
        losses = [p.realized_pnl for p in all_positions if p.realized_pnl < 0]

        return PnLBreakdown(
            realized_pnl=realized,
            unrealized_pnl=unrealized,
            floating_pnl=unrealized,
            gross_profit=sum(wins) if wins else Decimal("0"),
            gross_loss=sum(losses) if losses else Decimal("0"),
            commission=commission,
            swap=swap,
            fees=fees,
            total_charges=commission + swap + fees,
        )

    async def get_portfolio_analytics(self) -> PortfolioAnalytics:
        """Get portfolio analytics.

        Returns:
            PortfolioAnalytics.
        """
        portfolio_heat = await self.calculate_portfolio_heat()
        return await self._analytics.calculate(portfolio_heat=portfolio_heat)

    async def calculate_portfolio_heat(self) -> float:
        """Calculate portfolio heat (0-100).

        Portfolio heat is a composite measure of:
        - Margin utilization
        - Position concentration
        - Exposure relative to account

        Returns:
            Heat score 0-100.
        """
        account = await self.get_account_snapshot()
        positions = await self._position_manager.get_open_positions()
        total_positions = await self._position_manager.total_count

        if account.equity == 0 or total_positions == 0:
            return 0.0

        # Margin utilization component (0-40)
        margin_heat = min(40.0, account.margin_utilization_pct * 0.4)

        # Position concentration heat (0-30)
        open_count = len(positions)
        concentration_heat = min(30.0, open_count * 5.0)

        # Exposure heat (0-30)
        exposure = await self._exposure_manager.get_gross_exposure()
        exposure_ratio = float(exposure / account.equity) if account.equity > 0 else 0.0
        exposure_heat = min(30.0, exposure_ratio * 0.3)

        return min(100.0, margin_heat + concentration_heat + exposure_heat)

    # ─── Cleanup ─────────────────────────────────────────────

    async def clear_all(self) -> None:
        """Clear all portfolio state (for testing)."""
        async with self._lock:
            await self._position_manager.clear_all()
            await self._balance_manager.reset(self._config.initial_balance)
            await self._equity_manager.reset(self._config.initial_equity)
            await self._margin_manager.reset()
            await self._exposure_manager.clear_all()
            await self._journal.clear()
            await self._analytics.clear()
