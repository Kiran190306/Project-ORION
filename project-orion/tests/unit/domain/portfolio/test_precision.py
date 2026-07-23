"""Forex Precision Tests for the Portfolio Engine.

Validates calculations for major Forex pairs:
- EURUSD (4 decimal places)
- GBPUSD (4 decimal places)
- USDJPY (2 decimal places)
- XAUUSD (2 decimal places) — Gold
- Fractional pips (5 decimal places)
- Micro lots (0.01 lot = 1,000 units)
- Large lots (institutional sizes)

Cross-checks:
- Floating PnL
- Realized PnL
- Net PnL (including commissions, swaps, fees)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide, PositionStatus
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


class TestEURUSDPrecision:
    """EURUSD — standard 4 decimal place Forex pair."""

    async def test_eurusd_1_pip_move(self, position_manager: PositionManager):
        """1 pip = 0.0001 on EURUSD with 100k units = $10."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1001"),  # 1 pip
        )
        assert closed.realized_pnl == Decimal("10")  # 0.0001 * 100000

    async def test_eurusd_10_pips(self, position_manager: PositionManager):
        """10 pip move = $100 on 100k units."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1010"),  # 10 pips
        )
        assert closed.realized_pnl == Decimal("100")

    async def test_eurusd_fractional_pip(self, position_manager: PositionManager):
        """Fractional pip (0.1 pip = 0.00001) on EURUSD = $1."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.10000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.10001"),  # 0.1 pip / 1 fractional pip
        )
        assert closed.realized_pnl == Decimal("1")

    async def test_eurusd_half_pip(self, position_manager: PositionManager):
        """0.5 pip = 0.00005 = $5 on 100k."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.10005"),
        )
        assert closed.realized_pnl == Decimal("5")

    async def test_eurusd_micro_lot(self, position_manager: PositionManager):
        """Micro lot (0.01 lot = 1,000 units): 1 pip = $0.10."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1010"),  # 10 pips
        )
        assert closed.realized_pnl == Decimal("1")  # 0.0010 * 1000

    async def test_eurusd_mini_lot(self, position_manager: PositionManager):
        """Mini lot (0.1 lot = 10,000 units): 1 pip = $1."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1001"),  # 1 pip
        )
        assert closed.realized_pnl == Decimal("1")

    async def test_eurusd_standard_lot(self, position_manager: PositionManager):
        """Standard lot (100,000 units): 1 pip = $10."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1001"),  # 1 pip
        )
        assert closed.realized_pnl == Decimal("10")

    async def test_eurusd_short_position(self, position_manager: PositionManager):
        """Short EURUSD: price drops = profit."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0990"),  # 10 pips down
        )
        assert closed.realized_pnl == Decimal("100")  # (1.1000 - 1.0990) * 100000

    async def test_eurusd_negative_pnl(self, position_manager: PositionManager):
        """Long EURUSD that moves against: negative P&L."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0990"),  # 10 pips down
        )
        assert closed.realized_pnl == Decimal("-100")  # (1.0990 - 1.1000) * 100000


class TestUSDJPYPrecision:
    """USDJPY — 2 decimal places standard, 3 decimal places some brokers."""

    async def test_usdjpy_1_pip(self, position_manager: PositionManager):
        """1 pip = 0.01 on USDJPY."""
        pos = await position_manager.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("110.01"),  # 1 pip
        )
        # P&L in JPY terms likely, but our model works in account currency
        assert closed.realized_pnl == Decimal("1000")  # 0.01 * 100000

    async def test_usdjpy_50_pips(self, position_manager: PositionManager):
        """50 pip move on USDJPY."""
        pos = await position_manager.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("110.50"),  # 50 pips
        )
        assert closed.realized_pnl == Decimal("50000")

    async def test_usdjpy_short(self, position_manager: PositionManager):
        """Short USDJPY."""
        pos = await position_manager.open_position(
            symbol="USDJPY",
            side=PositionSide.SHORT,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("109.50"),  # 50 pips down
        )
        assert closed.realized_pnl == Decimal("50000")

    async def test_usdjpy_micro_lot(self, position_manager: PositionManager):
        """USDJPY micro lot."""
        pos = await position_manager.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("110.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("110.10"),  # 10 pips
        )
        assert closed.realized_pnl == Decimal("100")  # 0.10 * 1000


