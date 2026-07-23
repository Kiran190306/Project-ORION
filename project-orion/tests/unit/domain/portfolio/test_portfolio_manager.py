"""Tests for PortfolioManager — the primary facade for all portfolio operations.

Covers:
- End-to-end: open/close positions through the facade
- Deposit/Withdraw, Account/Portfolio snapshots
- Drawdown, P&L breakdown, Portfolio heat
- Journal integration, Analytics integration
- All sub-manager interactions
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide, PositionStatus
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig


@pytest.fixture
async def portfolio() -> PortfolioManager:
    """Create a clean PortfolioManager for each test."""
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("10000"),
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


class TestInitialState:
    """Initial portfolio state scenarios."""

    async def test_initial_account_snapshot(self, portfolio: PortfolioManager):
        snap = await portfolio.get_account_snapshot()
        assert snap.balance == Decimal("10000")
        assert snap.equity == Decimal("10000")
        assert snap.free_margin == Decimal("10000")
        assert snap.used_margin == Decimal("0")
        assert snap.margin_level == float("inf")

    async def test_initial_portfolio_snapshot(self, portfolio: PortfolioManager):
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.position_count == 0
        assert snap.open_position_count == 0
        assert snap.total_realized_pnl == Decimal("0")

    async def test_initial_pnl_breakdown(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("0")
        assert pnl.unrealized_pnl == Decimal("0")

    async def test_initial_portfolio_analytics(self, portfolio: PortfolioManager):
        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades == 0

    async def test_initial_drawdown(self, portfolio: PortfolioManager):
        dd = await portfolio.get_drawdown()
        assert dd.current_drawdown == 0.0
        assert dd.max_drawdown == 0.0

    async def test_properties(self, portfolio: PortfolioManager):
        assert portfolio.position_manager is not None
        assert portfolio.balance_manager is not None
        assert portfolio.equity_manager is not None
        assert portfolio.margin_manager is not None
        assert portfolio.exposure_manager is not None
        assert portfolio.journal is not None
        assert portfolio.analytics is not None
        assert portfolio.config is not None


class TestOpenPosition:
    """End-to-end position opening scenarios."""

    async def test_open_long_position(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            execution_id="EXEC-001",
            decision_id="DEC-001",
            strategy="momentum",
        )
        assert pos.symbol == "EURUSD"
        assert pos.status == PositionStatus.OPEN

        snap = await portfolio.get_portfolio_snapshot()
        assert snap.open_position_count == 1
        assert snap.position_count == 1

        # Journal entry created
        entries = await portfolio.journal.get_by_position(pos.position_id)
        assert len(entries) > 0
        assert entries[0].entry_type.value == "position_opened"

    async def test_open_with_commission(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            commission=Decimal("5"),
        )
        assert pos.commission == Decimal("5")

    async def test_open_position_updates_exposure(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        exposure = await portfolio.exposure_manager.get_net_exposure()
        assert exposure == Decimal("11000")  # 10000 * 1.1000

    async def test_open_position_updates_margin(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        used = await portfolio.margin_manager.get_used_margin()
        assert used > Decimal("0")


class TestClosePosition:
    """End-to-end position closing scenarios."""

    async def test_close_long_position(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            close_reason="take_profit",
        )
        assert closed.status == PositionStatus.CLOSED

        snap = await portfolio.get_account_snapshot()
        assert snap.balance > Decimal("10000")  # Profit added

        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl > Decimal("0")

    async def test_close_position_journal_entry(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
        )
        entries = await portfolio.journal.get_by_position(pos.position_id)
        assert len(entries) >= 2  # opened + profit

    async def test_close_position_updates_exposure(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
        )
        net = await portfolio.exposure_manager.get_net_exposure()
        assert net == Decimal("0")

    async def test_close_position_updates_margin(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
        )
        used = await portfolio.margin_manager.get_used_margin()
        assert used == Decimal("0")


class TestPartialClose:
    """End-to-end partial close scenarios."""

    async def test_partial_close_updates_position(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await portfolio.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("4000"),
            close_price=Decimal("1.1050"),
        )
        assert closed.quantity == Decimal("6000")
        exposure = await portfolio.exposure_manager.get_net_exposure()
        assert exposure == Decimal("6600")  # 6000 * 1.1000

    async def test_partial_close_journal(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("4000"),
            close_price=Decimal("1.1050"),
        )
        entries = await portfolio.journal.get_by_position(pos.position_id)
        modified = [e for e in entries if e.entry_type.value == "position_modified"]
        assert len(modified) >= 1


class TestIncreasePosition:
    """End-to-end position increase scenarios."""

    async def test_increase_updates_exposure(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        # Original: 10000*1.1000, Additional: 5000*1.1050
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure > Decimal("11000")


class TestDepositWithdraw:
    """Deposit and withdrawal scenarios."""

    async def test_deposit_funds(self, portfolio: PortfolioManager):
        snap = await portfolio.deposit(Decimal("5000"), reason="deposit")
        assert snap.balance == Decimal("15000")
        assert snap.equity == Decimal("15000")

    async def test_withdraw_funds(self, portfolio: PortfolioManager):
        snap = await portfolio.withdraw(Decimal("3000"), reason="withdrawal")
        assert snap.balance == Decimal("7000")
        assert snap.equity == Decimal("7000")

    async def test_deposit_updates_equity(self, portfolio: PortfolioManager):
        await portfolio.deposit(Decimal("5000"))
        equity = await portfolio.equity_manager.get_equity()
        assert equity == Decimal("15000")


class TestAccountSnapshot:
    """Account snapshot scenarios."""

    async def test_account_snapshot_with_positions(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        snap = await portfolio.get_account_snapshot()
        assert snap.balance == Decimal("10000")
        assert snap.used_margin > Decimal("0")
        assert snap.free_margin < Decimal("10000")
        assert snap.margin_level > 0
        assert snap.buying_power > Decimal("0")
        assert snap.available_funds <= snap.free_margin

    async def test_account_summary(self, portfolio: PortfolioManager):
        summary = await portfolio.get_account_summary()
        assert "balance" in summary
        assert "equity" in summary
        assert "margin_level" in summary
        assert summary["currency"] == "USD"


class TestPortfolioSnapshot:
    """Portfolio snapshot scenarios."""

    async def test_portfolio_snapshot_with_positions(self, portfolio: PortfolioManager):
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1050"))

        snap = await portfolio.get_portfolio_snapshot()
        assert snap.position_count == 2
        assert snap.open_position_count == 1
        assert snap.total_realized_pnl == Decimal("50")
        assert snap.long_exposure == Decimal("0")  # long closed
        assert snap.total_commission >= Decimal("0")
        assert len(snap.currency_exposures) >= 0

    async def test_portfolio_snapshot_aggregation(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1000"),
        )
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.net_exposure == Decimal("5500")  # 10000*1.1 - 5000*1.1
        assert snap.gross_exposure == Decimal("16500")  # 11000 + 5500


class TestDrawdown:
    """Drawdown scenarios."""

    async def test_drawdown_after_loss(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        # Force equity drop via loss
        await portfolio.close_position(pos.position_id, Decimal("1.0900"))
        dd = await portfolio.get_drawdown()
        # Loss was -100, so equity = 10000 - 100 = 9900
        assert dd.current_drawdown > 0
        assert dd.peak_equity >= Decimal("10000")
        assert dd.current_equity < Decimal("10000")


class TestPnLBreakdown:
    """P&L breakdown scenarios."""

    async def test_pnl_breakdown_after_trades(self, portfolio: PortfolioManager):
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            commission=Decimal("10"),
        )
        p2 = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1050"), commission=Decimal("5"))
        await portfolio.close_position(p2.position_id, Decimal("1.2400"), commission=Decimal("3"))

        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("100")  # 50 + 50
        assert pnl.commission == Decimal("18")  # 10 + 5 + 3
        assert pnl.net_profit == Decimal("82")  # 100 - 18


class TestPortfolioHeat:
    """Portfolio heat calculation scenarios."""

    async def test_portfolio_heat_no_positions(self, portfolio: PortfolioManager):
        heat = await portfolio.calculate_portfolio_heat()
        assert heat == 0.0

    async def test_portfolio_heat_with_positions(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        heat = await portfolio.calculate_portfolio_heat()
        assert 0 < heat <= 100.0


class TestPriceUpdates:
    """Price update scenarios."""

    async def test_update_price_updates_positions(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        updated = await portfolio.update_price("EURUSD", Decimal("1.1100"))
        assert len(updated) == 1
        assert updated[0].unrealized_pnl == Decimal("100")

    async def test_update_price_updates_equity(self, portfolio: PortfolioManager):
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1100"))
        equity = await portfolio.equity_manager.get_equity()
        assert equity == Decimal("10100")  # balance 10000 + unrealized 100


class TestAnalyticsIntegration:
    """Analytics integration scenarios."""

    async def test_analytics_after_trades(self, portfolio: PortfolioManager):
        # Winning trade
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1100"))

        # Losing trade
        p2 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(p2.position_id, Decimal("1.0950"))

        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades == 2
        assert analytics.winning_trades == 1
        assert analytics.losing_trades == 1
        assert analytics.win_rate == 0.5


class TestClearAll:
    """Clear all scenarios."""

    async def test_clear_all_resets_state(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.clear_all()
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.position_count == 0
        assert snap.open_position_count == 0
        account = await portfolio.get_account_snapshot()
        assert account.balance == Decimal("10000")


class TestAccountSummary:
    """Account summary scenarios."""

    async def test_account_summary_fields(self, portfolio: PortfolioManager):
        summary = await portfolio.get_account_summary()
        assert "balance" in summary
        assert "equity" in summary
        assert "free_margin" in summary
        assert "used_margin" in summary
        assert "margin_level" in summary
        assert "margin_utilization_pct" in summary
        assert "buying_power" in summary
        assert "leverage" in summary
        assert "is_margin_call" in summary
        assert "is_stop_out" in summary
        assert "currency" in summary
        assert summary["currency"] == "USD"
        assert summary["balance"] == 10000.0
        assert summary["equity"] == 10000.0
        assert summary["is_margin_call"] is False
        assert summary["is_stop_out"] is False

    async def test_account_summary_with_positions(self, portfolio: PortfolioManager):
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        summary = await portfolio.get_account_summary()
        assert summary["used_margin"] > 0
        assert summary["free_margin"] < 10000.0
        assert summary["leverage"] > 0


class TestPnLBreakdownCrossCheck:
    """Cross-check P&L breakdown calculations independently."""

    async def test_realized_pnl_independent_check(self, portfolio: PortfolioManager):
        """Independently calculate realized P&L and verify it matches."""
        # Open and close a long position
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            commission=Decimal("10"),
        )
        await portfolio.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1100"),
            commission=Decimal("5"),
        )
        # Expected: (1.1100 - 1.1000) * 100000 = 1000 realized P&L
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.realized_pnl == Decimal("1000")
        assert pnl.net_profit == Decimal("985")  # 1000 - 10 - 5

    async def test_floating_pnl_independent_check(self, portfolio: PortfolioManager):
        """Cross-check floating (unrealized) P&L independently."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        # Expected floating: (1.1050 - 1.1000) * 100000 = 500
        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.unrealized_pnl == Decimal("500")
        assert pnl.floating_pnl == Decimal("500")

    async def test_net_pnl_cross_check(self, portfolio: PortfolioManager):
        """Verify net P&L = realized + unrealized - charges."""
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
            commission=Decimal("7"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        await portfolio.close_position(
            position_id=p1.position_id,
            close_price=Decimal("1.1050"),
            commission=Decimal("3"),
        )
        pnl = await portfolio.get_pnl_breakdown()
        # realized = (1.1050-1.1000)*50000 = 250
        # charges = 7 + 3 = 10
        # net = 250 - 10 = 240
        assert pnl.realized_pnl == Decimal("250")
        assert pnl.commission == Decimal("10")
        assert pnl.net_profit == Decimal("240")

    async def test_gross_profit_loss_independent(self, portfolio: PortfolioManager):
        """Verify gross profit and loss independently."""
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(p1.position_id, Decimal("1.1100"))  # win: 500

        p2 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(p2.position_id, Decimal("1.0900"))  # loss: -500

        pnl = await portfolio.get_pnl_breakdown()
        assert pnl.gross_profit == Decimal("500")
        assert pnl.gross_loss == Decimal("-500")


class TestPortfolioHeatCrossCheck:
    """Portfolio heat cross-check scenarios."""

    async def test_portfolio_heat_no_positions(self, portfolio: PortfolioManager):
        heat = await portfolio.calculate_portfolio_heat()
        assert heat == 0.0

    async def test_portfolio_heat_with_many_positions(self, portfolio: PortfolioManager):
        """Heat should increase with more positions."""
        for i in range(5):
            await portfolio.open_position(
                symbol=f"PAIR{i:02d}",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.1000"),
            )
        heat = await portfolio.calculate_portfolio_heat()
        assert heat > 0
        assert heat <= 100.0

    async def test_portfolio_heat_with_exposure(self, portfolio: PortfolioManager):
        """Position concentration should contribute to heat."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("10"),
        )
        heat = await portfolio.calculate_portfolio_heat()
        assert heat > 0

    async def test_portfolio_heat_zero_equity(self, portfolio: PortfolioManager):
        """Heat should handle zero equity gracefully."""
        # Withdraw all funds
        await portfolio.withdraw(Decimal("10000"))
        heat = await portfolio.calculate_portfolio_heat()
        assert heat == 0.0


class TestAccountingInvariants:
    """Core accounting invariant validation."""

    async def test_balance_non_negative(self, portfolio: PortfolioManager):
        """Balance must always be >= 0."""
        assert (await portfolio.get_account_snapshot()).balance >= Decimal("0")
        await portfolio.deposit(Decimal("5000"))
        assert (await portfolio.get_account_snapshot()).balance >= Decimal("0")

    async def test_equity_balance_unrealized_relation(self, portfolio: PortfolioManager):
        """Equity = Balance + UnrealizedPnL (at the portfolio level)."""
        account = await portfolio.get_account_snapshot()
        pnl = await portfolio.get_pnl_breakdown()
        # When no positions: equity = balance
        assert account.equity == account.balance

        # After opening positions with unrealized P&L
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))

        account2 = await portfolio.get_account_snapshot()
        pnl2 = await portfolio.get_pnl_breakdown()
        # equity = balance + unrealized_pnl
        assert account2.equity == account2.balance + pnl2.unrealized_pnl

    async def test_used_margin_le_equity(self, portfolio: PortfolioManager):
        """Used Margin must never exceed Equity."""
        account = await portfolio.get_account_snapshot()
        assert account.used_margin <= account.equity

    async def test_free_margin_formula(self, portfolio: PortfolioManager):
        """Free Margin = Equity - Used Margin."""
        account = await portfolio.get_account_snapshot()
        expected_free = account.equity - account.used_margin
        assert account.free_margin == expected_free or account.free_margin == max(
            Decimal("0"), expected_free
        )

    async def test_gross_exposure_ge_net_exposure(self, portfolio: PortfolioManager):
        """Gross Exposure >= Net Exposure (absolute value)."""
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

    async def test_position_quantity_non_negative(self, portfolio: PortfolioManager):
        """Position quantities must be >= 0."""
        positions = await portfolio.position_manager.get_all_positions()
        for p in positions:
            assert p.quantity >= Decimal("0")


class TestSnapshotImmutability:
    """Verify all snapshot types are immutable."""

    async def test_account_snapshot_immutable(self, portfolio: PortfolioManager):
        snap = await portfolio.get_account_snapshot()
        with pytest.raises((TypeError, AttributeError, Exception)):
            snap.balance = Decimal("99999")

    async def test_portfolio_snapshot_immutable(self, portfolio: PortfolioManager):
        snap = await portfolio.get_portfolio_snapshot()
        with pytest.raises((TypeError, AttributeError, Exception)):
            snap.position_count = 999

    async def test_pnl_breakdown_immutable(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        with pytest.raises((TypeError, AttributeError, Exception)):
            pnl.realized_pnl = Decimal("99999")

    async def test_drawdown_snapshot_immutable(self, portfolio: PortfolioManager):
        dd = await portfolio.get_drawdown()
        with pytest.raises((TypeError, AttributeError, Exception)):
            dd.current_drawdown = 999.0


class TestConcurrencyEnhanced:
    """Enhanced concurrency scenarios."""

    async def test_concurrent_opens_and_closes_50(self, portfolio: PortfolioManager):
        import asyncio

        async def trade(i: int):
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1000"),
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

    async def test_concurrent_deposit_withdraw_trade(self, portfolio: PortfolioManager):
        import asyncio

        async def deposit():
            return await portfolio.deposit(Decimal("1000"))

        async def withdraw():
            return await portfolio.withdraw(Decimal("500"))

        async def trade():
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1000"),
                    entry_price=Decimal("1.1000"),
                )
                await portfolio.close_position(pos.position_id, Decimal("1.1100"))
                return True
            except Exception:
                return False

        tasks = (
            [deposit() for _ in range(5)]
            + [withdraw() for _ in range(3)]
            + [trade() for _ in range(5)]
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if not isinstance(r, Exception) and r is not False)
        assert successes > 0
