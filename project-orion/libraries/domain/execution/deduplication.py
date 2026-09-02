"""Order deduplication.

Prevents duplicate order submissions by tracking decision IDs
and implementing a configurable deduplication window.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from libraries.domain.execution.exceptions import DuplicateOrderError


@dataclass(frozen=True, slots=True)
class DeduplicationConfig:
    """Configuration for deduplication."""

    window_seconds: float = 60.0  # Time window for dedup check
    max_entries: int = 10000  # Max tracked entries
    check_decision_id: bool = True
    check_symbol_side: bool = True
    check_order_id: bool = True


@dataclass(frozen=True, slots=True)
class TrackedEntry:
    """A tracked order submission for deduplication."""

    key: str
    order_id: str
    decision_id: str
    symbol: str
    side: str
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None


class OrderDeduplicator:
    """Prevents duplicate order submissions.

    Thread-safe via asyncio.Lock. Uses time-based expiration
    to automatically clean up old entries.
    """

    def __init__(
        self,
        config: DeduplicationConfig | None = None,
    ) -> None:
        self._config = config or DeduplicationConfig()
        self._entries: dict[str, TrackedEntry] = {}
        self._lock = asyncio.Lock()

    @property
    def config(self) -> DeduplicationConfig:
        return self._config

    async def check_and_register(
        self,
        order_id: str,
        decision_id: str,
        symbol: str,
        side: str,
    ) -> None:
        """Check for duplicates and register if not found.

        Args:
            order_id: Unique order identifier.
            decision_id: Decision engine decision ID.
            symbol: Trading symbol.
            side: Order side.

        Raises:
            DuplicateOrderError: If a duplicate is detected.
        """
        async with self._lock:
            self._cleanup_expired()

            # Check by decision ID
            if self._config.check_decision_id:
                decision_key = f"decision:{decision_id}"
                if decision_key in self._entries:
                    existing = self._entries[decision_key]
                    raise DuplicateOrderError(
                        f"Duplicate decision {decision_id}: "
                        f"already submitted as order {existing.order_id} "
                        f"at {existing.submitted_at.isoformat()}"
                    )

            # Check by order ID
            if self._config.check_order_id:
                order_key = f"order:{order_id}"
                if order_key in self._entries:
                    raise DuplicateOrderError(f"Duplicate order ID: {order_id}")

            # Check by symbol + side
            if self._config.check_symbol_side:
                ss_key = f"symbol_side:{symbol}:{side}"
                if ss_key in self._entries:
                    existing = self._entries[ss_key]
                    raise DuplicateOrderError(
                        f"Duplicate order for {symbol} {side}: "
                        f"already submitted as order {existing.order_id} "
                        f"at {existing.submitted_at.isoformat()}"
                    )

            # Register all keys
            expires_at = datetime.now(timezone.utc).timestamp() + self._config.window_seconds
            entry = TrackedEntry(
                key="",
                order_id=order_id,
                decision_id=decision_id,
                symbol=symbol,
                side=side,
                expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
            )

            if self._config.check_decision_id:
                self._entries[f"decision:{decision_id}"] = entry
            if self._config.check_order_id:
                self._entries[f"order:{order_id}"] = entry
            if self._config.check_symbol_side:
                self._entries[f"symbol_side:{symbol}:{side}"] = entry

            # Enforce max entries
            if len(self._entries) > self._config.max_entries:
                self._enforce_max_entries()

    async def is_duplicate(
        self,
        decision_id: str,
        order_id: str,
        symbol: str,
        side: str,
    ) -> bool:
        """Check if a submission would be a duplicate.

        Args:
            decision_id: Decision ID to check.
            order_id: Order ID to check.
            symbol: Symbol to check.
            side: Side to check.

        Returns:
            True if duplicate detected.
        """
        async with self._lock:
            self._cleanup_expired()

            if self._config.check_decision_id and f"decision:{decision_id}" in self._entries:
                return True

            if self._config.check_order_id and f"order:{order_id}" in self._entries:
                return True

            return (
                self._config.check_symbol_side
                and f"symbol_side:{symbol}:{side}" in self._entries
            )

    async def remove(self, order_id: str) -> None:
        """Remove entries for a given order ID.

        Args:
            order_id: Order ID to remove.
        """
        async with self._lock:
            keys_to_remove = [
                key for key, entry in self._entries.items() if entry.order_id == order_id
            ]
            for key in keys_to_remove:
                self._entries.pop(key, None)

    async def clear(self) -> None:
        """Clear all tracked entries."""
        async with self._lock:
            self._entries.clear()

    async def entry_count(self) -> int:
        """Return number of tracked entries."""
        async with self._lock:
            return len(self._entries)

    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at and entry.expires_at <= now
        ]
        for key in expired_keys:
            self._entries.pop(key, None)

    def _enforce_max_entries(self) -> None:
        """Remove oldest entries when max is exceeded."""
        while len(self._entries) > self._config.max_entries:
            oldest_key = min(
                self._entries.keys(),
                key=lambda k: self._entries[k].submitted_at,
            )
            self._entries.pop(oldest_key, None)
