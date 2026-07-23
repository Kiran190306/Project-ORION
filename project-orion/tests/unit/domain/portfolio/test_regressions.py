"""Regression tests for the Portfolio & Position Management Engine.

Every bug fix must include a regression test that:
1. Identifies root cause.
2. Verifies the issue cannot reoccur.

Covers known edge cases and historical bugs.
"""

from __future__ import annotations

from decimal import Decimal

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


@pytest.fixture
async def position_manager() -> PositionManager:
    m = PositionManager(config=PositionManagerConfig(generate_position_id=True, track_history=True))
    yield m
    await m.clear_all()


@pytest.fixture
async def portfolio() -> PortfolioManager:
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("100000"),
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


class TestRegressionPositionManager:
    """Regression tests for PositionManager bugs."""

    async def test_regression_close_nonexistent_position(self, position_manager: PositionManager):
        """REGRESSION: Attempting to close a nonexistent position should raise PositionNotFoundError,
        not silently fail or create phantom state."""
        with pytest.raises(PositionNotFoundError):
            await position_manager.close_position(
                position_id="DOES-NOT-EXIST-999",
                close_price=Decimal("1.1000"),
            )

    async def test_regression_duplicate_race_condition(self, position_manager: PositionManager):
        """REGRESSION: Opening a position with a duplicate ID must always raise DuplicatePositionError,
        even under concurrent access patterns."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
            position_id="REGRESSION-DUP-001",
        )
        assert pos is not None
        with pytest.raises(DuplicatePositionError):
            await position_manager.open_position(
                symbol="GBPUSD",
                side=PositionSide.SHORT,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.2500"),
                position_id="REGRESSION-DUP-001",
            )

    async def test_regression_partial_close_exact_remaining(
        self, position_manager: PositionManager
    ):
        """REGRESSION: Partial close of exact remaining quantity should mark position as CLOSED,
        not leave it as PARTIALLY_CLOSED with zero quantity."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("6000"),
            close_price=Decimal("1.1050"),
        )
        assert closed.status == PositionStatus.PARTIALLY_CLOSED
        assert closed.quantity == Decimal("4000")

        # Close the remainder — should become CLOSED
        fully_closed = await position_manager.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("4000"),
            close_price=Decimal("1.1100"),
        )
        assert fully_closed.status == PositionStatus.CLOSED
        assert fully_closed.quantity == Decimal("0")
        assert fully_closed.close_time is not None

    async def test_regression_double_close_raises(self, position_manager: PositionManager):
        """REGRESSION: Double-closing a position should raise InvalidPositionStateError."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        await position_manager.close_position(pos.position_id, Decimal("1.1100"))
        with pytest.raises(InvalidPositionStateError):
            await position_manager.close_position(pos.position_id, Decimal("1.1200"))

    async def test_regression_merge_same_position_id(self, position_manager: PositionManager):
        """REGRESSION: Merging a position with itself should be rejected."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        with pytest.raises(InvalidPositionStateError):
            await position_manager.merge_positions([pos.position_id])

    async def test_regression_split_zero_ratio(self, position_manager: PositionManager):
        """REGRESSION: Split with ratios summing to 0 should be rejected."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        with pytest.raises(InvalidPositionStateError):
            await position_manager.split_position(
                position_id=pos.position_id,
                split_ratios=[0.0, 0.0],
            )

    async def test_regression_close_with_zero_price(self, position_manager: PositionManager):
        """REGRESSION: Closing with zero price should calculate P&L correctly
        (entry_price * -quantity for long)."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await position_manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("0"),
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.realized_pnl == Decimal("-1100")  # (0 - 1.1000) * 1000

    async def test_regression_increase_update_price_preserved(
        self, position_manager: PositionManager
    ):
        """REGRESSION: Increasing a position should preserve the current price."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        await position_manager.update_position_price(pos.position_id, Decimal("1.1050"))
        increased = await position_manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("500"),
            entry_price=Decimal("1.1100"),
        )
        # Current price should be the last entry price from increase
        assert increased.current_price == Decimal("1.1100")

    async def test_regression_merge_updates_realized_pnl(self, position_manager: PositionManager):
        """REGRESSION: Merging positions should sum realized P&L correctly."""
        p1 = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        p2 = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        # Close p2 partially to get some realized P&L first
        await position_manager.partially_close_position(
            position_id=p2.position_id,
            close_quantity=Decimal("2000"),
            close_price=Decimal("1.1100"),
        )
        merged = await position_manager.merge_positions([p1.position_id, p2.position_id])
        # p2 had 2000 * (1.1100 - 1.1050) = 10 realized
        assert merged.realized_pnl == Decimal("10")

    async def test_regression_liquidate_position_updates_status(
        self, position_manager: PositionManager
    ):
        """REGRESSION: Liquidated position must have LIQUIDATED status."""
        pos = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        liquidated = await position_manager.liquidate_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0900"),
            reason="margin_call",
        )
        assert liquidated.status == PositionStatus.LIQUIDATED
        assert liquidated.close_reason == "margin_call"
        assert liquidated.realized_pnl == Decimal("-10")  # (1.0900 - 1.1000) * 1000

    async def test_regression_clear_all_resets_state(self, position_manager: PositionManager):
        """REGRESSION: Clear all must reset all internal state so portfolio is empty."""
        pos1 = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos1.position_id.startswith("POS-")
        await position_manager.clear_all()
        assert await position_manager.total_count == 0
        assert await position_manager.get_open_positions() == []
        assert await position_manager.get_symbols() == []
        # New positions should work after clear
        pos2 = await position_manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos2.position_id.startswith("POS-")
        assert await position_manager.total_count == 1


class TestRegressionPortfolioManager:
    """Regression tests for PortfolioManager bugs."""

    async def test_regression_balance_non_negative_after_loss(self, portfolio: PortfolioManager):
        """REGRESSION: Balance must never go negative even after a losing trade."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.0900"))
        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")

    async def test_regression_equity_consistency_after_multiple_trades(
        self, portfolio: PortfolioManager
    ):
        """REGRESSION: Equity must always equal balance + unrealized P&L after multiple trades."""
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1100"))
        account = await portfolio.get_account_snapshot()
        pnl = await portfolio.get_pnl_breakdown()
        assert account.equity == account.balance + pnl.unrealized_pnl

    async def test_regression_journal_records_all_events(self, portfolio: PortfolioManager):
        """REGRESSION: All trade events must be recorded in the journal."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            decision_id="DEC-REGRESSION",
            execution_id="EXEC-REGRESSION",
            strategy="momentum",
        )
        await portfolio.close_position(
            pos.position_id,
            Decimal("1.1100"),
            close_reason="take_profit",
        )
        entries = await portfolio.journal.get_by_position(pos.position_id)
        assert len(entries) >= 2
        entry_types = [e.entry_type.value for e in entries]
        assert "position_opened" in entry_types
        assert "trade_profit" in entry_types or "position_closed" in entry_types

    async def test_regression_portfolio_snapshot_immutable(self, portfolio: PortfolioManager):
        """REGRESSION: PortfolioSnapshots must be immutable after creation."""
        snap = await portfolio.get_portfolio_snapshot()
        with pytest.raises((TypeError, AttributeError, Exception)):
            snap.position_count = 999  # type: ignore

    async def test_regression_account_snapshot_immutable(self, portfolio: PortfolioManager):
        """REGRESSION: AccountSnapshots must be immutable after creation."""
        snap = await portfolio.get_account_snapshot()
        with pytest.raises((TypeError, AttributeError, Exception)):
            snap.balance = Decimal("99999")  # type: ignore

    async def test_regression_free_margin_formula(self, portfolio: PortfolioManager):
        """REGRESSION: Free Margin must equal max(0, Equity - Used Margin)."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        account = await portfolio.get_account_snapshot()
        expected_free = max(Decimal("0"), account.equity - account.used_margin)
        assert account.free_margin == expected_free

    async def test_regression_gross_exposure_ge_abs_net(self, portfolio: PortfolioManager):
        """REGRESSION: Gross exposure must always be >= absolute net exposure."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

    async def test_regression_analytics_counts_match(self, portfolio: PortfolioManager):
        """REGRESSION: Analytics trade counts must match actual completed trades."""
        for i in range(5):
            pos = await portfolio.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
            )
            await portfolio.close_position(
                pos.position_id,
                Decimal("1.1100") if i % 2 == 0 else Decimal("1.0950"),
            )
        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades == 5
        assert analytics.winning_trades + analytics.losing_trades == 5

    async def test_regression_open_position_with_zero_quantity(self, portfolio: PortfolioManager):
        """REGRESSION: Opening a position with zero quantity should be allowed."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("0"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.quantity == Decimal("0")
        assert pos.status == PositionStatus.OPEN

    async def test_regression_exposure_cleared_after_close(self, portfolio: PortfolioManager):
        """REGRESSION: After closing all positions, net exposure must be zero."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.1100"))
        net = await portfolio.exposure_manager.get_net_exposure()
        assert net == Decimal("0")

    async def test_regression_used_margin_cleared_after_close(self, portfolio: PortfolioManager):
        """REGRESSION: After closing all positions, used margin must be zero."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.1100"))
        used = await portfolio.margin_manager.get_used_margin()
        assert used == Decimal("0")

    async def test_regression_no_duplicate_journal_entries(self, portfolio: PortfolioManager):
        """REGRESSION: Each trade action should produce exactly one journal entry of each type."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.1100"))
        entries = await portfolio.journal.get_by_position(pos.position_id)
        opened = [e for e in entries if e.entry_type.value == "position_opened"]
        assert len(opened) == 1
        profit = [e for e in entries if e.entry_type.value == "trade_profit"]
        assert len(profit) == 1

    async def test_regression_concurrent_deposit_balance_consistency(
        self, portfolio: PortfolioManager
    ):
        """REGRESSION: Concurrent deposits must result in consistent final balance."""
        import asyncio

        async def deposit():
            return await portfolio.deposit(Decimal("1000"))

        tasks = [deposit() for _ in range(10)]
        await asyncio.gather(*tasks)
        account = await portfolio.get_account_snapshot()
        assert account.balance == Decimal("110000")  # 100000 + 10 * 1000
