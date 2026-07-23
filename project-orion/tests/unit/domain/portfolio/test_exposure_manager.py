"""Tests for ExposureManager — portfolio exposure tracking.

Covers:
- Net, Gross, Long, Short exposure
- Symbol exposure, Currency exposure
- Max exposure, Snapshot
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.portfolio.exposure_manager import (
    ExposureManager,
    ExposureSnapshot,
    SymbolExposure,
)
from libraries.domain.portfolio.models import PositionSide


@pytest.fixture
async def manager() -> ExposureManager:
    """Create a clean ExposureManager for each test."""
    m = ExposureManager()
    yield m
    await m.clear_all()


class TestAddExposure:
    """Exposure addition scenarios."""

    async def test_add_long_exposure(self, manager: ExposureManager):
        await manager.add_exposure(
            symbol="EURUSD",
            side=PositionSide.LONG,
            notional_value=Decimal("100000"),
            currency="USD",
        )
        net = await manager.get_net_exposure()
        gross = await manager.get_gross_exposure()
        long_exp = await manager.get_long_exposure()
        short_exp = await manager.get_short_exposure()
        assert net == Decimal("100000")
        assert gross == Decimal("100000")
        assert long_exp == Decimal("100000")
        assert short_exp == Decimal("0")

    async def test_add_short_exposure(self, manager: ExposureManager):
        await manager.add_exposure(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            notional_value=Decimal("50000"),
            currency="USD",
        )
        net = await manager.get_net_exposure()
        gross = await manager.get_gross_exposure()
        assert net == Decimal("-50000")
        assert gross == Decimal("50000")

    async def test_add_multiple_symbols(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.add_exposure("GBPUSD", PositionSide.SHORT, Decimal("50000"))
        await manager.add_exposure("USDJPY", PositionSide.LONG, Decimal("200000"))
        net = await manager.get_net_exposure()
        gross = await manager.get_gross_exposure()
        assert net == Decimal("250000")  # 100000 - 50000 + 200000
        assert gross == Decimal("350000")  # 100000 + 50000 + 200000


class TestRemoveExposure:
    """Exposure removal scenarios."""

    async def test_remove_exposure(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.remove_exposure("EURUSD", PositionSide.LONG, Decimal("40000"))
        net = await manager.get_net_exposure()
        assert net == Decimal("60000")

    async def test_remove_beyond_exposure(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.remove_exposure("EURUSD", PositionSide.LONG, Decimal("200000"))
        net = await manager.get_net_exposure()
        assert net == Decimal("0")

    async def test_remove_nonexistent(self, manager: ExposureManager):
        await manager.remove_exposure("EURUSD", PositionSide.LONG, Decimal("50000"))
        net = await manager.get_net_exposure()
        assert net == Decimal("0")


class TestUpdateExposure:
    """Exposure update scenarios."""

    async def test_update_exposure_increase(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.update_exposure(
            "EURUSD", PositionSide.LONG, Decimal("100000"), Decimal("150000")
        )
        gross = await manager.get_gross_exposure()
        assert gross == Decimal("150000")

    async def test_update_exposure_decrease(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.update_exposure(
            "EURUSD", PositionSide.LONG, Decimal("100000"), Decimal("50000")
        )
        gross = await manager.get_gross_exposure()
        assert gross == Decimal("50000")

    async def test_update_exposure_no_change(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.update_exposure(
            "EURUSD", PositionSide.LONG, Decimal("100000"), Decimal("100000")
        )
        gross = await manager.get_gross_exposure()
        assert gross == Decimal("100000")


class TestSymbolExposure:
    """Per-symbol exposure scenarios."""

    async def test_get_symbol_exposure(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        sym = await manager.get_symbol_exposure("EURUSD")
        assert sym is not None
        assert sym.symbol == "EURUSD"
        assert sym.long_exposure == Decimal("100000")
        assert sym.short_exposure == Decimal("0")
        assert sym.net_exposure == Decimal("100000")
        assert sym.gross_exposure == Decimal("100000")
        assert sym.position_count == 1

    async def test_get_symbol_exposure_nonexistent(self, manager: ExposureManager):
        sym = await manager.get_symbol_exposure("NONEXISTENT")
        assert sym is None

    async def test_symbol_exposure_properties(self, manager: ExposureManager):
        sym = SymbolExposure(symbol="EURUSD", net_exposure=Decimal("50000"))
        assert sym.is_long
        assert not sym.is_short
        assert not sym.is_flat

        sym2 = SymbolExposure(symbol="EURUSD", net_exposure=Decimal("-30000"))
        assert sym2.is_short
        assert not sym2.is_long

        sym3 = SymbolExposure(symbol="EURUSD", net_exposure=Decimal("0"))
        assert sym3.is_flat

    async def test_all_symbol_exposures(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.add_exposure("GBPUSD", PositionSide.SHORT, Decimal("50000"))
        all_sym = await manager.get_all_symbol_exposures()
        assert len(all_sym) == 2


class TestCurrencyExposure:
    """Per-currency exposure scenarios."""

    async def test_get_currency_exposure(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"), currency="EUR")
        curr = await manager.get_currency_exposure("EUR")
        assert curr is not None
        assert curr.currency == "EUR"
        assert curr.long_exposure == Decimal("100000")

    async def test_get_currency_exposure_nonexistent(self, manager: ExposureManager):
        curr = await manager.get_currency_exposure("XYZ")
        assert curr is None

    async def test_all_currency_exposures(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"), currency="EUR")
        await manager.add_exposure("GBPUSD", PositionSide.SHORT, Decimal("50000"), currency="GBP")
        all_curr = await manager.get_all_currency_exposures()
        assert len(all_curr) == 2


class TestMaxExposure:
    """Maximum exposure tracking scenarios."""

    async def test_max_exposure(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        assert await manager.get_max_exposure() == Decimal("100000")

    async def test_max_exposure_increases(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("50000"))
        assert await manager.get_max_exposure() == Decimal("50000")
        await manager.add_exposure("GBPUSD", PositionSide.LONG, Decimal("100000"))
        assert await manager.get_max_exposure() == Decimal("100000")

    async def test_max_exposure_does_not_decrease(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.add_exposure("GBPUSD", PositionSide.LONG, Decimal("50000"))
        await manager.remove_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        assert await manager.get_max_exposure() == Decimal("100000")


class TestSnapshot:
    """Exposure snapshot scenarios."""

    async def test_get_snapshot_empty(self, manager: ExposureManager):
        snap = await manager.get_snapshot()
        assert snap.net_exposure == Decimal("0")
        assert snap.gross_exposure == Decimal("0")
        assert snap.long_exposure == Decimal("0")
        assert snap.short_exposure == Decimal("0")
        assert snap.position_count == 0

    async def test_get_snapshot_with_positions(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.add_exposure("GBPUSD", PositionSide.SHORT, Decimal("50000"))
        snap = await manager.get_snapshot()
        assert snap.net_exposure == Decimal("50000")
        assert snap.gross_exposure == Decimal("150000")
        assert snap.long_exposure == Decimal("100000")
        assert snap.short_exposure == Decimal("50000")
        assert snap.position_count == 2
        assert len(snap.symbol_exposures) == 2

    async def test_snapshot_types(self, manager: ExposureManager):
        snap = await manager.get_snapshot()
        assert isinstance(snap, ExposureSnapshot)
        assert hasattr(snap, "timestamp")


class TestClear:
    """Clear operations."""

    async def test_clear_symbol(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.clear_exposure("EURUSD")
        sym = await manager.get_symbol_exposure("EURUSD")
        assert sym is None

    async def test_clear_all(self, manager: ExposureManager):
        await manager.add_exposure("EURUSD", PositionSide.LONG, Decimal("100000"))
        await manager.add_exposure("GBPUSD", PositionSide.SHORT, Decimal("50000"))
        await manager.clear_all()
        assert await manager.get_net_exposure() == Decimal("0")
        assert await manager.get_max_exposure() == Decimal("0")
