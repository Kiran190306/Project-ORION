"""Snapshot Immutability Tests for the Portfolio Engine.

All snapshot objects (AccountSnapshot, PortfolioSnapshot, PnLBreakdown, etc.)
must be immutable — frozen dataclasses that cannot be modified after creation.

This module verifies immutability for all snapshot types used in the portfolio domain.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.analytics import PortfolioAnalytics
from libraries.domain.portfolio.balance_manager import BalanceSnapshot
from libraries.domain.portfolio.equity_manager import EquitySnapshot
from libraries.domain.portfolio.exposure_manager import (
    CurrencyExposure,
    ExposureSnapshot,
    SymbolExposure,
)
from libraries.domain.portfolio.journal import JournalEntry
from libraries.domain.portfolio.margin_manager import MarginSnapshot
from libraries.domain.portfolio.models import (
    AccountSnapshot,
    CurrencyPosition,
    DrawdownSnapshot,
    PnLBreakdown,
    PortfolioSnapshot,
    Position,
    PositionSide,
    PositionStatus,
    PositionSummary,
)
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig


@pytest.fixture
async def portfolio() -> PortfolioManager:
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("100000"),
            max_leverage=Decimal("100"),
            account_currency="USD",
            track_journal=True,
            track_analytics=True,
        ),
    )
    yield p
    await p.clear_all()


def _expect_immutable(obj: object, attr: str, value: object) -> None:
    """Expect that setting an attribute on an immutable object raises an error."""
    with pytest.raises((TypeError, AttributeError, Exception)):
        setattr(obj, attr, value)


class TestAccountSnapshotImmutability:
    """AccountSnapshot must be immutable."""

    async def test_account_snapshot_immutable(self, portfolio: PortfolioManager):
        snap = await portfolio.get_account_snapshot()
        _expect_immutable(snap, "balance", Decimal("99999"))
        _expect_immutable(snap, "equity", Decimal("99999"))
        _expect_immutable(snap, "free_margin", Decimal("99999"))
        _expect_immutable(snap, "used_margin", Decimal("99999"))
        _expect_immutable(snap, "margin_level", 999.0)
        _expect_immutable(snap, "buying_power", Decimal("99999"))
        _expect_immutable(snap, "currency", "EUR")

    async def test_account_snapshot_frozen_dataclass(self):
        snap = AccountSnapshot()
        _expect_immutable(snap, "balance", Decimal("100"))


class TestPortfolioSnapshotImmutability:
    """PortfolioSnapshot must be immutable."""

    async def test_portfolio_snapshot_immutable(self, portfolio: PortfolioManager):
        snap = await portfolio.get_portfolio_snapshot()
        _expect_immutable(snap, "position_count", 999)
        _expect_immutable(snap, "open_position_count", 999)
        _expect_immutable(snap, "total_realized_pnl", Decimal("99999"))
        _expect_immutable(snap, "total_unrealized_pnl", Decimal("99999"))
        _expect_immutable(snap, "net_exposure", Decimal("99999"))
        _expect_immutable(snap, "gross_exposure", Decimal("99999"))
        _expect_immutable(snap, "long_exposure", Decimal("99999"))
        _expect_immutable(snap, "short_exposure", Decimal("99999"))


class TestPnLBreakdownImmutability:
    """PnLBreakdown must be immutable."""

    async def test_pnl_breakdown_immutable(self, portfolio: PortfolioManager):
        pnl = await portfolio.get_pnl_breakdown()
        _expect_immutable(pnl, "realized_pnl", Decimal("99999"))
        _expect_immutable(pnl, "unrealized_pnl", Decimal("99999"))
        _expect_immutable(pnl, "floating_pnl", Decimal("99999"))
        _expect_immutable(pnl, "gross_profit", Decimal("99999"))
        _expect_immutable(pnl, "gross_loss", Decimal("99999"))
        _expect_immutable(pnl, "net_profit", Decimal("99999"))
        _expect_immutable(pnl, "commission", Decimal("99999"))
        _expect_immutable(pnl, "swap", Decimal("99999"))
        _expect_immutable(pnl, "fees", Decimal("99999"))

    async def test_pnl_breakdown_frozen(self):
        pnl = PnLBreakdown()
        _expect_immutable(pnl, "realized_pnl", Decimal("100"))


class TestDrawdownSnapshotImmutability:
    """DrawdownSnapshot must be immutable."""

    async def test_drawdown_immutable(self, portfolio: PortfolioManager):
        dd = await portfolio.get_drawdown()
        _expect_immutable(dd, "current_drawdown", 999.0)
        _expect_immutable(dd, "max_drawdown", 999.0)
        _expect_immutable(dd, "peak_equity", Decimal("99999"))
        _expect_immutable(dd, "current_equity", Decimal("99999"))


class TestBalanceSnapshotImmutability:
    """BalanceSnapshot must be immutable."""

    async def test_balance_snapshot_immutable(self):
        snap = BalanceSnapshot(
            balance=Decimal("10000"),
            previous_balance=Decimal("10000"),
            change=Decimal("0"),
            change_pct=0.0,
            buying_power=Decimal("0"),
            available_funds=Decimal("10000"),
            currency="USD",
        )
        _expect_immutable(snap, "balance", Decimal("99999"))
        _expect_immutable(snap, "previous_balance", Decimal("99999"))
        _expect_immutable(snap, "change", Decimal("99999"))
        _expect_immutable(snap, "buying_power", Decimal("99999"))


class TestEquitySnapshotImmutability:
    """EquitySnapshot must be immutable."""

    async def test_equity_snapshot_immutable(self):
        snap = EquitySnapshot(
            equity=Decimal("10000"),
            balance=Decimal("10000"),
            unrealized_pnl=Decimal("0"),
            daily_change=Decimal("0"),
            weekly_change=Decimal("0"),
            monthly_change=Decimal("0"),
            peak_equity=Decimal("10000"),
            currency="USD",
        )
        _expect_immutable(snap, "equity", Decimal("99999"))
        _expect_immutable(snap, "balance", Decimal("99999"))
        _expect_immutable(snap, "unrealized_pnl", Decimal("99999"))
        _expect_immutable(snap, "peak_equity", Decimal("99999"))


class TestMarginSnapshotImmutability:
    """MarginSnapshot must be immutable."""

    async def test_margin_snapshot_immutable(self):
        snap = MarginSnapshot(
            required_margin=Decimal("1000"),
            used_margin=Decimal("1000"),
            free_margin=Decimal("9000"),
            equity=Decimal("10000"),
            margin_level=1000.0,
            margin_utilization_pct=10.0,
        )
        _expect_immutable(snap, "required_margin", Decimal("99999"))
        _expect_immutable(snap, "used_margin", Decimal("99999"))
        _expect_immutable(snap, "free_margin", Decimal("99999"))
        _expect_immutable(snap, "equity", Decimal("99999"))
        _expect_immutable(snap, "margin_level", 999.0)


class TestExposureSnapshotImmutability:
    """ExposureSnapshot must be immutable."""

    async def test_exposure_snapshot_immutable(self):
        snap = ExposureSnapshot(
            net_exposure=Decimal("100000"),
            gross_exposure=Decimal("100000"),
            long_exposure=Decimal("100000"),
            short_exposure=Decimal("0"),
            max_exposure=Decimal("100000"),
        )
        _expect_immutable(snap, "net_exposure", Decimal("99999"))
        _expect_immutable(snap, "gross_exposure", Decimal("99999"))
        _expect_immutable(snap, "long_exposure", Decimal("99999"))
        _expect_immutable(snap, "short_exposure", Decimal("99999"))
        _expect_immutable(snap, "max_exposure", Decimal("99999"))


class TestSymbolExposureImmutability:
    """SymbolExposure must be immutable."""

    async def test_symbol_exposure_immutable(self):
        exp = SymbolExposure(
            symbol="EURUSD",
            long_exposure=Decimal("100000"),
            short_exposure=Decimal("0"),
            net_exposure=Decimal("100000"),
            gross_exposure=Decimal("100000"),
            position_count=1,
        )
        _expect_immutable(exp, "symbol", "GBPUSD")
        _expect_immutable(exp, "long_exposure", Decimal("99999"))
        _expect_immutable(exp, "net_exposure", Decimal("99999"))


class TestCurrencyExposureImmutability:
    """CurrencyExposure must be immutable."""

    async def test_currency_exposure_immutable(self):
        exp = CurrencyExposure(
            currency="USD",
            long_exposure=Decimal("100000"),
            short_exposure=Decimal("0"),
            net_exposure=Decimal("100000"),
            gross_exposure=Decimal("100000"),
            position_count=1,
        )
        _expect_immutable(exp, "currency", "EUR")
        _expect_immutable(exp, "long_exposure", Decimal("99999"))


class TestPositionImmutability:
    """Position must be immutable (frozen dataclass)."""

    async def test_position_immutable(self):
        pos = Position(
            position_id="POS-TEST-001",
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        _expect_immutable(pos, "position_id", "CHANGED")
        _expect_immutable(pos, "symbol", "GBPUSD")
        _expect_immutable(pos, "quantity", Decimal("99999"))
        _expect_immutable(pos, "entry_price", Decimal("99999"))
        _expect_immutable(pos, "status", PositionStatus.CLOSED)


class TestPositionSummaryImmutability:
    """PositionSummary must be immutable."""

    async def test_position_summary_immutable(self):
        summary = PositionSummary(
            symbol="EURUSD",
            total_long_quantity=Decimal("10000"),
            total_short_quantity=Decimal("5000"),
            net_quantity=Decimal("5000"),
            unrealized_pnl=Decimal("100"),
            realized_pnl=Decimal("200"),
            position_count=2,
            active_count=2,
        )
        _expect_immutable(summary, "symbol", "GBPUSD")
        _expect_immutable(summary, "total_long_quantity", Decimal("99999"))
        _expect_immutable(summary, "net_quantity", Decimal("99999"))


class TestCurrencyPositionImmutability:
    """CurrencyPosition must be immutable."""

    async def test_currency_position_immutable(self):
        cp = CurrencyPosition(
            currency="USD",
            long_exposure=Decimal("100000"),
            short_exposure=Decimal("50000"),
            net_exposure=Decimal("50000"),
            position_count=2,
        )
        _expect_immutable(cp, "currency", "EUR")
        _expect_immutable(cp, "net_exposure", Decimal("99999"))


class TestPortfolioAnalyticsImmutability:
    """PortfolioAnalytics must be immutable."""

    async def test_portfolio_analytics_immutable(self):
        analytics = PortfolioAnalytics(
            total_trades=10,
            winning_trades=5,
            losing_trades=5,
            win_rate=0.5,
            profit_factor=2.0,
            sharpe_ratio=1.5,
        )
        _expect_immutable(analytics, "total_trades", 999)
        _expect_immutable(analytics, "winning_trades", 999)
        _expect_immutable(analytics, "win_rate", 0.99)


class TestJournalEntryImmutability:
    """JournalEntry must be immutable."""

    async def test_journal_entry_immutable(self):
        from libraries.domain.portfolio.journal import JournalEntryType

        entry = JournalEntry(
            entry_id="JRN-000001",
            entry_type=JournalEntryType.POSITION_OPENED,
            position_id="POS-001",
            symbol="EURUSD",
            quantity=Decimal("10000"),
            price=Decimal("1.1000"),
        )
        _expect_immutable(entry, "entry_id", "CHANGED")
        _expect_immutable(entry, "entry_type", JournalEntryType.POSITION_CLOSED)
        _expect_immutable(entry, "symbol", "GBPUSD")
        _expect_immutable(entry, "quantity", Decimal("99999"))


class TestDrawdownSnapshotModel:
    """DrawdownSnapshot from models must be immutable."""

    async def test_drawdown_snapshot_model_immutable(self):
        dd = DrawdownSnapshot(
            current_drawdown=10.0,
            max_drawdown=25.0,
            peak_equity=Decimal("100000"),
            current_equity=Decimal("90000"),
            recovery_factor=0.5,
        )
        _expect_immutable(dd, "current_drawdown", 999.0)
        _expect_immutable(dd, "max_drawdown", 999.0)
        _expect_immutable(dd, "peak_equity", Decimal("99999"))
        _expect_immutable(dd, "current_equity", Decimal("99999"))
