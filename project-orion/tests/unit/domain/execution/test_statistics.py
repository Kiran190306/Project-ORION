"""Tests for execution statistics."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.statistics import (
    ExecutionOutcome,
    ExecutionStatistics,
    ExecutionStats,
)


class TestExecutionStatistics:
    async def test_empty_stats(self) -> None:
        stats = ExecutionStatistics()
        snapshot = await stats.get_stats()
        assert snapshot.total_orders == 0
        assert snapshot.fill_rate == 0.0

    async def test_record_filled_execution(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(
            outcome=ExecutionOutcome.FILLED,
            broker_id="broker-1",
            latency_ms=50.0,
            volume=Decimal("1000"),
            commission=Decimal("0.50"),
        )
        snapshot = await stats.get_stats()
        assert snapshot.total_orders == 1
        assert snapshot.filled_orders == 1
        assert snapshot.average_latency_ms == 50.0
        assert snapshot.total_volume == Decimal("1000")
        assert snapshot.total_commission == Decimal("0.50")

    async def test_record_multiple_outcomes(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED)
        await stats.record_execution(outcome=ExecutionOutcome.PARTIAL_FILL)
        await stats.record_execution(outcome=ExecutionOutcome.REJECTED)
        await stats.record_execution(outcome=ExecutionOutcome.CANCELLED)
        await stats.record_execution(outcome=ExecutionOutcome.EXPIRED)
        snapshot = await stats.get_stats()
        assert snapshot.total_orders == 5
        assert snapshot.filled_orders == 1
        assert snapshot.partial_fills == 1
        assert snapshot.rejected_orders == 1
        assert snapshot.cancelled_orders == 1
        assert snapshot.expired_orders == 1

    async def test_fill_rate_calculation(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED)
        await stats.record_execution(outcome=ExecutionOutcome.FILLED)
        await stats.record_execution(outcome=ExecutionOutcome.REJECTED)
        await stats.record_execution(outcome=ExecutionOutcome.PARTIAL_FILL)
        snapshot = await stats.get_stats()
        assert snapshot.fill_rate == 0.75  # 3 out of 4
        assert snapshot.total_orders == 4

    async def test_broker_breakdown(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, broker_id="broker-1")
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, broker_id="broker-1")
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, broker_id="broker-2")
        snapshot = await stats.get_stats()
        assert snapshot.broker_breakdown["broker-1"] == 2
        assert snapshot.broker_breakdown["broker-2"] == 1

    async def test_average_latency(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, latency_ms=10.0)
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, latency_ms=20.0)
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, latency_ms=30.0)
        snapshot = await stats.get_stats()
        assert snapshot.average_latency_ms == 20.0

    async def test_average_slippage(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, slippage_pips=1.0)
        await stats.record_execution(outcome=ExecutionOutcome.FILLED, slippage_pips=3.0)
        snapshot = await stats.get_stats()
        assert snapshot.average_slippage_pips == 2.0

    async def test_reset(self) -> None:
        stats = ExecutionStatistics()
        await stats.record_execution(outcome=ExecutionOutcome.FILLED)
        assert (await stats.get_stats()).total_orders == 1
        await stats.reset()
        assert (await stats.get_stats()).total_orders == 0

    async def test_execution_outcome_values(self) -> None:
        assert ExecutionOutcome.FILLED.value == "filled"
        assert ExecutionOutcome.REJECTED.value == "rejected"
        assert ExecutionOutcome.CANCELLED.value == "cancelled"

    async def test_execution_stats_snapshot(self) -> None:
        snapshot = ExecutionStats(
            total_orders=10,
            filled_orders=8,
            fill_rate=0.8,
            average_latency_ms=25.0,
        )
        assert snapshot.total_orders == 10
        assert snapshot.filled_orders == 8
        assert snapshot.fill_rate == 0.8
        assert snapshot.average_latency_ms == 25.0