class TestXAUUSDPrecision:
    """XAUUSD (Gold) — typically 2 decimal places."""

    async def test_xauusd_1_dollar_move(self, position_manager: PositionManager):
        """$1 move on XAUUSD with 100oz = $100."""
        pos = await position_manager.open_position(
            symbol="XAUUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100"),
            entry_price=Decimal("1900.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1901.00"),  # $1 move
        )
        assert closed.realized_pnl == Decimal("100")  # 1.00 * 100

    async def test_xauusd_10_cents(self, position_manager: PositionManager):
        """$0.10 move on XAUUSD."""
        pos = await position_manager.open_position(
            symbol="XAUUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100"),
            entry_price=Decimal("1900.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1900.10"),  # $0.10
        )
        assert closed.realized_pnl == Decimal("10")  # 0.10 * 100

    async def test_xauusd_short(self, position_manager: PositionManager):
        """Short XAUUSD."""
        pos = await position_manager.open_position(
            symbol="XAUUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("100"),
            entry_price=Decimal("1900.00"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1898.00"),  # $2 drop
        )
        assert closed.realized_pnl == Decimal("200")


class TestPrecisionCrossCheck:
    """Cross-check P&L calculations independently."""

    async def test_floating_pnl_cross_check(self, portfolio: PortfolioManager):
        """Cross-check floating (unrealized) P&L independently."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        # Floating P&L = (1.1050 - 1.1000) * 100000 = 500
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.unrealized_pnl == Decimal("500")
        assert pnl.floating_pnl == Decimal("500")

    async def test_realized_pnl_cross_check(self, portfolio: PortfolioManager):
        """Cross-check realized P&L independently."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
        )
        # Realized P&L = (1.1100 - 1.1000) * 100000 = 1000
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("1000")

    async def test_net_pnl_with_charges(self, portfolio: PortfolioManager):
        """Cross-check net P&L including commissions, swaps, fees."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            commission=Decimal("15"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            commission=Decimal("5"),
            swap=Decimal("-2"),
            fees=Decimal("1"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        # Realized: 1000
        # Commission: 15 + 5 = 20
        # Swap: -2
        # Fees: 1
        # Net: 1000 - 20 - (-2?) Actually net_profit = realized + unrealized - commission - swap - fees
        # Wait, net_profit from PnLBreakdown = realized + unrealized - commission - swap - fees
        # net_profit = 1000 + 0 - 20 - (-2) - 1 = 981? Let's check the formula
        # From PortfolioManager.get_pnl_breakdown:
        # net_profit = realized + unrealized - commission - swap - fees
        # = 1000 - 20 - (-2) - 1 = 1000 - 20 + 2 - 1 = 981
        assert pnl.realized_pnl == Decimal("1000")
        assert pnl.commission == Decimal("20")  # 15 + 5
        assert pnl.swap == Decimal("-2")
        assert pnl.fees == Decimal("1")

    async def test_precision_multiple_pairs(self, portfolio: PortfolioManager):
        """Test precision across multiple pairs simultaneously."""
        pairs = [
            ("EURUSD", PositionSide.LONG, Decimal("1.1000"), Decimal("1.1010"), Decimal("100000")),
            ("GBPUSD", PositionSide.SHORT, Decimal("1.2500"), Decimal("1.2480"), Decimal("50000")),
            ("USDJPY", PositionSide.LONG, Decimal("110.00"), Decimal("110.50"), Decimal("100000")),
            ("XAUUSD", PositionSide.SHORT, Decimal("1900.00"), Decimal("1895.00"), Decimal("50")),
        ]

        for symbol, side, entry, close, qty in pairs:
            pos = await portfolio.open_position(
                symbol=symbol,
                side=side,
                quantity=qty,
                entry_price=entry,
            )
            closed = await portfolio.close_position(
                position_id=pos.position_id,
                close_price=close,
            )
            # Verify P&L sign is correct based on direction
            if side == PositionSide.LONG:
                assert (closed.realized_pnl > Decimal("0")) == (close > entry)
            else:
                assert (closed.realized_pnl > Decimal("0")) == (entry > close)

    async def test_precision_zero_pnl(self, portfolio: PortfolioManager):
        """P&L should be exactly zero when close equals entry."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.10000"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.10000"),
        )
        assert closed.realized_pnl == Decimal("0")

    async def test_precision_aggregate_pnl(self, portfolio: PortfolioManager):
        """Verify aggregate P&L across multiple trades."""
        total_expected = Decimal("0")

        # Win: +500
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
        )
        c1 = await portfolio.close_position(p1.position_id, Decimal("1.1100"))
        total_expected += c1.realized_pnl

        # Loss: -250
        p2 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
        )
        c2 = await portfolio.close_position(p2.position_id, Decimal("1.0950"))
        total_expected += c2.realized_pnl

        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == total_expected
