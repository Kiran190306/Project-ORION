"""Tests for RollingStatistics."""

from __future__ import annotations

import asyncio
import math

import pytest

from libraries.domain.market_intelligence.statistics import (
    RollingStatistics,
    StatisticsConfig,
)


class TestRollingStatistics:
    def test_initial_state(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            snap = await stats.get_snapshot()
            assert snap.count == 0
            assert snap.mean == 0.0
            assert snap.sum == 0.0

        asyncio.run(exercise())

    def test_add_single_value(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            await stats.add(42.0)
            assert stats.count == 1
            snap = await stats.get_snapshot()
            assert snap.mean == 42.0
            assert snap.minimum == 42.0
            assert snap.maximum == 42.0

        asyncio.run(exercise())

    def test_add_multiple_values(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
                await stats.add(v)
            snap = await stats.get_snapshot()
            assert snap.count == 5
            assert snap.mean == 3.0
            assert snap.minimum == 1.0
            assert snap.maximum == 5.0

        asyncio.run(exercise())

    def test_percentile_computation(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics(StatisticsConfig(window_size=100))
            for v in range(1, 101):
                await stats.add(float(v))
            snap = await stats.get_snapshot()
            assert snap.p50 == 50.5
            assert snap.p95 > 94.0
            assert snap.p99 > 98.0
            assert snap.median == 50.5

        asyncio.run(exercise())

    def test_std_and_variance(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            for v in [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]:
                await stats.add(v)
            snap = await stats.get_snapshot()
            assert snap.count == 8
            assert snap.mean == 5.0
            assert snap.variance > 0
            assert snap.std > 0

        asyncio.run(exercise())

    def test_window_sliding(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics(StatisticsConfig(window_size=3))
            for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
                await stats.add(v)
            assert stats.count == 3  # Only last 3
            snap = await stats.get_snapshot()
            assert snap.minimum == 3.0
            assert snap.maximum == 5.0

        asyncio.run(exercise())

    def test_add_many(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            await stats.add_many([10.0, 20.0, 30.0])
            assert stats.count == 3
            snap = await stats.get_snapshot()
            assert snap.mean == 20.0

        asyncio.run(exercise())

    def test_clear(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            await stats.add(1.0)
            await stats.add(2.0)
            await stats.clear()
            snap = await stats.get_snapshot()
            assert snap.count == 0

        asyncio.run(exercise())

    def test_z_score(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            for v in [9.0, 10.0, 11.0, 9.5, 10.5]:
                await stats.add(v)
            z = await stats.z_score(15.0)
            assert z > 0.0

        asyncio.run(exercise())

    def test_is_significant(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()
            assert not await stats.is_significant(5)
            for _ in range(5):
                await stats.add(1.0)
            assert await stats.is_significant(5)

        asyncio.run(exercise())

    def test_concurrent_adds(self) -> None:
        async def exercise() -> None:
            stats = RollingStatistics()

            async def add_values() -> None:
                for _ in range(100):
                    await stats.add(1.0)

            await asyncio.gather(add_values(), add_values(), add_values())
            assert stats.total_count == 300

        asyncio.run(exercise())
