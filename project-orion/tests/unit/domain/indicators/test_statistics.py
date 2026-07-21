"""Tests for the Indicator Statistics."""

from __future__ import annotations

import pytest

from libraries.domain.indicators.statistics import IndicatorStatistics


@pytest.fixture
def stats() -> IndicatorStatistics:
    return IndicatorStatistics()


class TestIndicatorStatistics:
    async def test_record_execution(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.execution_count == 1
        assert s.total_latency == 0.001

    async def test_record_multiple_executions(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("rsi", 0.002)
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.execution_count == 2
        assert s.avg_latency > 0

    async def test_cache_hit_ratio(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001, cache_hit=True)
        await stats.record_execution("rsi", 0.002, cache_hit=False)
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.cache_hits == 1
        assert s.cache_misses == 1
        assert s.cache_hit_ratio == 0.5

    async def test_record_warmup(self, stats: IndicatorStatistics) -> None:
        await stats.record_warmup("rsi")
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.warmup_count == 1

    async def test_record_error(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001, error="Division by zero")
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.error_count == 1
        assert s.last_error == "Division by zero"

    async def test_get_stats_nonexistent(self, stats: IndicatorStatistics) -> None:
        s = await stats.get_stats("nonexistent")
        assert s is None

    async def test_get_all_stats(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("ema", 0.002)
        all_stats = await stats.get_all_stats()
        assert len(all_stats) == 2
        assert "rsi" in all_stats
        assert "ema" in all_stats

    async def test_reset_single(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("ema", 0.002)
        await stats.reset("rsi")
        assert await stats.get_stats("rsi") is None
        assert await stats.get_stats("ema") is not None

    async def test_reset_all(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("ema", 0.002)
        await stats.reset()
        all_stats = await stats.get_all_stats()
        assert len(all_stats) == 0

    async def test_summary_empty(self, stats: IndicatorStatistics) -> None:
        summary = await stats.summary()
        assert summary["total_executions"] == 0
        assert summary["total_indicators"] == 0

    async def test_summary_with_data(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("ema", 0.002)
        summary = await stats.summary()
        assert summary["total_executions"] == 2
        assert summary["total_indicators"] == 2
        assert summary["avg_latency_ms"] > 0

    async def test_last_execution_timestamp(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.last_execution is not None

    async def test_max_min_latency(self, stats: IndicatorStatistics) -> None:
        await stats.record_execution("rsi", 0.001)
        await stats.record_execution("rsi", 0.005)
        s = await stats.get_stats("rsi")
        assert s is not None
        assert s.max_latency == 0.005
        assert s.min_latency == 0.001
