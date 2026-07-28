"""Tests for leaderboard module."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.ai_research.exceptions import LeaderboardError
from libraries.domain.ai_research.leaderboard import Leaderboard
from libraries.domain.ai_research.models import (
    LeaderboardEntry,
    LeaderboardFilter,
    StrategyEvaluation,
)


def _make_entry(
    strategy_id: str = "strat-1",
    sharpe: float = 1.5,
    profit_factor: float = 1.8,
    win_rate: float = 55.0,
    expectancy: float = 0.5,
    drawdown: float = 10.0,
) -> LeaderboardEntry:
    eval_result = StrategyEvaluation(
        strategy_id=strategy_id,
        metrics={
            "sharpe_ratio": sharpe,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "expectancy": expectancy,
            "max_drawdown": drawdown,
        },
        dataset_id="ds-1",
    )
    return LeaderboardEntry(rank=1, evaluation=eval_result, composite_score=0.75)


class TestLeaderboardInit:
    def test_default_init(self):
        lb = Leaderboard()
        assert lb.entry_count == 0
        assert lb.entries == ()
        assert lb._history == []


class TestLeaderboardUpdate:
    def test_update_sets_entries(self):
        lb = Leaderboard()
        entries = (_make_entry("strat-1"), _make_entry("strat-2"))
        asyncio.run(lb.update(entries))
        assert lb.entry_count == 2

    def test_update_empty_raises_error(self):
        lb = Leaderboard()
        with pytest.raises(LeaderboardError, match="must not be empty"):
            asyncio.run(lb.update(()))

    def test_update_duplicate_ids_raises_error(self):
        lb = Leaderboard()
        entries = (_make_entry("strat-1"), _make_entry("strat-1"))
        with pytest.raises(LeaderboardError, match="duplicate"):
            asyncio.run(lb.update(entries))

    def test_update_with_prior_entries_saves_history(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        asyncio.run(lb.update((_make_entry("strat-2"), _make_entry("strat-1"))))
        assert len(lb._history) == 1


class TestLeaderboardGetEntry:
    def test_get_entry_found(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        entry = asyncio.run(lb.get_entry("strat-1"))
        assert entry is not None
        assert entry.evaluation.strategy_id == "strat-1"

    def test_get_entry_not_found(self):
        lb = Leaderboard()
        entry = asyncio.run(lb.get_entry("nonexistent"))
        assert entry is None

    def test_get_entry_empty_leaderboard(self):
        lb = Leaderboard()
        entry = asyncio.run(lb.get_entry("strat-1"))
        assert entry is None


class TestLeaderboardQuery:
    def test_query_no_filter_returns_all(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"), _make_entry("strat-2"))))
        result = asyncio.run(lb.query())
        assert len(result) == 2

    def test_query_with_min_score(self):
        lb = Leaderboard()
        e1 = _make_entry("strat-1", sharpe=2.0)
        e2 = _make_entry("strat-2", sharpe=0.5, win_rate=30.0)
        asyncio.run(lb.update((e1, e2)))
        flt = LeaderboardFilter(min_score=0.6)
        result = asyncio.run(lb.query(flt))
        assert len(result) == 2

    def test_query_no_results_with_high_min_score(self):
        lb = Leaderboard()
        e1 = _make_entry("strat-1", sharpe=2.0)
        asyncio.run(lb.update((e1,)))
        flt = LeaderboardFilter(min_score=0.90)
        result = asyncio.run(lb.query(flt))
        assert len(result) == 0

    def test_query_with_top_n(self):
        lb = Leaderboard()
        entries = tuple(_make_entry(f"strat-{i}") for i in range(5))
        asyncio.run(lb.update(entries))
        flt = LeaderboardFilter(top_n=3)
        result = asyncio.run(lb.query(flt))
        assert len(result) == 3

    def test_query_empty(self):
        lb = Leaderboard()
        result = asyncio.run(lb.query())
        assert result == ()


class TestLeaderboardGetTopN:
    def test_get_top_n(self):
        lb = Leaderboard()
        entries = tuple(_make_entry(f"strat-{i}") for i in range(5))
        asyncio.run(lb.update(entries))
        result = asyncio.run(lb.get_top_n(3))
        assert len(result) == 3

    def test_get_top_n_negative_raises_error(self):
        lb = Leaderboard()
        with pytest.raises(LeaderboardError, match="positive"):
            asyncio.run(lb.get_top_n(0))

    def test_get_top_n_empty(self):
        lb = Leaderboard()
        result = asyncio.run(lb.get_top_n(1))
        assert result == ()

    def test_get_top_n_more_than_available(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        result = asyncio.run(lb.get_top_n(10))
        assert len(result) == 1


class TestLeaderboardCompareVersions:
    def test_compare_versions_returns_changes(self):
        lb = Leaderboard()
        e_old = _make_entry("strat-1")
        object.__setattr__(e_old, "composite_score", 0.50)
        asyncio.run(lb.update((e_old,)))
        e_new = _make_entry("strat-1")
        object.__setattr__(e_new, "composite_score", 0.85)
        asyncio.run(lb.update((_make_entry("strat-2"), e_new)))
        comparison = asyncio.run(lb.compare_versions("strat-1"))
        assert comparison is not None
        assert comparison.strategy_id == "strat-1"
        assert comparison.score_change > 0

    def test_compare_versions_strategy_not_found(self):
        lb = Leaderboard()
        result = asyncio.run(lb.compare_versions("nonexistent"))
        assert result is None

    def test_compare_versions_no_history(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        result = asyncio.run(lb.compare_versions("strat-1"))
        assert result is None


class TestLeaderboardGetHistory:
    def test_get_history_returns_all_entries(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        asyncio.run(lb.update((_make_entry("strat-2"), _make_entry("strat-1"))))
        history = asyncio.run(lb.get_history("strat-1"))
        assert len(history) == 2

    def test_get_history_strategy_not_found(self):
        lb = Leaderboard()
        history = asyncio.run(lb.get_history("nonexistent"))
        assert history == ()

    def test_get_history_empty(self):
        lb = Leaderboard()
        history = asyncio.run(lb.get_history("strat-1"))
        assert history == ()


class TestLeaderboardClear:
    def test_clear_removes_entries(self):
        lb = Leaderboard()
        asyncio.run(lb.update((_make_entry("strat-1"),)))
        assert lb.entry_count == 1
        asyncio.run(lb.clear())
        assert lb.entry_count == 0
        assert lb._history == []

    def test_clear_empty(self):
        lb = Leaderboard()
        asyncio.run(lb.clear())
        assert lb.entry_count == 0
