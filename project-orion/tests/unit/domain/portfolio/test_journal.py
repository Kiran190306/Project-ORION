"""Tests for TradeJournal — trade event recording and queries.

Covers:
- Entry creation (all types)
- Query with filters
- Position/symbol queries
- Recent entries, P&L entries
- Max entries limit
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from libraries.domain.portfolio.journal import JournalEntryType, TradeJournal


@pytest.fixture
async def journal() -> TradeJournal:
    """Create a clean TradeJournal for each test."""
    j = TradeJournal(max_entries=1000)
    yield j
    await j.clear()


class TestRecordEntry:
    """Entry recording scenarios."""

    async def test_record_position_opened(self, journal: TradeJournal):
        entry = await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            position_id="POS-001",
            symbol="EURUSD",
            side="long",
            quantity=Decimal("10000"),
            price=Decimal("1.1000"),
        )
        assert entry.entry_id.startswith("JRN-")
        assert entry.entry_type == JournalEntryType.POSITION_OPENED
        assert entry.position_id == "POS-001"
        assert entry.symbol == "EURUSD"
        assert entry.side == "long"
        assert entry.quantity == Decimal("10000")
        assert entry.price == Decimal("1.1000")

    async def test_record_all_entry_types(self, journal: TradeJournal):
        types = list(JournalEntryType)
        for t in types:
            entry = await journal.record(entry_type=t)
            assert entry.entry_type == t

    async def test_record_with_all_fields(self, journal: TradeJournal):
        entry = await journal.record(
            entry_type=JournalEntryType.TRADE_PROFIT,
            position_id="POS-001",
            symbol="EURUSD",
            side="long",
            quantity=Decimal("10000"),
            price=Decimal("1.1050"),
            pnl=Decimal("50"),
            commission=Decimal("5"),
            swap=Decimal("-1"),
            fees=Decimal("0.5"),
            balance=Decimal("10050"),
            equity=Decimal("10050"),
            margin_level=500.0,
            reason="take_profit",
            strategy="momentum",
            decision_id="DEC-001",
            execution_id="EXEC-001",
            tags=("forex", "eur"),
            details={"source": "test"},
        )
        assert entry.pnl == Decimal("50")
        assert entry.commission == Decimal("5")
        assert entry.swap == Decimal("-1")
        assert entry.fees == Decimal("0.5")
        assert entry.balance == Decimal("10050")
        assert entry.equity == Decimal("10050")
        assert entry.margin_level == 500.0
        assert entry.reason == "take_profit"
        assert entry.strategy == "momentum"
        assert entry.decision_id == "DEC-001"
        assert entry.execution_id == "EXEC-001"
        assert entry.tags == ("forex", "eur")
        assert entry.details["source"] == "test"

    async def test_total_entries(self, journal: TradeJournal):
        assert await journal.total_entries == 0
        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        await journal.record(entry_type=JournalEntryType.POSITION_CLOSED)
        assert await journal.total_entries == 2

    async def test_entry_id_increment(self, journal: TradeJournal):
        e1 = await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        e2 = await journal.record(entry_type=JournalEntryType.POSITION_CLOSED)
        assert e1.entry_id == "JRN-000001"
        assert e2.entry_id == "JRN-000002"


class TestQuery:
    """Query scenarios."""

    async def test_query_by_type(self, journal: TradeJournal):
        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        await journal.record(entry_type=JournalEntryType.POSITION_CLOSED)
        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        results = await journal.query(entry_type=JournalEntryType.POSITION_OPENED)
        assert len(results) == 2

    async def test_query_by_position_id(self, journal: TradeJournal):
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            position_id="POS-001",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_CLOSED,
            position_id="POS-001",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            position_id="POS-002",
        )
        results = await journal.query(position_id="POS-001")
        assert len(results) == 2

    async def test_query_by_symbol(self, journal: TradeJournal):
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            symbol="EURUSD",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            symbol="GBPUSD",
        )
        results = await journal.query(symbol="EURUSD")
        assert len(results) == 1

    async def test_query_by_strategy(self, journal: TradeJournal):
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            strategy="momentum",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            strategy="mean_reversion",
        )
        results = await journal.query(strategy="momentum")
        assert len(results) == 1

    async def test_query_by_time_range(self, journal: TradeJournal):
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)

        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        results = await journal.query(from_time=past, to_time=future)
        assert len(results) == 1

        results = await journal.query(from_time=future)
        assert len(results) == 0

    async def test_query_limit_and_offset(self, journal: TradeJournal):
        for i in range(20):
            await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        results = await journal.query(limit=5, offset=0)
        assert len(results) == 5
        results = await journal.query(limit=5, offset=10)
        assert len(results) == 5

    async def test_query_default_limit(self, journal: TradeJournal):
        for i in range(200):
            await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        results = await journal.query()
        assert len(results) == 100  # default limit


class TestGetByPosition:
    """Position-specific query scenarios."""

    async def test_get_by_position(self, journal: TradeJournal):
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            position_id="POS-001",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_MODIFIED,
            position_id="POS-001",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_CLOSED,
            position_id="POS-001",
        )
        results = await journal.get_by_position("POS-001")
        assert len(results) == 3

    async def test_get_by_position_empty(self, journal: TradeJournal):
        results = await journal.get_by_position("NONEXISTENT")
        assert len(results) == 0


class TestGetBySymbol:
    """Symbol-specific query scenarios."""

    async def test_get_by_symbol(self, journal: TradeJournal):
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            symbol="EURUSD",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_CLOSED,
            symbol="EURUSD",
        )
        await journal.record(
            entry_type=JournalEntryType.POSITION_OPENED,
            symbol="GBPUSD",
        )
        results = await journal.get_by_symbol("EURUSD")
        assert len(results) == 2


class TestGetRecent:
    """Recent entries scenarios."""

    async def test_get_recent(self, journal: TradeJournal):
        for i in range(10):
            await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        recent = await journal.get_recent(limit=5)
        assert len(recent) == 5

    async def test_get_recent_default_limit(self, journal: TradeJournal):
        for i in range(60):
            await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        recent = await journal.get_recent()
        assert len(recent) == 50

    async def test_get_recent_ordering(self, journal: TradeJournal):
        e1 = await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        e2 = await journal.record(entry_type=JournalEntryType.POSITION_CLOSED)
        recent = await journal.get_recent(limit=2)
        assert recent[0].entry_id == e2.entry_id  # newest first
        assert recent[1].entry_id == e1.entry_id


class TestGetPnLEntries:
    """P&L entries scenarios."""

    async def test_get_pnl_entries(self, journal: TradeJournal):
        await journal.record(entry_type=JournalEntryType.TRADE_PROFIT)
        await journal.record(entry_type=JournalEntryType.TRADE_LOSS)
        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        results = await journal.get_pnl_entries()
        assert len(results) == 1  # Only TRADE_PROFIT

    async def test_get_pnl_entries_time_range(self, journal: TradeJournal):
        await journal.record(entry_type=JournalEntryType.TRADE_PROFIT)
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)
        results = await journal.get_pnl_entries(from_time=past, to_time=future)
        assert len(results) == 1


class TestMaxEntries:
    """Max entries limit scenarios."""

    async def test_max_entries_enforced(self):
        j = TradeJournal(max_entries=5)
        for i in range(10):
            await j.record(entry_type=JournalEntryType.POSITION_OPENED)
        assert await j.total_entries == 5

    async def test_max_entries_keeps_latest(self):
        j = TradeJournal(max_entries=3)
        e1 = await j.record(entry_type=JournalEntryType.POSITION_OPENED)
        await j.record(entry_type=JournalEntryType.POSITION_CLOSED)
        await j.record(entry_type=JournalEntryType.POSITION_MODIFIED)
        await j.record(entry_type=JournalEntryType.POSITION_OPENED)
        recent = await j.get_recent(limit=5)
        assert len(recent) == 3
        # e1 should be dropped
        assert all(e.entry_id != e1.entry_id for e in recent)


class TestClear:
    """Clear scenarios."""

    async def test_clear(self, journal: TradeJournal):
        await journal.record(entry_type=JournalEntryType.POSITION_OPENED)
        await journal.clear()
        assert await journal.total_entries == 0
