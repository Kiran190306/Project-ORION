"""Trade Journal — records all trade events for audit and analysis.

Supports:
- Position open/close entries
- P&L journal entries
- Order event entries
- Time-range queries
- Trade commentary
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class JournalEntryType(StrEnum):
    """Type of journal entry."""

    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_MODIFIED = "position_modified"
    TRADE_PROFIT = "trade_profit"
    TRADE_LOSS = "trade_loss"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    ORDER_CANCELLED = "order_cancelled"
    RISK_EVENT = "risk_event"
    SYSTEM_EVENT = "system_event"
    NOTE = "note"
    COMMENT = "comment"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """A single journal entry — immutable."""

    entry_id: str
    entry_type: JournalEntryType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    position_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    pnl: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fees: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    equity: Decimal = Decimal("0")
    margin_level: float = 0.0
    reason: str = ""
    strategy: str = ""
    decision_id: str = ""
    execution_id: str = ""
    tags: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


class TradeJournal:
    """Records and queries trade journal entries.

    Thread-safe via asyncio.Lock.
    Maintains ordered entries with index for efficient queries.
    """

    def __init__(self, max_entries: int = 100000) -> None:
        self._lock = asyncio.Lock()
        self._entries: list[JournalEntry] = []
        self._max_entries = max_entries
        self._entry_counter: int = 0

    @property
    async def total_entries(self) -> int:
        """Return total journal entries."""
        async with self._lock:
            return len(self._entries)

    async def record(
        self,
        entry_type: JournalEntryType,
        *,
        position_id: str = "",
        symbol: str = "",
        side: str = "",
        quantity: Decimal = Decimal("0"),
        price: Decimal = Decimal("0"),
        pnl: Decimal = Decimal("0"),
        commission: Decimal = Decimal("0"),
        swap: Decimal = Decimal("0"),
        fees: Decimal = Decimal("0"),
        balance: Decimal = Decimal("0"),
        equity: Decimal = Decimal("0"),
        margin_level: float = 0.0,
        reason: str = "",
        strategy: str = "",
        decision_id: str = "",
        execution_id: str = "",
        tags: tuple[str, ...] = (),
        details: dict[str, Any] | None = None,
    ) -> JournalEntry:
        """Record a new journal entry.

        Args:
            entry_type: Type of entry.
            position_id: Associated position ID.
            symbol: Trading symbol.
            side: Position side.
            quantity: Quantity.
            price: Price.
            pnl: Profit/loss.
            commission: Commission.
            swap: Swap.
            fees: Fees.
            balance: Account balance.
            equity: Account equity.
            margin_level: Margin level.
            reason: Reason/description.
            strategy: Strategy name.
            decision_id: Decision ID.
            execution_id: Execution ID.
            tags: Entry tags.
            details: Additional details.

        Returns:
            The recorded JournalEntry.
        """
        self._entry_counter += 1
        entry_id = f"JRN-{self._entry_counter:06d}"

        entry = JournalEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            position_id=position_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            pnl=pnl,
            commission=commission,
            swap=swap,
            fees=fees,
            balance=balance,
            equity=equity,
            margin_level=margin_level,
            reason=reason,
            strategy=strategy,
            decision_id=decision_id,
            execution_id=execution_id,
            tags=tags,
            details=details or {},
        )

        async with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries :]

        return entry

    async def query(
        self,
        *,
        entry_type: JournalEntryType | None = None,
        position_id: str | None = None,
        symbol: str | None = None,
        strategy: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JournalEntry]:
        """Query journal entries with filters.

        Args:
            entry_type: Filter by type.
            position_id: Filter by position ID.
            symbol: Filter by symbol.
            strategy: Filter by strategy.
            from_time: Start time filter.
            to_time: End time filter.
            limit: Max results (default 100).
            offset: Result offset.

        Returns:
            List of matching JournalEntry.
        """
        async with self._lock:
            results = list(self._entries)

        # Apply filters
        if entry_type is not None:
            results = [e for e in results if e.entry_type == entry_type]
        if position_id:
            results = [e for e in results if e.position_id == position_id]
        if symbol:
            results = [e for e in results if e.symbol == symbol]
        if strategy:
            results = [e for e in results if e.strategy == strategy]
        if from_time:
            results = [e for e in results if e.timestamp >= from_time]
        if to_time:
            results = [e for e in results if e.timestamp <= to_time]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[offset : offset + limit]

    async def get_by_position(self, position_id: str) -> list[JournalEntry]:
        """Get all entries for a specific position.

        Args:
            position_id: Position ID.

        Returns:
            List of JournalEntry for the position.
        """
        return await self.query(position_id=position_id, limit=10000)

    async def get_by_symbol(self, symbol: str, limit: int = 1000) -> list[JournalEntry]:
        """Get all entries for a symbol.

        Args:
            symbol: Trading symbol.
            limit: Max results.

        Returns:
            List of JournalEntry.
        """
        return await self.query(symbol=symbol, limit=limit)

    async def get_recent(self, limit: int = 50) -> list[JournalEntry]:
        """Get the most recent entries.

        Args:
            limit: Max results.

        Returns:
            List of recent JournalEntry.
        """
        return await self.query(limit=limit)

    async def get_pnl_entries(
        self,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[JournalEntry]:
        """Get P&L-related entries.

        Args:
            from_time: Start time.
            to_time: End time.
            limit: Max results.

        Returns:
            List of P&L JournalEntry.
        """
        return await self.query(
            entry_type=JournalEntryType.TRADE_PROFIT,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
        )

    async def clear(self) -> None:
        """Clear all journal entries."""
        async with self._lock:
            self._entries.clear()
            self._entry_counter = 0
