"""Tests for MarginManager — margin calculations and thresholds.

Covers:
- Margin calculation, Used/Free margin
- Margin call, Stop out, Warning
- Position margin registration/unregistration
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.margin_manager import MarginManager, MarginSnapshot
from libraries.domain.portfolio.models import MarginCallThresholds


@pytest.fixture
async def manager() -> MarginManager:
    """Create a clean MarginManager for each test."""
    m = MarginManager(
        thresholds=MarginCallThresholds(
            margin_call_level=100.0,
            stop_out_level=50.0,
            warning_level=200.0,
        ),
        currency="USD",
    )
    yield m
    await m.reset()


class TestMarginCalculation:
    """Margin calculation scenarios."""

    async def test_required_margin_basic(self, manager: MarginManager):
        margin = await manager.calculate_required_margin(
            notional_value=Decimal("100000"),
            leverage=Decimal("100"),
            margin_rate=Decimal("0.01"),
        )
        assert margin == Decimal("10")  # 100000 * 0.01 / 100

    async def test_required_margin_different_leverage(self, manager: MarginManager):
        margin = await manager.calculate_required_margin(
            notional_value=Decimal("100000"),
            leverage=Decimal("50"),
            margin_rate=Decimal("0.01"),
        )
        assert margin == Decimal("20")  # 100000 * 0.01 / 50

    async def test_required_margin_zero_leverage(self, manager: MarginManager):
        margin = await manager.calculate_required_margin(
            notional_value=Decimal("100000"),
            leverage=Decimal("0"),
            margin_rate=Decimal("0.01"),
        )
        assert margin == Decimal("1000")  # 100000 * 0.01 / 1 (min leverage)


class TestPositionMargin:
    """Position margin registration scenarios."""

    async def test_register_position_margin(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("200"))
        used = await manager.get_used_margin()
        assert used == Decimal("200")

    async def test_register_multiple_positions(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("200"))
        await manager.register_position_margin("POS-002", Decimal("300"))
        await manager.register_position_margin("POS-003", Decimal("500"))
        used = await manager.get_used_margin()
        assert used == Decimal("1000")

    async def test_register_negative_margin(self, manager: MarginManager):
        with pytest.raises(ValueError, match="Margin must be non-negative"):
            await manager.register_position_margin("POS-001", Decimal("-100"))

    async def test_unregister_position_margin(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("200"))
        await manager.register_position_margin("POS-002", Decimal("300"))
        await manager.unregister_position_margin("POS-001")
        used = await manager.get_used_margin()
        assert used == Decimal("300")

    async def test_unregister_nonexistent(self, manager: MarginManager):
        await manager.unregister_position_margin("NONEXISTENT")
        used = await manager.get_used_margin()
        assert used == Decimal("0")

    async def test_update_position_margin(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("200"))
        await manager.update_position_margin("POS-001", Decimal("500"))
        used = await manager.get_used_margin()
        assert used == Decimal("500")

    async def test_update_negative_margin(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("200"))
        with pytest.raises(ValueError, match="Margin must be non-negative"):
            await manager.update_position_margin("POS-001", Decimal("-50"))


class TestFreeMargin:
    """Free margin scenarios."""

    async def test_free_margin_no_positions(self, manager: MarginManager):
        free = await manager.get_free_margin(equity=Decimal("10000"))
        assert free == Decimal("10000")

    async def test_free_margin_with_positions(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        await manager.register_position_margin("POS-002", Decimal("3000"))
        free = await manager.get_free_margin(equity=Decimal("10000"))
        assert free == Decimal("5000")

    async def test_free_margin_exceeds_equity(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("15000"))
        free = await manager.get_free_margin(equity=Decimal("10000"))
        assert free == Decimal("0")


class TestMarginLevel:
    """Margin level calculation scenarios."""

    async def test_margin_level_no_positions(self, manager: MarginManager):
        level = await manager.get_margin_level(equity=Decimal("10000"))
        assert level == float("inf")

    async def test_margin_level_with_positions(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        level = await manager.get_margin_level(equity=Decimal("10000"))
        assert level == 500.0  # 10000/2000*100

    async def test_margin_level_exact_threshold(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("10000"))
        level = await manager.get_margin_level(equity=Decimal("10000"))
        assert level == 100.0

    async def test_margin_utilization(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        util = await manager.get_margin_utilization(equity=Decimal("10000"))
        assert util == 20.0

    async def test_margin_utilization_zero_equity(self, manager: MarginManager):
        util = await manager.get_margin_utilization(equity=Decimal("0"))
        assert util == 0.0


class TestMarginCall:
    """Margin call scenarios."""

    async def test_margin_call_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("10000"))
        assert await manager.check_margin_call(equity=Decimal("10000"))

    async def test_margin_call_not_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        assert not await manager.check_margin_call(equity=Decimal("10000"))

    async def test_margin_call_below_threshold(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("20000"))
        assert await manager.check_margin_call(equity=Decimal("10000"))


class TestStopOut:
    """Stop-out scenarios."""

    async def test_stop_out_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("20000"))
        assert await manager.check_stop_out(equity=Decimal("10000"))

    async def test_stop_out_not_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        assert not await manager.check_stop_out(equity=Decimal("10000"))

    async def test_stop_out_exact_threshold(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("20000"))
        assert await manager.check_stop_out(equity=Decimal("10000"))


class TestWarning:
    """Warning threshold scenarios."""

    async def test_warning_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("6000"))
        assert await manager.check_warning(equity=Decimal("10000"))  # level = 166.6 < 200

    async def test_warning_not_triggered(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("1000"))
        assert not await manager.check_warning(equity=Decimal("10000"))  # level = 1000 > 200


class TestSnapshot:
    """Margin snapshot scenarios."""

    async def test_get_snapshot(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert snap.required_margin == Decimal("2000")
        assert snap.used_margin == Decimal("2000")
        assert snap.free_margin == Decimal("8000")
        assert snap.equity == Decimal("10000")
        assert snap.margin_level == 500.0
        assert snap.margin_utilization_pct == 20.0
        assert not snap.margin_call_active
        assert not snap.stop_out_active

    async def test_snapshot_margin_call(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("10000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert snap.margin_call_active
        assert not snap.stop_out_active

    async def test_snapshot_stop_out(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("25000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert snap.margin_call_active
        assert snap.stop_out_active

    async def test_snapshot_no_positions(self, manager: MarginManager):
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert snap.margin_level == float("inf")
        assert snap.free_margin == Decimal("10000")

    async def test_snapshot_margin_healthy(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("1000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert snap.is_healthy
        assert not snap.is_warning
        assert not snap.is_critical

    async def test_snapshot_margin_warning(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("6000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert not snap.is_healthy
        assert snap.is_warning
        assert not snap.is_critical

    async def test_snapshot_margin_critical(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("10000"))
        snap = await manager.get_snapshot(equity=Decimal("10000"))
        assert not snap.is_healthy
        assert not snap.is_warning
        assert snap.is_critical


class TestReset:
    """Reset scenarios."""

    async def test_reset_clears_positions(self, manager: MarginManager):
        await manager.register_position_margin("POS-001", Decimal("2000"))
        await manager.reset()
        assert await manager.get_used_margin() == Decimal("0")
