"""Strategy leaderboard for ranking, filtering, and comparing strategies.

Supports:
- Strategy ranking with composite scores
- Filtering by tags, score range, and version
- Historical ranking snapshots
- Benchmark comparison
- Top-N strategies
- Version comparison
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from libraries.domain.ai_research.exceptions import LeaderboardError
from libraries.domain.ai_research.models import (
    LeaderboardComparison,
    LeaderboardEntry,
    LeaderboardFilter,
    StrategyEvaluation,
)


class Leaderboard:
    """In-memory strategy leaderboard with ranking, filtering, and comparison."""

    def __init__(self) -> None:
        self._entries: dict[str, LeaderboardEntry] = {}
        self._history: list[dict[str, LeaderboardEntry]] = []
        self._snapshot_timestamps: list[datetime] = []

    @property
    def entries(self) -> tuple[LeaderboardEntry, ...]:
        """Return all entries sorted by rank."""
        return tuple(sorted(self._entries.values(), key=lambda e: e.rank))

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    async def update(self, entries: tuple[LeaderboardEntry, ...]) -> None:
        """Update the leaderboard with new entries.

        Args:
            entries: New leaderboard entries.

        Raises:
            LeaderboardError: If entries are empty or contain duplicates.
        """
        if not entries:
            raise LeaderboardError("entries must not be empty")
        strategy_ids = {e.evaluation.strategy_id for e in entries}
        if len(strategy_ids) != len(entries):
            raise LeaderboardError("duplicate strategy IDs in entries")

        # Snapshot current state before overwriting
        if self._entries:
            self._history.append(dict(self._entries))
            self._snapshot_timestamps.append(datetime.now(timezone.utc))

        self._entries = {e.evaluation.strategy_id: e for e in entries}

    async def get_entry(self, strategy_id: str) -> LeaderboardEntry | None:
        """Get a single entry by strategy ID.

        Args:
            strategy_id: Strategy identifier.

        Returns:
            LeaderboardEntry if found, None otherwise.
        """
        return self._entries.get(strategy_id)

    async def query(self, filter_: LeaderboardFilter | None = None) -> tuple[LeaderboardEntry, ...]:
        """Query the leaderboard with optional filters.

        Args:
            filter_: Optional filter criteria.

        Returns:
            Filtered and sorted leaderboard entries.
        """
        entries = list(self._entries.values())

        if filter_ is None:
            return tuple(sorted(entries, key=lambda e: e.composite_score, reverse=True))

        # Apply tag filter
        if filter_.tags:
            entries = [
                e
                for e in entries
                if filter_.tags.issubset(e.evaluation.metadata.get("tags", frozenset()))
            ]

        # Apply score range filter
        if filter_.min_score > 0.0:
            entries = [e for e in entries if e.composite_score >= filter_.min_score]
        if filter_.max_score != float("inf"):
            entries = [e for e in entries if e.composite_score <= filter_.max_score]

        # Apply version filter
        if filter_.version is not None:
            entries = [
                e for e in entries if e.evaluation.metadata.get("version") == filter_.version
            ]

        # Sort
        reverse = not filter_.sort_ascending
        if filter_.sort_by == "composite_score":
            entries.sort(key=lambda e: e.composite_score, reverse=reverse)
        else:
            entries.sort(key=lambda e: e.rank, reverse=reverse)

        # Apply top-N
        if filter_.top_n is not None and filter_.top_n < len(entries):
            entries = entries[: filter_.top_n]

        return tuple(entries)

    async def get_top_n(self, n: int) -> tuple[LeaderboardEntry, ...]:
        """Get the top N strategies.

        Args:
            n: Number of strategies to return.

        Returns:
            Top N leaderboard entries.
        """
        if n < 1:
            raise LeaderboardError("n must be positive")
        return tuple(self.entries[:n])

    async def compare_versions(self, strategy_id: str) -> LeaderboardComparison | None:
        """Compare current and previous ranking for a strategy.

        Args:
            strategy_id: Strategy identifier.

        Returns:
            LeaderboardComparison if strategy exists in history, None otherwise.
        """
        current = self._entries.get(strategy_id)
        if current is None:
            return None

        # Look for previous snapshot
        if not self._history:
            return None

        previous_snapshot = self._history[-1]
        previous = previous_snapshot.get(strategy_id)
        if previous is None:
            return None

        return LeaderboardComparison(
            strategy_id=strategy_id,
            rank_change=previous.rank - current.rank,
            score_change=current.composite_score - previous.composite_score,
            previous_rank=previous.rank,
            current_rank=current.rank,
            previous_score=previous.composite_score,
            current_score=current.composite_score,
        )

    async def get_history(self, strategy_id: str) -> tuple[LeaderboardEntry, ...]:
        """Get historical rankings for a strategy.

        Args:
            strategy_id: Strategy identifier.

        Returns:
            Historical leaderboard entries for the strategy.
        """
        entries: list[LeaderboardEntry] = []
        for snapshot in self._history:
            entry = snapshot.get(strategy_id)
            if entry is not None:
                entries.append(entry)
        # Add current entry
        current = self._entries.get(strategy_id)
        if current is not None:
            entries.append(current)
        return tuple(entries)

    async def clear(self) -> None:
        """Clear all entries and history."""
        self._entries.clear()
        self._history.clear()
        self._snapshot_timestamps.clear()
