"""Tests for P&L calculations via PortfolioManager.

Covers:
- Realized P&L, Unrealized P&L
- Commission, Swap, Fees
- Floating P&L, Net P&L
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig


@pytest.fixture
async def portfolio() -> PortfolioManager:
    """Create a clean PortfolioManager for each test."""
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("10000"),
            max_leverage=Decimal("100"),
            track_journal=True,
            track_analytics=True,
        ),
    )
    yield p
    await p.clear_all()


class TestRealizedPnL:
    """Realized P&L scenarios."""

    async def test_realized_pnl_long_profit(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            close_reason="tp",
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("100")  # (1.1100-1.1000)*10000
        assert pnl.net_profit > 0

    async def test_realized_pnl_long_loss(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0900"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("-100")

    async def test_realized_pnl_short_profit(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.2400"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("50")  # (1.2500-1.2400)*5000

    async def test_realized_pnl_short_loss(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.2600"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("-50")

    async def test_multiple_trades_realized_pnl(self, portfolio: PortfolioManager):
        p1 = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            "GBPUSD",
            PositionSide.SHORT,
            Decimal("5000"),
            Decimal("1.2500"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1050"))
        await portfolio.close_position(p2.position_id, Decimal("1.2400"))
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("100")  # 50 + 50


class TestUnrealizedPnL:
    """Unrealized P&L scenarios."""

    async def test_unrealized_pnl_long(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1100"))
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.unrealized_pnl == Decimal("100")

    async def test_unrealized_pnl_short(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "GBPUSD",
            PositionSide.SHORT,
            Decimal("5000"),
            Decimal("1.2500"),
        )
        await portfolio.update_price("GBPUSD", Decimal("1.2400"))
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.unrealized_pnl == Decimal("50")


class TestCommissionSwapFees:
    """Commission, swap and fees scenarios."""

    async def test_commission_charged(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
            commission=Decimal("10"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            commission=Decimal("5"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.commission == Decimal("15")
        assert pnl.total_charges >= Decimal("15")

    async def test_swap_charged(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
            swap=Decimal("-2"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            swap=Decimal("-1"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.swap == Decimal("-3")

    async def test_fees_charged(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
            fees=Decimal("1"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            fees=Decimal("2"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.fees == Decimal("3")


class TestFloatingPnL:
    """Floating P&L scenarios."""

    async def test_floating_pnl_equals_unrealized(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.floating_pnl == pnl.unrealized_pnl

    async def test_floating_pnl_updates_with_price(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        pnl1 = await portfolio.get_pnl_breakdown()
        assert pnl1.floating_pnl == Decimal("50")

        await portfolio.update_price("EURUSD", Decimal("1.1100"))
        pnl2 = await portfolio.get_pnl_breakdown()
        assert pnl2.floating_pnl == Decimal("100")


class TestGrossProfitLoss:
    """Gross profit and loss scenarios."""

    async def test_gross_profit(self, portfolio: PortfolioManager):
        p1 = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            "GBPUSD",
            PositionSide.SHORT,
            Decimal("5000"),
            Decimal("1.2500"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1050"))  # +50
        await portfolio.close_position(p2.position_id, Decimal("1.2400"))  # +50
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.gross_profit == Decimal("100")

    async def test_gross_loss(self, portfolio: PortfolioManager):
        p1 = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            "GBPUSD",
            PositionSide.SHORT,
            Decimal("5000"),
            Decimal("1.2500"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.0950"))  # -50
        await portfolio.close_position(p2.position_id, Decimal("1.2600"))  # -50
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.gross_loss == Decimal("-100")

    async def test_net_pnl_with_charges(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            "EURUSD",
            PositionSide.LONG,
            Decimal("10000"),
            Decimal("1.1000"),
            commission=Decimal("10"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            commission=Decimal("10"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        # realized=100, commission=20, net = 100-20 = 80
        assert pnl.net_profit == Decimal("80")


class TestPnLBreakdownStructure:
    """PnLBreakdown model structure tests."""

    async def test_pnl_breakdown_properties(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        assert hasattr(pnl, "realized_pnl")
        assert hasattr(pnl, "unrealized_pnl")
        assert hasattr(pnl, "floating_pnl")
        assert hasattr(pnl, "gross_profit")
        assert hasattr(pnl, "gross_loss")
        assert hasattr(pnl, "net_profit")
        assert hasattr(pnl, "commission")
        assert hasattr(pnl, "swap")
        assert hasattr(pnl, "fees")
        assert hasattr(pnl, "total_charges")
        assert hasattr(pnl, "total_cost")
        assert hasattr(pnl, "is_profitable")
        assert hasattr(pnl, "currency")
        assert hasattr(pnl, "timestamp")

    async def test_total_cost(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.total_cost == pnl.commission + pnl.swap + pnl.fees

    async def test_is_profitable(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        if pnl.net_profit > 0:
            assert pnl.is_profitable
        else:
            assert not pnl.is_profitable
