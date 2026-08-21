"""Balance Manager — tracks account balance and available funds.

Supports:
- Balance tracking
- Buying power calculation
- Available funds calculation
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BalanceSnapshot:
    """Immutable snapshot of account balance state."""

    balance: Decimal = Decimal(0)
    previous_balance: Decimal = Decimal(0)
    change: Decimal = Decimal(0)
    change_pct: float = 0.0
    buying_power: Decimal = Decimal(0)
    available_funds: Decimal = Decimal(0)
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def has_changed(self) -> bool:
        return self.change != 0


class BalanceManager:
    """Manages account balance.

    Thread-safe via asyncio.Lock.
    Tracks balance, buying power, and available funds.
    """

    def __init__(
        self,
        initial_balance: Decimal = Decimal(0),
        currency: str = "USD",
        max_leverage: Decimal = Decimal(100),
    ) -> None:
        self._lock = asyncio.Lock()
        self._balance = initial_balance
        self._previous_balance = initial_balance
        self._currency = currency
        self._max_leverage = max_leverage
        self._reserved_funds: Decimal = Decimal(0)

    @property
    def balance(self) -> Decimal:
        """Current account balance (thread-safe read)."""
        return self._balance

    @property
    def currency(self) -> str:
        return self._currency

    async def get_balance(self) -> Decimal:
        """Return current account balance."""
        async with self._lock:
            return self._balance

    async def get_previous_balance(self) -> Decimal:
        """Return previous balance before last change."""
        async with self._lock:
            return self._previous_balance

    async def get_buying_power(
        self,
        used_margin: Decimal = Decimal(0),
        equity: Decimal | None = None,
    ) -> Decimal:
        """Calculate available buying power.

        Buying power = max(0, equity * max_leverage - used_margin)

        Args:
            used_margin: Currently used margin.
            equity: Current equity (if None, uses balance).

        Returns:
            Available buying power.
        """
        async with self._lock:
            eq = equity if equity is not None else self._balance
            max_power = eq * self._max_leverage
            return max(Decimal(0), max_power - used_margin)

    async def get_available_funds(
        self,
        used_margin: Decimal = Decimal(0),
        equity: Decimal | None = None,
    ) -> Decimal:
        """Calculate available funds (free margin).

        Available funds = equity - used_margin - reserved_funds

        Args:
            used_margin: Currently used margin.
            equity: Current equity (if None, uses balance).

        Returns:
            Available funds.
        """
        async with self._lock:
            eq = equity if equity is not None else self._balance
            return max(Decimal(0), eq - used_margin - self._reserved_funds)

    async def deposit(self, amount: Decimal, reason: str = "") -> BalanceSnapshot:
        """Deposit funds into the account.

        Args:
            amount: Amount to deposit (positive).
            reason: Reason for deposit.

        Returns:
            BalanceSnapshot after deposit.

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError("Deposit amount must be positive")
        async with self._lock:
            self._previous_balance = self._balance
            self._balance += amount
            change = self._balance - self._previous_balance
            change_pct = (
                float(change / self._previous_balance * 100) if self._previous_balance != 0 else 0.0
            )
            return BalanceSnapshot(
                balance=self._balance,
                previous_balance=self._previous_balance,
                change=change,
                change_pct=round(change_pct, 4),
                currency=self._currency,
            )

    async def withdraw(self, amount: Decimal, reason: str = "") -> BalanceSnapshot:
        """Withdraw funds from the account.

        Args:
            amount: Amount to withdraw (positive).
            reason: Reason for withdrawal.

        Returns:
            BalanceSnapshot after withdrawal.

        Raises:
            ValueError: If amount exceeds balance or is negative.
        """
        if amount < 0:
            raise ValueError("Withdrawal amount must be positive")
        async with self._lock:
            if amount > self._balance:
                raise ValueError(f"Insufficient balance: {amount} > {self._balance}")
            self._previous_balance = self._balance
            self._balance -= amount
            change = self._balance - self._previous_balance
            change_pct = (
                float(change / self._previous_balance * 100) if self._previous_balance != 0 else 0.0
            )
            return BalanceSnapshot(
                balance=self._balance,
                previous_balance=self._previous_balance,
                change=change,
                change_pct=round(change_pct, 4),
                currency=self._currency,
            )

    async def update_balance(
        self,
        new_balance: Decimal,
        reason: str = "",
    ) -> BalanceSnapshot:
        """Directly update the balance (e.g., from P&L settlement).

        Args:
            new_balance: New balance value.
            reason: Reason for update.

        Returns:
            BalanceSnapshot after update.
        """
        async with self._lock:
            self._previous_balance = self._balance
            change = new_balance - self._balance
            change_pct = (
                float(change / self._previous_balance * 100) if self._previous_balance != 0 else 0.0
            )
            self._balance = new_balance
            return BalanceSnapshot(
                balance=self._balance,
                previous_balance=self._previous_balance,
                change=change,
                change_pct=round(change_pct, 4),
                currency=self._currency,
            )

    async def reserve_funds(self, amount: Decimal) -> None:
        """Reserve funds (reduce available funds for pending orders).

        Args:
            amount: Amount to reserve.
        """
        async with self._lock:
            self._reserved_funds += amount

    async def release_funds(self, amount: Decimal) -> None:
        """Release previously reserved funds.

        Args:
            amount: Amount to release.
        """
        async with self._lock:
            self._reserved_funds = max(Decimal(0), self._reserved_funds - amount)

    async def get_snapshot(
        self,
        used_margin: Decimal = Decimal(0),
        equity: Decimal | None = None,
    ) -> BalanceSnapshot:
        """Get current balance snapshot.

        Args:
            used_margin: Currently used margin.
            equity: Current equity.

        Returns:
            BalanceSnapshot.
        """
        async with self._lock:
            eq = equity if equity is not None else self._balance
            buying_power = max(Decimal(0), eq * self._max_leverage - used_margin)
            available = max(Decimal(0), eq - used_margin - self._reserved_funds)
            change = self._balance - self._previous_balance
            change_pct = (
                float(change / self._previous_balance * 100) if self._previous_balance != 0 else 0.0
            )

            return BalanceSnapshot(
                balance=self._balance,
                previous_balance=self._previous_balance,
                change=change,
                change_pct=round(change_pct, 4),
                buying_power=buying_power,
                available_funds=available,
                currency=self._currency,
            )

    async def reset(self, balance: Decimal = Decimal(0)) -> None:
        """Reset balance manager (for testing)."""
        async with self._lock:
            self._balance = balance
            self._previous_balance = balance
            self._reserved_funds = Decimal(0)
