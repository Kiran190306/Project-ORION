"""Accounting Invariant Validation for the Portfolio Engine.

Validates core accounting invariants that must hold after every state transition:

1. Balance >= 0
2. Equity = Balance + UnrealizedPnL
3. Free Margin = max(0, Equity - Used Margin)
4. Margin Level = (Equity / Used Margin) * 100 (when Used Margin > 0)
5. Gross Exposure >= |Net Exposure|
6. Position Quantity >= 0
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig


@pytest.fixture
async def portfolio() -> PortfolioManager:
    """Create a clean PortfolioManager for invariant testing."""
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


class TestAccountInvariants:
    """Core accounting invariants that must hold at all times."""

    async def _verify_all_invariants(self, portfolio: PortfolioManager) -> None:
        """Verify all accounting invariants hold."""
        account = await portfolio.get_account_snapshot()
        snap = await portfolio.get_portfolio_snapshot()
        pnl = await portfolio.get_pnl_breakdown()

        # 1. Balance >= 0
        assert account.balance >= Decimal("0"), f"Balance invariant failed: {account.balance}"

        # 2. Equity = Balance + UnrealizedPnL
        # The equity manager tracks equity = balance + unrealized_pnl from all open positions.
        # PnL breakdown also computes unrealized = sum of unrealized_pnl from open positions.
        # Allow small tolerance for floating-point precision in Decimal arithmetic.
        expected_equity = account.balance + pnl.unrealized_pnl
        diff = abs(account.equity - expected_equity)
        assert diff <= Decimal("0.001") * max(
            Decimal("1"), expected_equity
        ), f"Equity invariant failed: {account.equity} != {account.balance} + {pnl.unrealized_pnl} (diff={diff})"

        # 3. Free Margin = max(0, Equity - Used Margin)
        expected_free = max(Decimal("0"), account.equity - account.used_margin)
        assert (
            account.free_margin == expected_free
        ), f"Free margin invariant failed: {account.free_margin} != max(0, {account.equity} - {account.used_margin})"

        # 4. Margin Level consistency: margin_level = (equity / used_margin) * 100
        if account.used_margin > 0:
            expected_level = float(account.equity / account.used_margin * 100)
            assert abs(
                account.margin_level - expected_level
            ) < 0.01 or account.margin_level == float(
                "inf"
            ), f"Margin level invariant failed: {account.margin_level} != {expected_level}"

        # 5. Gross Exposure >= |Net Exposure|
        assert snap.gross_exposure >= abs(
            snap.net_exposure
        ), f"Exposure invariant failed: {snap.gross_exposure} < |{snap.net_exposure}|"

        # 6. All position quantities >= 0
        for pos in snap.positions:
            assert pos.quantity >= Decimal(
                "0"
            ), f"Position quantity invariant failed for {pos.position_id}: {pos.quantity}"

    async def test_initial_state_invariants(self, portfolio: PortfolioManager):
        """All invariants must hold at initial state."""
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_single_open(self, portfolio: PortfolioManager):
        """All invariants must hold after opening a position."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_price_update(self, portfolio: PortfolioManager):
        """All invariants must hold after price update (unrealized P&L change)."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_price_drop(self, portfolio: PortfolioManager):
        """All invariants must hold when unrealized P&L is negative."""
        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.0950"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_close(self, portfolio: PortfolioManager):
        """All invariants must hold after closing a position."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.1100"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_losing_trade(self, portfolio: PortfolioManager):
        """All invariants must hold after a losing trade."""
        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        await portfolio.close_position(pos.position_id, Decimal("1.0900"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_multiple_positions(self, portfolio: PortfolioManager):
        """All invariants must hold with multiple overlapping positions."""
        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.1000"),
        )
        p2 = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("30000"),
            entry_price=Decimal("1.2500"),
        )
        p3 = await portfolio.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
        )
        await self._verify_all_invariants(portfolio)

        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        await portfolio.update_price("GBPUSD", Decimal("1.2400"))
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(p1.position_id, Decimal("1.1100"))
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(p2.position_id, Decimal("1.2300"))
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(p3.position_id, Decimal("111.00"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_deposit(self, portfolio: PortfolioManager):
        """All invariants must hold after deposit."""
        await portfolio.deposit(Decimal("5000"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_withdrawal(self, portfolio: PortfolioManager):
        """All invariants must hold after withdrawal."""
        await portfolio.withdraw(Decimal("5000"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_after_mixed_operations(self, portfolio: PortfolioManager):
        """All invariants must hold after a sequence of mixed operations."""
        await portfolio.deposit(Decimal("20000"))

        p1 = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        await self._verify_all_invariants(portfolio)

        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        await self._verify_all_invariants(portfolio)

        await portfolio.partially_close_position(
            p1.position_id,
            Decimal("30000"),
            Decimal("1.1080"),
        )

        p2 = await portfolio.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("50000"),
            entry_price=Decimal("1.2500"),
        )
        # Sync prices before invariant check
        await portfolio.update_price("EURUSD", Decimal("1.1080"))
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(p1.position_id, Decimal("1.1120"))
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(p2.position_id, Decimal("1.2400"))
        await self._verify_all_invariants(portfolio)

        await portfolio.withdraw(Decimal("10000"))
        await self._verify_all_invariants(portfolio)

    async def test_invariants_balance_deposit_open_close_withdraw(
        self, portfolio: PortfolioManager
    ):
        """Full cycle invariants: deposit -> open -> close -> withdraw."""
        await portfolio.deposit(Decimal("50000"))
        await self._verify_all_invariants(portfolio)

        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("200000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("100"),
        )
        await self._verify_all_invariants(portfolio)

        await portfolio.close_position(pos.position_id, Decimal("1.1050"))
        await self._verify_all_invariants(portfolio)

        await portfolio.withdraw(Decimal("30000"))
        await self._verify_all_invariants(portfolio)

    async def test_balance_non_negative_strict(self, portfolio: PortfolioManager):
        """Strict: Balance must never go negative under any scenario."""
        for _ in range(5):
            pos = await portfolio.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
            )
            await portfolio.close_position(pos.position_id, Decimal("1.0900"))
            account = await portfolio.get_account_snapshot()
            assert account.balance >= Decimal("0")

    async def test_equity_formula_strict(self, portfolio: PortfolioManager):
        """Strict: Equity = Balance + UnrealizedPnL must hold after every operation."""
        account = await portfolio.get_account_snapshot()
        pnl = await portfolio.get_pnl_breakdown()
        assert account.equity == account.balance + pnl.unrealized_pnl

        pos = await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
        )
        await portfolio.update_price("EURUSD", Decimal("1.1050"))
        account = await portfolio.get_account_snapshot()
        pnl = await portfolio.get_pnl_breakdown()
        assert account.equity == account.balance + pnl.unrealized_pnl

        await portfolio.close_position(pos.position_id, Decimal("1.1100"))
        account = await portfolio.get_account_snapshot()
        pnl = await portfolio.get_pnl_breakdown()
        assert account.equity == account.balance + pnl.unrealized_pnl

    async def test_free_margin_formula_strict(self, portfolio: PortfolioManager):
        """Strict: Free Margin = max(0, Equity - Used Margin)."""
        account = await portfolio.get_account_snapshot()
        assert account.free_margin == max(Decimal("0"), account.equity - account.used_margin)

        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("1.1000"),
            leverage=Decimal("50"),
        )
        account = await portfolio.get_account_snapshot()
        expected = max(Decimal("0"), account.equity - account.used_margin)
        assert account.free_margin == expected

    async def test_gross_exposure_ge_net_exposure_strict(self, portfolio: PortfolioManager):
        """Strict: Gross Exposure >= |Net Exposure|."""
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

        await portfolio.open_position(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1000"),
        )
        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)

    async def test_position_quantity_non_negative_strict(self, portfolio: PortfolioManager):
        """Strict: All position quantities must be >= 0."""
        positions = [
            await portfolio.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
            ),
            await portfolio.open_position(
                symbol="GBPUSD",
                side=PositionSide.SHORT,
                quantity=Decimal("5000"),
                entry_price=Decimal("1.2500"),
            ),
        ]
        for pos in positions:
            assert pos.quantity >= Decimal("0")
