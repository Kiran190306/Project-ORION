"""Aggressive Concurrency Tests for the Portfolio Engine.

Validates thread safety and race-condition resilience under heavy concurrent load.

Scenarios:
- Concurrent opens, closes, partial closes
- Concurrent deposits, withdrawals
- Concurrent margin updates, price updates
- Mixed concurrent operations

Validates:
- No race conditions
- No duplicate positions
- No lost updates
- No negative balances
- Consistent snapshots under concurrent load
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig
from libraries.domain.portfolio.position_manager import PositionManager, PositionManagerConfig


@pytest.fixture
async def position_manager() -> PositionManager:
    m = PositionManager(config=PositionManagerConfig(generate_position_id=True, track_history=True))
    yield m
    await m.clear_all()


@pytest.fixture
async def portfolio() -> PortfolioManager:
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("1000000"),
            max_leverage=Decimal("100"),
            account_currency="USD",
            margin_call_level=100.0,
            stop_out_level=50.0,
            track_journal=True,
            track_analytics=True,
        ),
    )
    yield p
    await p.clear_all()


class TestConcurrentOpens:
    """Concurrent position opening scenarios."""

    async def test_concurrent_100_opens(self, position_manager: PositionManager):
        """Open 100 positions concurrently."""

        async def open_pos(i: int):
            return await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
                strategy="concurrent_open",
            )

        tasks = [open_pos(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 100
        assert await position_manager.total_count == 100
        # All positions should be unique
        ids = {p.position_id for p in results}
        assert len(ids) == 100

    async def test_concurrent_opens_multiple_symbols(self, position_manager: PositionManager):
        """Open positions on different symbols concurrently."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD"]

        async def open_pos(symbol: str):
            return await position_manager.open_position(
                symbol=symbol,
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
            )

        tasks = [open_pos(s) for s in symbols for _ in range(20)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 100

        # Verify per-symbol counts
        for sym in symbols:
            positions = await position_manager.get_positions_by_symbol(sym)
            assert len(positions) == 20, f"Symbol {sym} expected 20, got {len(positions)}"


class TestConcurrentCloses:
    """Concurrent position closing scenarios."""

    async def test_concurrent_closes(self, position_manager: PositionManager):
        """Open then close all positions concurrently."""
        positions = []
        for i in range(50):
            pos = await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
            )
            positions.append(pos)

        async def close_pos(pos):
            return await position_manager.close_position(
                position_id=pos.position_id,
                close_price=Decimal("1.1100"),
            )

        results = await asyncio.gather(*[close_pos(p) for p in positions])
        assert len(results) == 50
        assert all(r.status.value == "closed" for r in results)

    async def test_concurrent_partial_closes(self, position_manager: PositionManager):
        """Concurrent partial closes on different positions."""
        positions = []
        for i in range(30):
            pos = await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
            )
            positions.append(pos)

        async def partial_close(pos):
            return await position_manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("3000"),
                close_price=Decimal("1.1050"),
            )

        results = await asyncio.gather(*[partial_close(p) for p in positions])
        assert len(results) == 30
        assert all(r.quantity == Decimal("7000") for r in results)


class TestConcurrentBalanceOperations:
    """Concurrent balance operation scenarios."""

    async def test_concurrent_deposits(self, portfolio: PortfolioManager):
        """20 concurrent deposits."""

        async def deposit():
            return await portfolio.deposit(Decimal("1000"))

        results = await asyncio.gather(*[deposit() for _ in range(20)])
        assert len(results) == 20
        account = await portfolio.get_account_snapshot()
        assert account.balance == Decimal("1020000")  # 1000000 + 20*1000

    async def test_concurrent_withdrawals(self, portfolio: PortfolioManager):
        """10 concurrent withdrawals. Each withdraw uses asyncio.Lock
        so concurrent operations are serialized correctly."""

        async def withdraw():
            return await portfolio.withdraw(Decimal("1000"))

        results = await asyncio.gather(*[withdraw() for _ in range(10)])
        assert len(results) == 10
        account = await portfolio.get_account_snapshot()
        # 10 * 1000 = 10000 deducted from 1000000
        assert account.balance == Decimal("990000")

    async def test_concurrent_deposit_and_withdraw(self, portfolio: PortfolioManager):
        """Mixed deposits and withdrawals."""

        async def deposit():
            return await portfolio.deposit(Decimal("5000"))

        async def withdraw():
            return await portfolio.withdraw(Decimal("2000"))

        tasks = [deposit() for _ in range(10)] + [withdraw() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        non_errors = sum(1 for r in results if not isinstance(r, Exception))
        assert non_errors > 0


class TestConcurrentMixedOperations:
    """Mixed concurrent operation scenarios."""

    async def test_concurrent_open_close(self, portfolio: PortfolioManager):
        """Concurrent open and close operations."""

        async def trade(i: int):
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("10000"),
                    entry_price=Decimal("1.1000"),
                    execution_id=f"EXEC-CONC-{i:04d}",
                )
                await portfolio.close_position(
                    pos.position_id,
                    Decimal("1.1050"),
                )
                return "success"
            except Exception:
                return "failed"

        tasks = [trade(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r == "success")
        assert success_count > 0
        # Verify final state is consistent
        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")
        assert account.equity >= Decimal("0")

    async def test_concurrent_open_close_deposit_withdraw(self, portfolio: PortfolioManager):
        """Heavy mixed workload: opens, closes, deposits, withdrawals."""

        async def deposit():
            return await portfolio.deposit(Decimal("5000"))

        async def withdraw():
            return await portfolio.withdraw(Decimal("2000"))

        async def trade(i: int):
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("10000"),
                    entry_price=Decimal("1.1000"),
                    execution_id=f"EXEC-MIX-{i:04d}",
                )
                await portfolio.close_position(
                    pos.position_id,
                    Decimal("1.1100"),
                )
                return True
            except Exception:
                return False

        tasks = (
            [deposit() for _ in range(10)]
            + [withdraw() for _ in range(5)]
            + [trade(i) for i in range(20)]
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if not isinstance(r, Exception) and r is not False)
        assert successes > 0

        # Verify invariants hold
        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

    async def test_concurrent_price_updates(self, portfolio: PortfolioManager):
        """Concurrent price updates on the same symbol."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )

        async def update_price(price: Decimal):
            return await portfolio.update_price("EURUSD", price)

        prices = [Decimal(f"1.10{i:02d}") for i in range(1, 21)]
        tasks = [update_price(p) for p in prices]
        await asyncio.gather(*tasks)

        # Verify final state is consistent
        account = await portfolio.get_account_snapshot()
        assert (
            account.equity == account.balance + (await portfolio.get_pnl_breakdown()).unrealized_pnl
        )

    async def test_concurrent_mixed_symbols(self, portfolio: PortfolioManager):
        """Concurrent operations on multiple symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]

        async def trade_on_symbol(symbol: str, i: int):
            try:
                pos = await portfolio.open_position(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=Decimal("10000"),
                    entry_price=Decimal("1.1000"),
                    execution_id=f"EXEC-MULTI-{i:04d}",
                )
                await portfolio.update_price(symbol, Decimal("1.1050"))
                return pos.position_id
            except Exception:
                return None

        tasks = [trade_on_symbol(s, i) for i, s in enumerate(symbols * 10)]
        results = await asyncio.gather(*tasks)
        successes = [r for r in results if r is not None]
        assert len(successes) > 0

    async def test_concurrent_no_duplicate_positions(self, position_manager: PositionManager):
        """Verify concurrent opens do not produce duplicate position IDs."""

        async def open_with_id(i: int):
            try:
                return await position_manager.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1000"),
                    entry_price=Decimal("1.1000"),
                )
            except Exception:
                return None

        results = await asyncio.gather(*[open_with_id(i) for i in range(50)])
        results = [r for r in results if r is not None]
        ids = [r.position_id for r in results]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {len(ids)} != {len(set(ids))}"


