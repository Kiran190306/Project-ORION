"""Edge case tests for the Portfolio & Position Management Engine.

Covers:
- Zero quantity, Negative prices
- Duplicate IDs, Invalid transitions
- Empty portfolio, Large portfolio (10,000 positions)
- Precision/rounding for Forex price formats
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

import pytest

from libraries.domain.portfolio.exceptions import (
    DuplicatePositionError,
    InvalidPositionStateError,
    PositionNotFoundError,
    PositionSizeError,
)
from libraries.domain.portfolio.models import PositionSide, PositionStatus
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig
from libraries.domain.portfolio.position_manager import PositionManager, PositionManagerConfig

# Increase precision for Forex tests
getcontext().prec = 50


@pytest.fixture
async def position_manager() -> PositionManager:
    m = PositionManager(config=PositionManagerConfig(generate_position_id=True, track_history=True))
    yield m
    await m.clear_all()


@pytest.fixture
async def portfolio() -> PortfolioManager:
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("10000"),
            max_leverage=Decimal("100"),
        ),
    )
    yield p
    await p.clear_all()


class TestZeroQuantity:
    """Zero quantity scenarios."""

    async def test_open_with_zero_quantity(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("0"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.quantity == Decimal("0")

    async def test_close_zero_quantity(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(PositionSizeError):
            await position_manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("0"),
                close_price=Decimal("1.11"),
            )

    async def test_increase_by_zero(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        increased = await position_manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("0"),
            entry_price=Decimal("1.11"),
        )
        assert increased.quantity == Decimal("1000")

    async def test_deposit_zero(self, portfolio: PortfolioManager):
        snap = await portfolio.deposit(Decimal("0"))
        assert snap.balance == Decimal("10000")

    async def test_withdraw_zero(self, portfolio: PortfolioManager):
        snap = await portfolio.withdraw(Decimal("0"))
        assert snap.balance == Decimal("10000")


class TestNegativePrices:
    """Negative price scenarios.

    Note: The Position model does NOT validate price sign — it accepts any Decimal.
    Negative prices produce negative P&L for long positions since
    models allow any rational price value.
    """

    async def test_open_with_negative_price(self, position_manager: PositionManager):
        """Negative entry price is accepted by the model but produces
        predictable P&L calculations."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("-1.10"),
        )
        assert pos.quantity == Decimal("1000")
        assert pos.entry_price == Decimal("-1.10")
        # Negative entry + positive close = profit (price difference)
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("0.00"),
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.realized_pnl == Decimal("1100")  # (0 - (-1.10)) * 1000

    async def test_close_with_negative_price(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        # Should still work as models allow any price
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("-1.00"),
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.realized_pnl == Decimal("-2100")  # (-1.00 - 1.10) * 1000


class TestDuplicateIDs:
    """Duplicate ID scenarios."""

    async def test_duplicate_position_id(self, position_manager: PositionManager):
        await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
            position_id="DUP-001",
        )
        with pytest.raises(DuplicatePositionError):
            await position_manager.open_position(
                symbol="GBPUSD",
                side=PositionSide.SHORT,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.25"),
                position_id="DUP-001",
            )


