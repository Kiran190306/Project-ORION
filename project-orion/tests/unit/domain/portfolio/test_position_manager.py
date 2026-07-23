"""Tests for PositionManager — all position operations.

Covers:
- Open, Close, Partial Close, Increase, Reduce
- Merge, Split, Forced Close, Liquidation
- Position history, O(1) lookups, error handling
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
from libraries.domain.portfolio.position_manager import PositionManager, PositionManagerConfig


@pytest.fixture
async def manager() -> PositionManager:
    """Create a clean PositionManager for each test."""
    m = PositionManager(config=PositionManagerConfig(generate_position_id=True, track_history=True))
    yield m
    await m.clear_all()


@pytest.fixture
async def manager_no_history() -> PositionManager:
    """PositionManager without history tracking."""
    m = PositionManager(config=PositionManagerConfig(track_history=False))
    yield m
    await m.clear_all()


class TestOpenPosition:
    """Position opening scenarios."""

    async def test_open_long_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.symbol == "EURUSD"
        assert pos.is_long
        assert pos.status == PositionStatus.OPEN
        assert pos.quantity == Decimal("10000")
        assert pos.initial_quantity == Decimal("10000")
        assert pos.entry_price == Decimal("1.1000")
        assert pos.current_price == Decimal("1.1000")
        assert pos.position_id.startswith("POS-")
        assert pos.open_time is not None

    async def test_open_short_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        assert pos.is_short
        assert pos.symbol == "GBPUSD"
        assert pos.quantity == Decimal("5000")

    async def test_open_with_custom_id(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="USDJPY",
            side=PositionSide.LONG,
            quantity=Decimal("100000"),
            entry_price=Decimal("110.50"),
            position_id="MY-POS-001",
        )
        assert pos.position_id == "MY-POS-001"

    async def test_open_with_all_options(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
            stop_loss=Decimal("1.0950"),
            take_profit=Decimal("1.1100"),
            decision_id="DEC-001",
            execution_id="EXEC-001",
            strategy="momentum",
            currency="USD",
            broker="IB",
            leverage=Decimal("50"),
            commission=Decimal("5"),
            swap=Decimal("-1"),
            fees=Decimal("0.5"),
            margin_used=Decimal("200"),
            tags=("forex", "eur"),
            metadata={"source": "test"},
        )
        assert pos.stop_loss == Decimal("1.0950")
        assert pos.take_profit == Decimal("1.1100")
        assert pos.decision_id == "DEC-001"
        assert pos.execution_id == "EXEC-001"
        assert pos.strategy == "momentum"
        assert pos.broker == "IB"
        assert pos.leverage == Decimal("50")
        assert pos.commission == Decimal("5")
        assert pos.swap == Decimal("-1")
        assert pos.fees == Decimal("0.5")
        assert pos.margin_used == Decimal("200")
        assert pos.tags == ("forex", "eur")
        assert pos.metadata["source"] == "test"

    async def test_duplicate_position_id(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
            position_id="DUP-001",
        )
        with pytest.raises(DuplicatePositionError):
            await manager.open_position(
                symbol="GBPUSD",
                side=PositionSide.SHORT,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.25"),
                position_id="DUP-001",
            )


class TestClosePosition:
    """Position closing scenarios."""

    async def test_close_long_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1050"),
            close_reason="take_profit",
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.quantity == Decimal("0")
        assert closed.realized_pnl == Decimal("50")  # (1.1050 - 1.1000) * 10000
        assert closed.close_time is not None
        assert closed.close_reason == "take_profit"

    async def test_close_short_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        closed = await manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.2400"),
            close_reason="profit",
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.realized_pnl == Decimal("50")  # (1.2500 - 1.2400) * 5000

    async def test_close_nonexistent_position(self, manager: PositionManager):
        with pytest.raises(PositionNotFoundError):
            await manager.close_position(
                position_id="DOES-NOT-EXIST",
                close_price=Decimal("1.10"),
            )

    async def test_close_already_closed_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.12"))

    async def test_close_with_commission_swap_fees(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.1050"),
            close_reason="tp",
            commission=Decimal("5"),
            swap=Decimal("-2"),
            fees=Decimal("1"),
        )
        assert closed.commission == Decimal("5")
        assert closed.swap == Decimal("-2")
        assert closed.fees == Decimal("1")


class TestPartialClose:
    """Partial close scenarios."""

    async def test_partial_close(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await manager.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("4000"),
            close_price=Decimal("1.1050"),
        )
        assert closed.status == PositionStatus.PARTIALLY_CLOSED
        assert closed.quantity == Decimal("6000")
        assert closed.realized_pnl == Decimal("20")  # (1.1050-1.1000)*4000
        assert closed.close_time is None  # still partially open

    async def test_partial_close_exact_remaining(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await manager.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("10000"),
            close_price=Decimal("1.1050"),
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.quantity == Decimal("0")
        assert closed.close_time is not None

    async def test_partial_close_exceeds_quantity(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(PositionSizeError):
            await manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("2000"),
                close_price=Decimal("1.11"),
            )

    async def test_partial_close_zero_quantity(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(PositionSizeError):
            await manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("0"),
                close_price=Decimal("1.11"),
            )

    async def test_partial_close_closed_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.partially_close_position(
                position_id=pos.position_id,
                close_quantity=Decimal("500"),
                close_price=Decimal("1.12"),
            )


class TestIncreasePosition:
    """Position increase scenarios."""

    async def test_increase_long_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        increased = await manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        assert increased.quantity == Decimal("15000")
        # Weighted avg: (10000*1.1000 + 5000*1.1050) / 15000
        expected_avg = (
            Decimal("10000") * Decimal("1.1000") + Decimal("5000") * Decimal("1.1050")
        ) / Decimal("15000")
        assert increased.entry_price == expected_avg
        assert increased.initial_quantity == Decimal("15000")

    async def test_increase_inactive_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.increase_position(
                position_id=pos.position_id,
                additional_quantity=Decimal("500"),
                entry_price=Decimal("1.12"),
            )

    async def test_increase_with_costs(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        increased = await manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
            commission=Decimal("3"),
            swap=Decimal("-1"),
            fees=Decimal("0.5"),
        )
        assert increased.commission == Decimal("3")
        assert increased.swap == Decimal("-1")
        assert increased.fees == Decimal("0.5")


class TestReducePosition:
    """Position reduction scenarios."""

    async def test_reduce_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        reduced = await manager.reduce_position(
            position_id=pos.position_id,
            reduce_quantity=Decimal("3000"),
            close_price=Decimal("1.1050"),
        )
        assert reduced.quantity == Decimal("7000")
        assert reduced.realized_pnl == Decimal("15")  # (1.1050-1.1000)*3000

    async def test_reduce_full_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1000"),
        )
        reduced = await manager.reduce_position(
            position_id=pos.position_id,
            reduce_quantity=Decimal("5000"),
            close_price=Decimal("1.1100"),
        )
        assert reduced.status == PositionStatus.CLOSED
        assert reduced.close_reason == "position_reduced"


class TestMergePositions:
    """Position merge scenarios."""

    async def test_merge_two_positions(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        p2 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        merged = await manager.merge_positions([p1.position_id, p2.position_id])
        assert merged.quantity == Decimal("15000")
        expected_avg = (
            Decimal("10000") * Decimal("1.1000") + Decimal("5000") * Decimal("1.1050")
        ) / Decimal("15000")
        assert merged.entry_price == expected_avg

        # Second position should be closed as merged
        p2_closed = await manager.get_position(p2.position_id)
        assert p2_closed is not None
        assert p2_closed.status == PositionStatus.CLOSED
        assert p2_closed.close_reason == "merged"

    async def test_merge_mismatched_symbols(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        p2 = await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.25"),
        )
        with pytest.raises(InvalidPositionStateError):
            await manager.merge_positions([p1.position_id, p2.position_id])

    async def test_merge_mismatched_sides(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        p2 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(InvalidPositionStateError):
            await manager.merge_positions([p1.position_id, p2.position_id])

    async def test_merge_less_than_two(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(InvalidPositionStateError):
            await manager.merge_positions([p1.position_id])

    async def test_merge_closed_position(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=p1.position_id, close_price=Decimal("1.11"))
        p2 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        with pytest.raises(InvalidPositionStateError):
            await manager.merge_positions([p1.position_id, p2.position_id])


class TestSplitPosition:
    """Position split scenarios."""

    async def test_split_into_two(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        results = await manager.split_position(
            position_id=pos.position_id,
            split_ratios=[0.6, 0.4],
        )
        assert len(results) == 2
        assert results[0].quantity == Decimal("6000")
        assert results[1].quantity == Decimal("4000")
        assert results[0].entry_price == Decimal("1.1000")
        assert results[0].position_id == pos.position_id  # Original ID kept

    async def test_split_into_three(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        results = await manager.split_position(
            position_id=pos.position_id,
            split_ratios=[0.5, 0.25, 0.25],
        )
        assert len(results) == 3
        assert results[0].quantity == Decimal("5000")
        assert results[1].quantity == Decimal("2500")
        assert results[2].quantity == Decimal("2500")

    async def test_split_invalid_ratios(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        with pytest.raises(InvalidPositionStateError):
            await manager.split_position(
                position_id=pos.position_id,
                split_ratios=[0.5, 0.3],  # sums to 0.8, not 1.0
            )

    async def test_split_closed_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.split_position(
                position_id=pos.position_id,
                split_ratios=[1.0],
            )


class TestForcedClose:
    """Forced close scenarios."""

    async def test_forced_close(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        closed = await manager.forced_close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0950"),
            reason="risk_policy_violation",
        )
        assert closed.status == PositionStatus.FORCED_CLOSE
        assert closed.close_reason == "risk_policy_violation"
        assert closed.realized_pnl == Decimal("-50")  # loss

    async def test_forced_close_already_closed(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.forced_close_position(
                position_id=pos.position_id,
                close_price=Decimal("1.09"),
            )


class TestLiquidation:
    """Position liquidation scenarios."""

    async def test_liquidate_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        liq = await manager.liquidate_position(
            position_id=pos.position_id,
            close_price=Decimal("1.0900"),
            reason="margin_call",
        )
        assert liq.status == PositionStatus.LIQUIDATED
        assert liq.close_reason == "margin_call"
        assert liq.realized_pnl == Decimal("-100")  # (1.0900-1.1000)*10000

    async def test_liquidate_already_closed(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.liquidate_position(
                position_id=pos.position_id,
                close_price=Decimal("1.09"),
            )


class TestPositionQueries:
    """Position query scenarios."""

    async def test_get_position_by_id(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        found = await manager.get_position(pos.position_id)
        assert found is not None
        assert found.position_id == pos.position_id

    async def test_get_position_not_found(self, manager: PositionManager):
        found = await manager.get_position("NONEXISTENT")
        assert found is None

    async def test_get_position_or_raise(self, manager: PositionManager):
        with pytest.raises(PositionNotFoundError):
            await manager.get_position_or_raise("NONEXISTENT")

    async def test_get_positions_by_symbol(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("3000"),
            entry_price=Decimal("1.2500"),
        )
        positions = await manager.get_positions_by_symbol("EURUSD")
        assert len(positions) == 2

    async def test_get_all_positions(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        all_pos = await manager.get_all_positions()
        assert len(all_pos) == 2

    async def test_get_open_positions(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        await manager.close_position(position_id=p1.position_id, close_price=Decimal("1.11"))
        open_pos = await manager.get_open_positions()
        assert len(open_pos) == 1
        assert open_pos[0].symbol == "GBPUSD"

    async def test_get_closed_positions(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.close_position(position_id=p1.position_id, close_price=Decimal("1.11"))
        closed = await manager.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].position_id == p1.position_id

    async def test_position_exists(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        assert await manager.position_exists(pos.position_id)
        assert not await manager.position_exists("NONEXISTENT")

    async def test_get_symbols(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        symbols = await manager.get_symbols()
        assert "EURUSD" in symbols
        assert "GBPUSD" in symbols

    async def test_position_summary(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        summary = await manager.get_position_summary("EURUSD")
        assert summary.symbol == "EURUSD"
        assert summary.total_long_quantity == Decimal("15000")
        assert summary.active_count == 2

    async def test_open_count_property(self, manager: PositionManager):
        p1 = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        count = await manager.open_count
        assert count == 2
        await manager.close_position(position_id=p1.position_id, close_price=Decimal("1.11"))
        count = await manager.open_count
        assert count == 1

    async def test_total_count_property(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        assert await manager.total_count == 1
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        assert await manager.total_count == 2


class TestPositionUpdates:
    """Position update scenarios."""

    async def test_update_price_long(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        updated = await manager.update_position_price(
            position_id=pos.position_id,
            current_price=Decimal("1.1100"),
        )
        assert updated.current_price == Decimal("1.1100")
        assert updated.unrealized_pnl == Decimal("100")  # (1.1100-1.1000)*10000

    async def test_update_price_short(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        updated = await manager.update_position_price(
            position_id=pos.position_id,
            current_price=Decimal("1.2400"),
        )
        assert updated.unrealized_pnl == Decimal("50")  # (1.2500-1.2400)*5000

    async def test_update_price_closed_position(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        updated = await manager.update_position_price(
            position_id=pos.position_id,
            current_price=Decimal("1.12"),
        )
        # Should return the closed position unchanged
        assert updated.status == PositionStatus.CLOSED

    async def test_update_stop_loss(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        updated = await manager.update_position_stop_loss(
            position_id=pos.position_id,
            stop_loss=Decimal("1.0950"),
        )
        assert updated.stop_loss == Decimal("1.0950")

    async def test_update_stop_loss_closed(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.update_position_stop_loss(
                position_id=pos.position_id,
                stop_loss=Decimal("1.09"),
            )

    async def test_update_take_profit(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        updated = await manager.update_position_take_profit(
            position_id=pos.position_id,
            take_profit=Decimal("1.1100"),
        )
        assert updated.take_profit == Decimal("1.1100")

    async def test_update_take_profit_closed(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        await manager.close_position(position_id=pos.position_id, close_price=Decimal("1.11"))
        with pytest.raises(InvalidPositionStateError):
            await manager.update_position_take_profit(
                position_id=pos.position_id,
                take_profit=Decimal("1.12"),
            )


class TestPositionHistory:
    """Position history scenarios."""

    async def test_history_tracking(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("5000"),
            entry_price=Decimal("1.1050"),
        )
        history = await manager.get_position_history(pos.position_id)
        assert len(history) == 2  # open + increase

    async def test_history_no_tracking(self, manager_no_history: PositionManager):
        pos = await manager_no_history.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager_no_history.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.11"),
        )
        history = await manager_no_history.get_position_history(pos.position_id)
        assert len(history) == 0

    async def test_history_not_found(self, manager: PositionManager):
        with pytest.raises(PositionNotFoundError):
            await manager.get_position_history("NONEXISTENT")


class TestConcurrency:
    """Concurrent operations on PositionManager."""

    async def test_concurrent_position_opens(self, manager: PositionManager):
        async def open_pos(symbol: str, side: PositionSide, qty: Decimal, price: Decimal):
            return await manager.open_position(
                symbol=symbol,
                side=side,
                quantity=qty,
                entry_price=price,
            )

        import asyncio

        tasks = [
            open_pos("EURUSD", PositionSide.LONG, Decimal("10000"), Decimal("1.10")),
            open_pos("GBPUSD", PositionSide.SHORT, Decimal("5000"), Decimal("1.25")),
            open_pos("USDJPY", PositionSide.LONG, Decimal("100000"), Decimal("110.50")),
            open_pos("AUDUSD", PositionSide.SHORT, Decimal("8000"), Decimal("0.75")),
            open_pos("NZDUSD", PositionSide.LONG, Decimal("6000"), Decimal("0.65")),
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5
        assert await manager.total_count == 5

    async def test_concurrent_updates(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        async def update_price(price: Decimal):
            return await manager.update_position_price(
                position_id=pos.position_id,
                current_price=price,
            )

        import asyncio

        tasks = [
            update_price(Decimal("1.1010")),
            update_price(Decimal("1.1020")),
            update_price(Decimal("1.1030")),
            update_price(Decimal("1.1040")),
            update_price(Decimal("1.1050")),
        ]
        await asyncio.gather(*tasks)
        # Final price should be one of the updates
        final = await manager.get_position(pos.position_id)
        assert final is not None
        assert final.current_price in (
            Decimal("1.1010"),
            Decimal("1.1020"),
            Decimal("1.1030"),
            Decimal("1.1040"),
            Decimal("1.1050"),
        )

    async def test_concurrent_close_and_update(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )

        import asyncio

        async def close_it():
            return await manager.close_position(
                position_id=pos.position_id,
                close_price=Decimal("1.11"),
            )

        async def update_it():
            return await manager.update_position_price(
                position_id=pos.position_id,
                current_price=Decimal("1.1050"),
            )

        results = await asyncio.gather(close_it(), update_it(), return_exceptions=True)
        # At least one should succeed
        non_exceptions = [r for r in results if not isinstance(r, Exception)]
        assert len(non_exceptions) > 0


class TestEdgeCases:
    """Edge cases for PositionManager."""

    async def test_empty_portfolio(self, manager: PositionManager):
        assert await manager.open_count == 0
        assert await manager.total_count == 0
        assert await manager.get_all_positions() == []
        assert await manager.get_open_positions() == []
        assert await manager.get_symbols() == []

    async def test_large_quantity(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000000000"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.quantity == Decimal("1000000000")

    async def test_small_quantity(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("0.01"),
            entry_price=Decimal("1.1000"),
        )
        assert pos.quantity == Decimal("0.01")

    async def test_clear_all(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="GBPUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.2500"),
        )
        await manager.clear_all()
        assert await manager.total_count == 0
        assert await manager.get_symbols() == []

    async def test_config_generate_id_false(self):
        m = PositionManager(config=PositionManagerConfig(generate_position_id=False))
        with pytest.raises((ValueError, TypeError)):  # Will fail with empty string or similar
            await m.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("1000"),
                entry_price=Decimal("1.10"),
            )
        await m.clear_all()

    async def test_metadata_update_on_close(self, manager: PositionManager):
        """Verify metadata is updated on close."""
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
            metadata={"source": "test", "batch": "A"},
        )
        closed = await manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.11"),
            metadata={"close_reason_detail": "target_hit"},
        )
        assert closed.metadata["source"] == "test"
        assert closed.metadata["close_reason_detail"] == "target_hit"

    async def test_metadata_update_on_partial_close(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
            metadata={"strategy": "momentum"},
        )
        closed = await manager.partially_close_position(
            position_id=pos.position_id,
            close_quantity=Decimal("500"),
            close_price=Decimal("1.11"),
            metadata={"partial_reason": "reduce_risk"},
        )
        assert closed.metadata["strategy"] == "momentum"
        assert closed.metadata["partial_reason"] == "reduce_risk"

    async def test_increase_zero_additional(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        increased = await manager.increase_position(
            position_id=pos.position_id,
            additional_quantity=Decimal("0"),
            entry_price=Decimal("1.11"),
        )
        # Weighted average with zero additional = same price
        assert increased.quantity == Decimal("1000")
        assert increased.entry_price == Decimal("1.10")

    async def test_close_position_without_reason(self, manager: PositionManager):
        pos = await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("1000"),
            entry_price=Decimal("1.10"),
        )
        closed = await manager.close_position(
            position_id=pos.position_id,
            close_price=Decimal("1.11"),
        )
        assert closed.status == PositionStatus.CLOSED
        assert closed.close_reason == ""

    async def test_position_summary_with_shorts(self, manager: PositionManager):
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.LONG,
            quantity=Decimal("10000"),
            entry_price=Decimal("1.1000"),
        )
        await manager.open_position(
            symbol="EURUSD",
            side=PositionSide.SHORT,
            quantity=Decimal("5000"),
            entry_price=Decimal("1.1000"),
        )
        summary = await manager.get_position_summary("EURUSD")
        assert summary.total_long_quantity == Decimal("10000")
        assert summary.total_short_quantity == Decimal("5000")
        assert summary.net_quantity == Decimal("5000")
        assert summary.avg_long_price == Decimal("1.1000")
        assert summary.avg_short_price == Decimal("1.1000")

    async def test_config_property(self, manager: PositionManager):
        assert manager.config is not None
        assert manager.config.generate_position_id is True
        assert manager.config.track_history is True