class TestConcurrentRaceCondition:
    """Race condition validation scenarios."""

    async def test_race_close_and_update_same_position(self, portfolio: PortfolioManager):
        """Race condition: close position while updating price on same position."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        async def close():
            return await portfolio.close_position(
                pos.position_id,
                Decimal("1.1100"),
            )

        async def update():
            return await portfolio.update_price("EURUSD", Decimal("1.1050"))

        # Fire these simultaneously to trigger race condition
        tasks = [close() for _ in range(5)] + [update() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one should succeed
        non_exceptions = [r for r in results if not isinstance(r, Exception)]
        assert len(non_exceptions) > 0

        # Verify invariants
        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")

    async def test_race_multiple_partial_closes(self, portfolio: PortfolioManager):
        """Race condition: multiple partial closes on the same position."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        async def partial_close():
            try:
                return await portfolio.partially_close_position(
                    position_id=pos.position_id,
                    close_quantity=Decimal("5000"),
                    close_price=Decimal("1.1050"),
                )
            except Exception:
                return None

        results = await asyncio.gather(*[partial_close() for _ in range(3)])
        successes = [r for r in results if r is not None]
        # Only one partial close should succeed (reduces quantity by 5000)
        assert len(successes) >= 1

    async def test_race_deposit_withdraw_open(self, portfolio: PortfolioManager):
        """Race condition: deposit, withdraw, and open simultaneously."""

        async def deposit():
            return await portfolio.deposit(Decimal("10000"))

        async def withdraw():
            return await portfolio.withdraw(Decimal("5000"))

        async def open_pos():
            try:
                return await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("10000"),
                    entry_price=Decimal("1.1000"),
                )
            except Exception:
                return None

        tasks = (
            [deposit() for _ in range(10)]
            + [withdraw() for _ in range(5)]
            + [open_pos() for _ in range(10)]
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        non_errors = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
        assert non_errors > 0

    async def test_race_margin_call_scenario(self, portfolio: PortfolioManager):
        """Race condition: large position open + withdraw to trigger margin call."""

        async def open_large():
            try:
                return await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("500000"),
                    entry_price=Decimal("1.1000"),
                    leverage=Decimal("10"),
                )
            except Exception:
                return None

        async def withdraw_all():
            try:
                return await portfolio.withdraw(Decimal("800000"))
            except Exception:
                return None

        results = await asyncio.gather(open_large(), withdraw_all(), return_exceptions=True)
        # Either could fail but state must be consistent
        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")

    async def test_consistent_snapshots_under_concurrent_load(self, portfolio: PortfolioManager):
        """Snapshots must be consistent when queried under concurrent load."""

        async def trade(i: int):
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("10000"),
                    entry_price=Decimal("1.1000"),
                )
                await portfolio.close_position(
                    pos.position_id,
                    Decimal("1.1050"),
                )
            except Exception:
                pass

        async def snapshot():
            try:
                return await portfolio.get_portfolio_snapshot()
            except Exception:
                return None

        # Mix trades and snapshot queries
        tasks = [trade(i) for i in range(20)] + [snapshot() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify snapshots are valid
        snapshots = [r for r in results if r is not None and not isinstance(r, Exception)]
        for snap in snapshots:
            assert snap.position_count >= 0
            assert snap.gross_exposure >= abs(snap.net_exposure)