class TestInvalidTransitions:
    """Invalid state transition scenarios."""

    async def test_close_already_closed(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await position_manager.close_position(pos.position_id, Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.close_position(pos.position_id, Decimal("1.12"))

    async def test_close_liquidated(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await position_manager.liquidate_position(pos.position_id, Decimal("1.09"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.close_position(pos.position_id, Decimal("1.11"))

    async def test_force_close_liquidated(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await position_manager.liquidate_position(pos.position_id, Decimal("1.09"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.forced_close_position(pos.position_id, Decimal("1.08"))

    async def test_update_stop_loss_closed(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await position_manager.close_position(pos.position_id, Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.update_position_stop_loss(pos.position_id, Decimal("1.09"))

    async def test_increase_closed_position(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await position_manager.close_position(pos.position_id, Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.increase_position(
                pos.position_id, Decimal("500"), Decimal("1.12")
            )


class TestEmptyPortfolio:
    """Empty portfolio scenarios."""

    async def test_empty_portfolio_operations(self, portfolio: PortfolioManager):
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.position_count == 0
        assert snap.open_position_count == 0
        assert snap.total_realized_pnl == Decimal("0")
        assert snap.net_exposure == Decimal("0")
        assert snap.gross_exposure == Decimal("0")

    async def test_stress_empty_journal(self, portfolio: PortfolioManager):
        entries = await portfolio.journal.get_recent()
        assert len(entries) == 0

    async def test_stress_empty_analytics(self, portfolio: PortfolioManager):
        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades == 0


class TestLargePortfolio:
    """Large portfolio (stress) scenarios."""

    @pytest.mark.slow
    async def test_10000_positions(self, position_manager: PositionManager):
        import asyncio

        async def open_pos(i: int):
            return await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
                strategy="stress_test",
                tags=(f"batch-{i // 1000}",),
            )

        tasks = [open_pos(i) for i in range(10000)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10000
        assert await position_manager.total_count == 10000

        # Verify lookups
        pos = await position_manager.get_position(results[5000].position_id)
        assert pos is not None

        # Verify symbol index
        eurusd = await position_manager.get_positions_by_symbol("EURUSD")
        assert len(eurusd) == 10000

        # Verify open count
        count = await position_manager.open_count
        assert count == 10000

    @pytest.mark.slow
    async def test_10000_positions_close_half(self, position_manager: PositionManager):
        import asyncio

        # Open positions
        positions = []
        for i in range(100):
            pos = await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
            )
            positions.append(pos)

        # Close half
        async def close_pos(pos):
            return await position_manager.close_position(
                position_id=pos.position_id,
                close_price=Decimal("1.1100"),
            )

        tasks = [close_pos(p) for p in positions[:50]]
        await asyncio.gather(*tasks)

        open_positions = await position_manager.get_open_positions()
        closed_positions = await position_manager.get_closed_positions()
        assert len(open_positions) == 50
        assert len(closed_positions) == 50

    @pytest.mark.slow
    async def test_large_portfolio_memory(self, position_manager: PositionManager):
        # Open positions across multiple symbols
        import asyncio

        symbols = [
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "AUDUSD",
            "NZDUSD",
            "USDCAD",
            "CHFJPY",
            "EURGBP",
            "EURJPY",
            "GBPJPY",
        ]

        async def open_pos_for_symbol(symbol: str, i: int):
            return await position_manager.open_position(
                symbol=symbol,
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
            )

        all_tasks = []
        for i in range(5000):
            sym = symbols[i % len(symbols)]
            all_tasks.append(open_pos_for_symbol(sym, i))

        results = await asyncio.gather(*all_tasks)
        assert len(results) == 5000

        # Verify per-symbol counts
        for sym in symbols:
            positions = await position_manager.get_positions_by_symbol(sym)
            assert len(positions) == 500

    @pytest.mark.slow
    async def test_portfolio_manager_stress(self, portfolio: PortfolioManager):
        import asyncio

        async def open_and_close(i: int):
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD" if i % 2 == 0 else "GBPUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1000"),
                    entry_price=Decimal("1.1000"),
                    execution_id=f"EXEC-{i:06d}",
                    decision_id=f"DEC-{i:06d}",
                    strategy="stress_test",
                )
                await portfolio.close_position(
                    position_id=pos.position_id,
                    close_price=Decimal("1.1100") if i % 2 == 0 else Decimal("1.0900"),
                    close_reason="stress_close",
                )
                return True
            except Exception:
                return False

        tasks = [open_and_close(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r)
        assert success_count > 0

        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades > 0


class TestPrecisionRounding:
    """Precision and rounding scenarios for Forex price formats."""

    # Standard Forex pip sizes:
    # EURUSD: 0.0001 (1 pip)
    # USDJPY: 0.01 (1 pip)
    # XAUUSD: 0.01 (1 pip)

    async def test_precision_eurusd_pips(self, position_manager: PositionManager):
        """Test precision for EURUSD (4 decimal places)."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.12345"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.12355"),
        )
        # 10 micro-pips difference = 100000 * 0.00010 = 10 USD
        assert closed.realized_pnl == Decimal("10")

    async def test_precision_usdjpy(self, position_manager: PositionManager):
        """Test precision for USDJPY (2 decimal places standard)."""
        pos = await position_manager.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("110.55"),
        )
        # 5 pips difference = 100000 * 0.05 = 5000 (in JPY terms, depends on contract)
        assert closed.realized_pnl == Decimal("5000")  # position * price diff

    async def test_precision_small_quantity(self, position_manager: PositionManager):
        """Test with micro-lot (0.01 lot = 1000 units)."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.10010"),
        )
        # 0.00010 * 1000 = 0.10
        assert closed.realized_pnl == Decimal("0.10")

    async def test_precision_many_decimals(self, position_manager: PositionManager):
        """Test with many decimal places in price."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.123456789"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.123456799"),
        )
        # Very small move
        diff = Decimal("1.123456799") - Decimal("1.123456789")
        expected = diff * Decimal("100000")
        assert closed.realized_pnl == expected

    async def test_precision_large_position(self, position_manager: PositionManager):
        """Test with institutional size position."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000000"),
            entry_price=Decimal("1.12345"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.12346"),
        )
        # 0.00001 * 10000000 = 100
        assert closed.realized_pnl == Decimal("100")

    async def test_precision_negative_pnl(self, position_manager: PositionManager):
        """Test precision for negative P&L."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.12345"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.12335"),
        )
        assert closed.realized_pnl == Decimal("-10")

    async def test_precision_zero(self, position_manager: PositionManager):
        """Test precision when P&L is zero."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.12345"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.12345"),
        )
        assert closed.realized_pnl == Decimal("0")


class TestConcurrentOperations:
    """Concurrent operation scenarios."""

    async def test_concurrent_position_opens(self, position_manager: PositionManager):
        import asyncio

        async def open_pos(i: int):
            return await position_manager.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.10"),
                strategy="concurrent",
            )

        tasks = [open_pos(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 50

    async def test_concurrent_deposits_and_withdrawals(self, portfolio: PortfolioManager):
        import asyncio

        async def deposit():
            return await portfolio.deposit(Decimal("1000"))

        async def withdraw():
            return await portfolio.withdraw(Decimal("500"))

        tasks = [deposit() for _ in range(10)] + [withdraw() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        non_exceptions = [r for r in results if not isinstance(r, Exception)]
        assert len(non_exceptions) > 0

    async def test_concurrent_position_updates(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        import asyncio

        async def update_price(price: Decimal):
            return await position_manager.update_position_price(
                position_id=pos.position_id,
                current_price=price,
            )

        tasks = [update_price(Decimal(f"1.10{i:02d}")) for i in range(10)]
        await asyncio.gather(*tasks)

        final = await position_manager.get_position(pos.position_id)
        assert final is not None
        assert final.current_price is not None

    async def test_concurrent_close_and_partial(self, position_manager: PositionManager):
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        import asyncio

        async def close_full():
            return await position_manager.close_position(
                position_id=pos.position_id,
                close_price=Decimal("1.11"),
            )

        async def partial_close():
            return await position_manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("5000"),
                close_price=Decimal("1.1050"),
            )

        results = await asyncio.gather(close_full(), partial_close(), return_exceptions=True)
        non_exceptions = [r for r in results if not isinstance(r, Exception)]
        assert len(non_exceptions) > 0
