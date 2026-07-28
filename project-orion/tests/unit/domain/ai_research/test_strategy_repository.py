"""Tests for EPIC-011 InMemoryStrategyRepository."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import RepositoryError
from libraries.domain.ai_research.models import StrategyCandidate
from libraries.domain.ai_research.strategy_repository import InMemoryStrategyRepository


class TestInMemoryStrategyRepository:
    """Test InMemoryStrategyRepository."""

    @pytest.fixture
    def repo(self):
        return InMemoryStrategyRepository()

    @pytest.mark.asyncio
    async def test_register_strategy(self, repo):
        strategy = StrategyCandidate(strategy_id="s1", name="Test Strategy")
        await repo.register(strategy)
        result = await repo.get_by_id("s1")
        assert result is not None
        assert result.strategy_id == "s1"
        assert result.name == "Test Strategy"

    @pytest.mark.asyncio
    async def test_register_duplicate_raises_error(self, repo):
        strategy = StrategyCandidate(strategy_id="s1", name="Test")
        await repo.register(strategy)
        with pytest.raises(RepositoryError, match="already registered"):
            await repo.register(strategy)

    @pytest.mark.asyncio
    async def test_remove_existing_strategy(self, repo):
        strategy = StrategyCandidate(strategy_id="s1", name="Test")
        await repo.register(strategy)
        result = await repo.remove("s1")
        assert result is True
        assert await repo.get_by_id("s1") is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_strategy(self, repo):
        result = await repo.remove("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent(self, repo):
        result = await repo.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_empty(self, repo):
        strategies = await repo.list()
        assert strategies == ()

    @pytest.mark.asyncio
    async def test_list_with_strategies(self, repo):
        s1 = StrategyCandidate(strategy_id="s1", name="Alpha")
        s2 = StrategyCandidate(strategy_id="s2", name="Beta")
        await repo.register(s1)
        await repo.register(s2)
        strategies = await repo.list()
        assert len(strategies) == 2
        # Should be sorted by ID
        assert strategies[0].strategy_id == "s1"

    @pytest.mark.asyncio
    async def test_list_with_tags_filter(self, repo):
        s1 = StrategyCandidate(strategy_id="s1", name="Alpha", tags=frozenset({"trend"}))
        s2 = StrategyCandidate(strategy_id="s2", name="Beta", tags=frozenset({"mean_reversion"}))
        s3 = StrategyCandidate(
            strategy_id="s3", name="Gamma", tags=frozenset({"trend", "momentum"})
        )
        await repo.register(s1)
        await repo.register(s2)
        await repo.register(s3)

        # Filter by single tag
        result = await repo.list(tags=frozenset({"trend"}))
        assert len(result) == 2
        assert all("trend" in s.tags for s in result)

        # Filter by multiple tags
        result = await repo.list(tags=frozenset({"trend", "momentum"}))
        assert len(result) == 1
        assert result[0].strategy_id == "s3"

    @pytest.mark.asyncio
    async def test_list_with_no_matching_tags(self, repo):
        s1 = StrategyCandidate(strategy_id="s1", name="Alpha", tags=frozenset({"trend"}))
        await repo.register(s1)
        result = await repo.list(tags=frozenset({"nonexistent"}))
        assert result == ()
