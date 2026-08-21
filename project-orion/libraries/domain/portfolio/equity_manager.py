"""Equity Manager — tracks account equity and equity changes.

Supports equity tracking across daily, weekly, monthly periods.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EquitySnapshot:
    """Immutable snapshot of equity state."""

    equity: Decimal = Decimal(0)
    balance: Decimal = Decimal(0)
    unrealized_pnl: Decimal = Decimal(0)
    daily_change: Decimal = Decimal(0)
    weekly_change: Decimal = Decimal(0)
    monthly_change: Decimal = Decimal(0)
    daily_change_pct: float = 0.0
    weekly_change_pct: float = 0.0
    monthly_change_pct: float = 0.0
    peak_equity: Decimal = Decimal(0)
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EquityManager:
    """Manages account equity tracking.

    Thread-safe via asyncio.Lock.
    Tracks equity, peak equity, and periodic changes.
    """

    def __init__(
        self,
        initial_equity: Decimal = Decimal(0),
        currency: str = "USD",
    ) -> None:
        self._lock = asyncio.Lock()
        self._equity = initial_equity
        self._balance = initial_equity
        self._peak_equity = initial_equity
        self._currency = currency

        # Periodic tracking
        self._day_start_equity = initial_equity
        self._week_start_equity = initial_equity
        self._month_start_equity = initial_equity
        self._last_reset_date = datetime.now(timezone.utc).date()

    async def get_equity(self) -> Decimal:
        """Return current equity."""
        async with self._lock:
            return self._equity

    async def get_peak_equity(self) -> Decimal:
        """Return historical peak equity."""
        async with self._lock:
            return self._peak_equity

    async def update(
        self,
        balance: Decimal,
        unrealized_pnl: Decimal = Decimal(0),
    ) -> EquitySnapshot:
        """Update equity based on balance and unrealized P&L.

        Equity = balance + unrealized_pnl

        Args:
            balance: Current account balance.
            unrealized_pnl: Current unrealized P&L.

        Returns:
            EquitySnapshot after update.
        """
        async with self._lock:
            self._check_periodic_reset()

            new_equity = balance + unrealized_pnl
            self._balance = balance
            self._equity = new_equity

            self._peak_equity = max(self._peak_equity, new_equity)

            daily_change = new_equity - self._day_start_equity
            weekly_change = new_equity - self._week_start_equity
            monthly_change = new_equity - self._month_start_equity

            daily_pct = (
                float(daily_change / self._day_start_equity * 100)
                if self._day_start_equity != 0
                else 0.0
            )
            weekly_pct = (
                float(weekly_change / self._week_start_equity * 100)
                if self._week_start_equity != 0
                else 0.0
            )
            monthly_pct = (
                float(monthly_change / self._month_start_equity * 100)
                if self._month_start_equity != 0
                else 0.0
            )

            return EquitySnapshot(
                equity=new_equity,
                balance=balance,
                unrealized_pnl=unrealized_pnl,
                daily_change=daily_change,
                weekly_change=weekly_change,
                monthly_change=monthly_change,
                daily_change_pct=round(daily_pct, 4),
                weekly_change_pct=round(weekly_pct, 4),
                monthly_change_pct=round(monthly_pct, 4),
                peak_equity=self._peak_equity,
                currency=self._currency,
            )

    async def get_snapshot(
        self,
        unrealized_pnl: Decimal = Decimal(0),
    ) -> EquitySnapshot:
        """Get current equity snapshot.

        Args:
            unrealized_pnl: Current unrealized P&L.

        Returns:
            EquitySnapshot.
        """
        async with self._lock:
            self._check_periodic_reset()
            new_equity = self._balance + unrealized_pnl

            daily_change = new_equity - self._day_start_equity
            weekly_change = new_equity - self._week_start_equity
            monthly_change = new_equity - self._month_start_equity

            daily_pct = (
                float(daily_change / self._day_start_equity * 100)
                if self._day_start_equity != 0
                else 0.0
            )
            weekly_pct = (
                float(weekly_change / self._week_start_equity * 100)
                if self._week_start_equity != 0
                else 0.0
            )
            monthly_pct = (
                float(monthly_change / self._month_start_equity * 100)
                if self._month_start_equity != 0
                else 0.0
            )

            return EquitySnapshot(
                equity=new_equity,
                balance=self._balance,
                unrealized_pnl=unrealized_pnl,
                daily_change=daily_change,
                weekly_change=weekly_change,
                monthly_change=monthly_change,
                daily_change_pct=round(daily_pct, 4),
                weekly_change_pct=round(weekly_pct, 4),
                monthly_change_pct=round(monthly_pct, 4),
                peak_equity=self._peak_equity,
                currency=self._currency,
            )

    def _check_periodic_reset(self) -> None:
        """Reset periodic tracking if a new period has started."""
        today = datetime.now(timezone.utc).date()
        if today > self._last_reset_date:
            # New day
            if today.weekday() == 0:  # Monday
                self._week_start_equity = self._equity
            if today.day == 1:  # First of month
                self._month_start_equity = self._equity

            self._day_start_equity = self._equity
            self._last_reset_date = today

    async def reset(self, equity: Decimal = Decimal(0)) -> None:
        """Reset equity manager (for testing)."""
        async with self._lock:
            self._equity = equity
            self._balance = equity
            self._peak_equity = equity
            self._day_start_equity = equity
            self._week_start_equity = equity
            self._month_start_equity = equity
            self._last_reset_date = datetime.now(timezone.utc).date()
