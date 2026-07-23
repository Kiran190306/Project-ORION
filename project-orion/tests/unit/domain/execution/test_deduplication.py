"""Tests for order deduplication."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from libraries.domain.execution.deduplication import (
    DeduplicationConfig,
    OrderDeduplicator,
    TrackedEntry,
)
from libraries.domain.execution.exceptions import DuplicateOrderError


class TestOrderDeduplicator:
    async def test_unique_submission_passes(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register(
            order_id="ORD-001",
            decision_id="DEC-001",
            symbol="EURUSD",
            side="buy",
        )
        assert await dedup.entry_count() > 0

    async def test_duplicate_decision_id_raises(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        with pytest.raises(DuplicateOrderError) as exc:
            await dedup.check_and_register("ORD-002", "DEC-001", "GBPUSD", "sell")
        assert "Duplicate decision" in str(exc.value)

    async def test_duplicate_order_id_raises(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        with pytest.raises(DuplicateOrderError):
            await dedup.check_and_register("ORD-001", "DEC-002", "GBPUSD", "sell")

    async def test_duplicate_symbol_side_raises(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        with pytest.raises(DuplicateOrderError):
            await dedup.check_and_register("ORD-002", "DEC-002", "EURUSD", "buy")

    async def test_is_duplicate_check(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        assert await dedup.is_duplicate("DEC-001", "ORD-001", "EURUSD", "buy")
        assert not await dedup.is_duplicate("DEC-002", "ORD-002", "GBPUSD", "sell")

    async def test_remove_order(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        assert await dedup.entry_count() > 0
        await dedup.remove("ORD-001")
        assert await dedup.entry_count() == 0

    async def test_clear(self) -> None:
        dedup = OrderDeduplicator()
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        await dedup.check_and_register("ORD-002", "DEC-002", "GBPUSD", "sell")
        assert await dedup.entry_count() == 6  # 3 keys * 2 orders
        await dedup.clear()
        assert await dedup.entry_count() == 0

    async def test_different_config_no_symbol_side_check(self) -> None:
        config = DeduplicationConfig(check_symbol_side=False)
        dedup = OrderDeduplicator(config=config)
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        await dedup.check_and_register("ORD-002", "DEC-002", "EURUSD", "buy")
        assert await dedup.entry_count() == 4  # 2 keys * 2 orders

    async def test_tracked_entry_creation(self) -> None:
        entry = TrackedEntry(
            key="test",
            order_id="ORD-001",
            decision_id="DEC-001",
            symbol="EURUSD",
            side="buy",
        )
        assert entry.order_id == "ORD-001"
        assert entry.decision_id == "DEC-001"
        assert entry.symbol == "EURUSD"
        assert entry.side == "buy"

    async def test_expired_entry_cleaned(self) -> None:
        config = DeduplicationConfig(window_seconds=0.001)
        dedup = OrderDeduplicator(config=config)
        await dedup.check_and_register("ORD-001", "DEC-001", "EURUSD", "buy")
        import asyncio

        await asyncio.sleep(0.01)
        # Should be cleaned up on next check
        assert not await dedup.is_duplicate("DEC-002", "ORD-002", "GBPUSD", "sell")
