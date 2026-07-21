"""Tests for StrategyStatistics."""

from __future__ import annotations

import asyncio

import pytest

from libraries.domain.strategies.statistics import (
    StrategyExecutionOutcome,
    StrategyStatistics,
)


class TestStrategyStatistics:
    def test_initial_stats(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            snapshot = await stats.get_stats("test_strategy")
            assert snapshot.strategy_id == "test_strategy"
            assert snapshot.execution_count == 0
            assert snapshot.win_rate == 0.0
            assert snapshot.avg_confidence == 0.0

        asyncio.run(exercise())

    def test_record_win(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            await stats.record_execution(
                outcome=StrategyExecutionOutcome.WIN,
                confidence=80.0,
                latency_ms=10.0,
            )
            snapshot = await stats.get_stats("test")
            assert snapshot.execution_count == 1
            assert snapshot.win_count == 1
            assert snapshot.win_rate == 1.0
            assert snapshot.avg_confidence == 80.0
            assert snapshot.avg_latency_ms == 10.0
            assert snapshot.last_outcome == StrategyExecutionOutcome.WIN
            assert snapshot.last_execution_time is not None

        asyncio.run(exercise())

    def test_record_loss(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            await stats.record_execution(
                outcome=StrategyExecutionOutcome.LOSS,
                confidence=30.0,
                latency_ms=5.0,
            )
            snapshot = await stats.get_stats("test")
            assert snapshot.execution_count == 1
            assert snapshot.loss_count == 1
            assert snapshot.loss_rate == 1.0

        asyncio.run(exercise())

    def test_record_error(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            await stats.record_execution(
                outcome=StrategyExecutionOutcome.ERROR,
                latency_ms=0.0,
            )
            snapshot = await stats.get_stats("test")
            assert snapshot.error_count == 1
            assert snapshot.execution_count == 1

        asyncio.run(exercise())

    def test_multiple_executions(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            await stats.record_execution(StrategyExecutionOutcome.WIN, 80.0, 10.0)
            await stats.record_execution(StrategyExecutionOutcome.WIN, 70.0, 15.0)
            await stats.record_execution(StrategyExecutionOutcome.LOSS, 30.0, 5.0)

            snapshot = await stats.get_stats("test")
            assert snapshot.execution_count == 3
            assert snapshot.win_count == 2
            assert snapshot.loss_count == 1
            # win_rate is rounded to 4 decimal places
            assert snapshot.win_rate == round(2 / 3, 4)
            assert snapshot.avg_confidence == round((80.0 + 70.0 + 30.0) / 3, 2)
            assert snapshot.avg_latency_ms == round((10.0 + 15.0 + 5.0) / 3, 2)

        asyncio.run(exercise())

    def test_reset_clears_all(self) -> None:
        async def exercise() -> None:
            stats = StrategyStatistics()
            await stats.record_execution(StrategyExecutionOutcome.WIN, 80.0, 10.0)
            await stats.record_execution(StrategyExecutionOutcome.LOSS, 30.0, 5.0)
            await stats.reset()

            snapshot = await stats.get_stats("test")
            assert snapshot.execution_count == 0
            assert snapshot.win_count == 0
            assert snapshot.loss_count == 0
            assert snapshot.avg_confidence == 0.0
            assert snapshot.last_execution_time is None
            assert snapshot.last_outcome is None

        asyncio.run(exercise())
