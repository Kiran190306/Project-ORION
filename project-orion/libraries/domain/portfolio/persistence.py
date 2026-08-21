"""Persistence interfaces for the Portfolio & Position Management Engine.

Defines store abstractions only — no database code.
Future implementations expected for SQLite, PostgreSQL, Redis, Cloud Storage.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from libraries.domain.portfolio.models import (
    AccountSnapshot,
    Position,
)


@runtime_checkable
class PositionStore(Protocol):
    """Store interface for position persistence."""

    async def save(self, position: Position) -> None:
        """Persist a position."""
        ...

    async def load(self, position_id: str) -> Position | None:
        """Load a position by ID."""
        ...

    async def load_by_symbol(self, symbol: str) -> list[Position]:
        """Load all positions for a symbol."""
        ...

    async def load_open_positions(self) -> list[Position]:
        """Load all open positions."""
        ...

    async def load_closed_positions(self) -> list[Position]:
        """Load all closed positions."""
        ...

    async def load_all(self) -> list[Position]:
        """Load all positions."""
        ...

    async def delete(self, position_id: str) -> None:
        """Delete a position record."""
        ...

    async def count_open(self) -> int:
        """Return count of open positions."""
        ...


@runtime_checkable
class AccountStore(Protocol):
    """Store interface for account snapshot persistence."""

    async def save_snapshot(self, snapshot: AccountSnapshot) -> None:
        """Persist an account snapshot."""
        ...

    async def load_latest_snapshot(self) -> AccountSnapshot | None:
        """Load the most recent account snapshot."""
        ...

    async def load_snapshots(
        self,
        from_time: Any,
        to_time: Any,
    ) -> list[AccountSnapshot]:
        """Load account snapshots within a time range."""
        ...


@runtime_checkable
class JournalStore(Protocol):
    """Store interface for trade journal persistence."""

    async def save_entry(self, entry: Any) -> None:
        """Persist a journal entry."""
        ...

    async def load_entries(
        self,
        position_id: str | None = None,
        from_time: Any | None = None,
        to_time: Any | None = None,
        limit: int = 100,
    ) -> list[Any]:
        """Load journal entries with optional filters."""
        ...

    async def count_entries(self) -> int:
        """Return total journal entry count."""
        ...


@runtime_checkable
class AnalyticsStore(Protocol):
    """Store interface for analytics persistence."""

    async def save_snapshot(self, snapshot: Any) -> None:
        """Persist an analytics snapshot."""
        ...

    async def load_latest_snapshot(self) -> Any | None:
        """Load the most recent analytics snapshot."""
        ...


@runtime_checkable
class PersistenceManager(Protocol):
    """Composite persistence manager.

    Aggregates all individual stores.
    """

    @property
    def positions(self) -> PositionStore: ...

    @property
    def accounts(self) -> AccountStore: ...

    @property
    def journal(self) -> JournalStore: ...

    @property
    def analytics(self) -> AnalyticsStore: ...

    async def initialize(self) -> None:
        """Initialize all stores (create tables, connect, etc.)."""
        ...

    async def close(self) -> None:
        """Close all stores gracefully."""
        ...
