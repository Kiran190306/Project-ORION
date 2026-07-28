"""Deterministic in-memory repository for research strategy metadata."""

from __future__ import annotations

from libraries.domain.ai_research.exceptions import RepositoryError
from libraries.domain.ai_research.models import StrategyCandidate


class InMemoryStrategyRepository:
    """Repository implementation intentionally isolated from persistence infrastructure."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyCandidate] = {}

    async def register(self, strategy: StrategyCandidate) -> None:
        if strategy.strategy_id in self._strategies:
            raise RepositoryError(f"strategy '{strategy.strategy_id}' is already registered")
        self._strategies[strategy.strategy_id] = strategy

    async def remove(self, strategy_id: str) -> bool:
        return self._strategies.pop(strategy_id, None) is not None

    async def get_by_id(self, strategy_id: str) -> StrategyCandidate | None:
        return self._strategies.get(strategy_id)

    async def list(self, tags: frozenset[str] | None = None) -> tuple[StrategyCandidate, ...]:
        entries = tuple(self._strategies[key] for key in sorted(self._strategies))
        return entries if not tags else tuple(item for item in entries if tags.issubset(item.tags))


# The concise name is the concrete Sprint-1 repository API.
StrategyRepository = InMemoryStrategyRepository
