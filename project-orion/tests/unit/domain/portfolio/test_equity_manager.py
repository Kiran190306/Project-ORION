"""Tests for EquityManager — equity tracking and periodic changes.

Covers:
- Equity updates, Peak equity tracking
- Daily/Weekly/Monthly change tracking
- Snapshots, Resets
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from libraries.domain.portfolio.equity_manager import EquityManager


@pytest.fixture
async def manager() -> EquityManager:
    """Create a clean EquityManager for each test."""
    m = EquityManager(initial_equity=Decimal("10000"), currency="USD")
    yield m
    await m.reset()


class TestInitialState:
    """Initial state scenarios."""

    async def test_initial_equity(self, manager: EquityManager):
        assert await manager.get_equity() == Decimal("10000")

    async def test_initial_peak_equity(self, manager: EquityManager):
        assert await manager.get_peak_equity() == Decimal("10000")


class TestUpdate:
    """Equity update scenarios."""

    async def test_update_with_unrealized_pnl(self, manager: EquityManager):
        snap = await manager.update(
            balance=Decimal("10000"),
            unrealized_pnl=Decimal("500"),
        )
        assert snap.equity == Decimal("10500")
        assert snap.balance == Decimal("10000")
        assert snap.unrealized_pnl == Decimal("500")
        assert snap.peak_equity == Decimal("10500")  # New peak

    async def test_update_no_unrealized(self, manager: EquityManager):
        snap = await manager.update(balance=Decimal("11000"))
        assert snap.equity == Decimal("11000")
        assert snap.peak_equity == Decimal("11000")

    async def test_update_decrease(self, manager: EquityManager):
        snap = await manager.update(
            balance=Decimal("8000"),
            unrealized_pnl=Decimal("-500"),
        )
        assert snap.equity == Decimal("7500")
        assert snap.peak_equity == Decimal("10000")  # Peak unchanged

    async def test_update_negative_unrealized(self, manager: EquityManager):
        snap = await manager.update(
            balance=Decimal("10000"),
            unrealized_pnl=Decimal("-2000"),
        )
        assert snap.equity == Decimal("8000")

    async def test_multiple_updates(self, manager: EquityManager):
        await manager.update(balance=Decimal("11000"))
        await manager.update(balance=Decimal("12000"))
        snap = await manager.update(balance=Decimal("13000"))
        assert snap.equity == Decimal("13000")
        assert snap.peak_equity == Decimal("13000")


class TestPeriodicChanges:
    """Periodic change tracking scenarios."""

    async def test_daily_change(self, manager: EquityManager):
        snap = await manager.update(
            balance=Decimal("10500"),
            unrealized_pnl=Decimal("500"),
        )
        assert snap.equity == Decimal("11000")
        assert snap.daily_change == Decimal("1000")  # 11000 - 10000
        assert snap.daily_change_pct == 10.0

    async def test_daily_change_negative(self, manager: EquityManager):
        snap = await manager.update(balance=Decimal("9000"))
        assert snap.daily_change == Decimal("-1000")
        assert snap.daily_change_pct == -10.0

    async def test_weekly_change(self, manager: EquityManager):
        snap = await manager.update(balance=Decimal("12000"))
        assert snap.weekly_change == Decimal("2000")

    async def test_monthly_change(self, manager: EquityManager):
        snap = await manager.update(balance=Decimal("15000"))
        assert snap.monthly_change == Decimal("5000")


class TestPeakEquity:
    """Peak equity tracking scenarios."""

    async def test_peak_equity_increases(self, manager: EquityManager):
        await manager.update(balance=Decimal("11000"))
        await manager.update(balance=Decimal("10500"))
        peak = await manager.get_peak_equity()
        assert peak == Decimal("11000")

    async def test_peak_equity_unchanged(self, manager: EquityManager):
        await manager.update(balance=Decimal("9000"))
        await manager.update(balance=Decimal("8000"))
        peak = await manager.get_peak_equity()
        assert peak == Decimal("10000")


class TestSnapshot:
    """Equity snapshot scenarios."""

    async def test_get_snapshot(self, manager: EquityManager):
        await manager.update(balance=Decimal("12000"), unrealized_pnl=Decimal("500"))
        snap = await manager.get_snapshot(unrealized_pnl=Decimal("500"))
        assert snap.equity == Decimal("12500")
        assert snap.balance == Decimal("12000")
        assert snap.unrealized_pnl == Decimal("500")
        assert snap.peak_equity == Decimal("12500")
        assert snap.currency == "USD"

    async def test_snapshot_no_updates(self, manager: EquityManager):
        snap = await manager.get_snapshot()
        assert snap.equity == Decimal("10000")
        assert snap.balance == Decimal("10000")
        assert snap.peak_equity == Decimal("10000")


class TestReset:
    """Reset scenarios."""

    async def test_reset_default(self, manager: EquityManager):
        await manager.update(balance=Decimal("15000"))
        await manager.reset()
        assert await manager.get_equity() == Decimal("0")
        assert await manager.get_peak_equity() == Decimal("0")

    async def test_reset_with_value(self, manager: EquityManager):
        await manager.update(balance=Decimal("15000"))
        await manager.reset(equity=Decimal("5000"))
        assert await manager.get_equity() == Decimal("5000")
        assert await manager.get_peak_equity() == Decimal("5000")
