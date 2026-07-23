"""Tests for BalanceManager — balance tracking and operations.

Covers:
- Deposit, Withdraw, Insufficient balance
- Multiple deposits, Concurrent updates
- Buying power, Available funds, Reserved funds
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.balance_manager import BalanceManager


@pytest.fixture
async def manager() -> BalanceManager:
    """Create a clean BalanceManager for each test."""
    m = BalanceManager(
        initial_balance=Decimal("10000"), currency="USD", max_leverage=Decimal("100")
    )
    yield m
    await m.reset()


class TestInitialState:
    """Initial state scenarios."""

    async def test_initial_balance(self, manager: BalanceManager):
        assert await manager.get_balance() == Decimal("10000")
        assert manager.balance == Decimal("10000")
        assert manager.currency == "USD"

    async def test_initial_previous_balance(self, manager: BalanceManager):
        assert await manager.get_previous_balance() == Decimal("10000")

    async def test_initial_buying_power(self, manager: BalanceManager):
        bp = await manager.get_buying_power()
        assert bp == Decimal("1000000")  # 10000 * 100

    async def test_initial_available_funds(self, manager: BalanceManager):
        af = await manager.get_available_funds()
        assert af == Decimal("10000")


class TestDeposit:
    """Deposit scenarios."""

    async def test_deposit_funds(self, manager: BalanceManager):
        snap = await manager.deposit(Decimal("5000"), reason="deposit")
        assert snap.balance == Decimal("15000")
        assert snap.previous_balance == Decimal("10000")
        assert snap.change == Decimal("5000")
        assert snap.change_pct == 50.0
        assert snap.currency == "USD"
        assert snap.has_changed

    async def test_multiple_deposits(self, manager: BalanceManager):
        await manager.deposit(Decimal("1000"))
        await manager.deposit(Decimal("2000"))
        await manager.deposit(Decimal("3000"))
        assert await manager.get_balance() == Decimal("16000")

    async def test_deposit_zero(self, manager: BalanceManager):
        snap = await manager.deposit(Decimal("0"))
        assert snap.balance == Decimal("10000")
        assert not snap.has_changed

    async def test_deposit_negative_raises(self, manager: BalanceManager):
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            await manager.deposit(Decimal("-100"))


class TestWithdraw:
    """Withdrawal scenarios."""

    async def test_withdraw_funds(self, manager: BalanceManager):
        snap = await manager.withdraw(Decimal("3000"), reason="withdrawal")
        assert snap.balance == Decimal("7000")
        assert snap.previous_balance == Decimal("10000")
        assert snap.change == Decimal("-3000")
        assert snap.has_changed

    async def test_withdraw_full_balance(self, manager: BalanceManager):
        snap = await manager.withdraw(Decimal("10000"))
        assert snap.balance == Decimal("0")

    async def test_insufficient_balance(self, manager: BalanceManager):
        with pytest.raises(ValueError, match="Insufficient balance"):
            await manager.withdraw(Decimal("20000"))

    async def test_withdraw_negative_raises(self, manager: BalanceManager):
        with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
            await manager.withdraw(Decimal("-100"))

    async def test_withdraw_zero(self, manager: BalanceManager):
        snap = await manager.withdraw(Decimal("0"))
        assert snap.balance == Decimal("10000")

    async def test_multiple_withdrawals(self, manager: BalanceManager):
        await manager.withdraw(Decimal("1000"))
        await manager.withdraw(Decimal("2000"))
        await manager.withdraw(Decimal("3000"))
        assert await manager.get_balance() == Decimal("4000")


class TestBuyingPower:
    """Buying power scenarios."""

    async def test_buying_power_no_margin(self, manager: BalanceManager):
        bp = await manager.get_buying_power(used_margin=Decimal("0"))
        assert bp == Decimal("1000000")  # 10000 * 100

    async def test_buying_power_with_margin(self, manager: BalanceManager):
        bp = await manager.get_buying_power(used_margin=Decimal("2000"))
        assert bp == Decimal("998000")  # 1000000 - 2000

    async def test_buying_power_with_equity(self, manager: BalanceManager):
        bp = await manager.get_buying_power(used_margin=Decimal("0"), equity=Decimal("20000"))
        assert bp == Decimal("2000000")  # 20000 * 100

    async def test_buying_power_exceeds_margin(self, manager: BalanceManager):
        bp = await manager.get_buying_power(used_margin=Decimal("2000000"))
        assert bp == Decimal("0")

    async def test_buying_power_negative(self, manager: BalanceManager):
        bp = await manager.get_buying_power(used_margin=Decimal("10000000"))
        assert bp == Decimal("0")


class TestAvailableFunds:
    """Available funds scenarios."""

    async def test_available_funds_basic(self, manager: BalanceManager):
        af = await manager.get_available_funds(used_margin=Decimal("2000"))
        assert af == Decimal("8000")

    async def test_available_funds_with_equity(self, manager: BalanceManager):
        af = await manager.get_available_funds(
            used_margin=Decimal("2000"),
            equity=Decimal("15000"),
        )
        assert af == Decimal("13000")

    async def test_available_funds_negative(self, manager: BalanceManager):
        af = await manager.get_available_funds(used_margin=Decimal("20000"))
        assert af == Decimal("0")


class TestReservedFunds:
    """Reserved funds scenarios."""

    async def test_reserve_funds(self, manager: BalanceManager):
        await manager.reserve_funds(Decimal("2000"))
        af = await manager.get_available_funds()
        assert af == Decimal("8000")

    async def test_release_funds(self, manager: BalanceManager):
        await manager.reserve_funds(Decimal("5000"))
        await manager.release_funds(Decimal("3000"))
        af = await manager.get_available_funds()
        assert af == Decimal("8000")

    async def test_release_beyond_reserved(self, manager: BalanceManager):
        await manager.reserve_funds(Decimal("1000"))
        await manager.release_funds(Decimal("5000"))
        af = await manager.get_available_funds()
        assert af == Decimal("10000")

    async def test_reserve_multiple(self, manager: BalanceManager):
        await manager.reserve_funds(Decimal("1000"))
        await manager.reserve_funds(Decimal("2000"))
        af = await manager.get_available_funds()
        assert af == Decimal("7000")


class TestUpdateBalance:
    """Direct balance update scenarios."""

    async def test_direct_update(self, manager: BalanceManager):
        snap = await manager.update_balance(Decimal("15000"), reason="pnl_settlement")
        assert snap.balance == Decimal("15000")
        assert snap.change == Decimal("5000")

    async def test_direct_update_lower(self, manager: BalanceManager):
        snap = await manager.update_balance(Decimal("5000"))
        assert snap.balance == Decimal("5000")
        assert snap.change == Decimal("-5000")


class TestSnapshot:
    """Balance snapshot scenarios."""

    async def test_get_snapshot(self, manager: BalanceManager):
        snap = await manager.get_snapshot(used_margin=Decimal("2000"), equity=Decimal("15000"))
        assert snap.balance == Decimal("10000")
        # buying_power = max(0, equity * max_leverage - used_margin)
        # = max(0, 15000 * 100 - 2000) = 1500000 - 2000 = 1498000
        assert snap.buying_power == Decimal("1498000")
        assert snap.available_funds == Decimal("13000")  # 15000 - 2000
        assert snap.currency == "USD"

    async def test_snapshot_no_args(self, manager: BalanceManager):
        snap = await manager.get_snapshot()
        assert snap.balance == Decimal("10000")
        assert snap.buying_power == Decimal("1000000")


class TestConcurrentOperations:
    """Concurrent balance operations."""

    async def test_concurrent_deposits(self, manager: BalanceManager):
        import asyncio

        async def deposit(amount: Decimal):
            return await manager.deposit(amount)

        tasks = [deposit(Decimal("1000")) for _ in range(10)]
        await asyncio.gather(*tasks)
        assert await manager.get_balance() == Decimal("20000")

    async def test_concurrent_withdrawals(self, manager: BalanceManager):
        import asyncio

        async def withdraw(amount: Decimal):
            return await manager.withdraw(amount)

        tasks = [withdraw(Decimal("1000")) for _ in range(5)]
        await asyncio.gather(*tasks)
        assert await manager.get_balance() == Decimal("5000")

    async def test_concurrent_deposit_and_withdraw(self, manager: BalanceManager):
        import asyncio

        async def dep():
            return await manager.deposit(Decimal("5000"))

        async def wth():
            return await manager.withdraw(Decimal("3000"))

        results = await asyncio.gather(dep(), wth(), return_exceptions=True)
        non_exceptions = [r for r in results if not isinstance(r, Exception)]
        assert len(non_exceptions) == 2


class TestEdgeCases:
    """Edge cases for BalanceManager."""

    async def test_large_balance(self, manager: BalanceManager):
        snap = await manager.deposit(Decimal("999999999"))
        assert snap.balance == Decimal("1000009999")

    async def test_small_decimal(self, manager: BalanceManager):
        snap = await manager.deposit(Decimal("0.01"))
        assert snap.balance == Decimal("10000.01")

    async def test_reset(self, manager: BalanceManager):
        await manager.deposit(Decimal("5000"))
        await manager.reset()
        assert await manager.get_balance() == Decimal("0")

    async def test_reset_with_value(self, manager: BalanceManager):
        await manager.reset(Decimal("5000"))
        assert await manager.get_balance() == Decimal("5000")
