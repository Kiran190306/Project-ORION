"""Tests for execution metrics collector."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.infrastructure.execution.execution_metrics import (
    ExecutionMetricsCollector,
)


class TestExecutionMetricsCollector:
    """Test suite for ExecutionMetricsCollector."""

    @pytest.fixture
    def metrics(self):
        return ExecutionMetricsCollector(max_history=1000)

    @pytest.mark.asyncio
    async def test_initial_state(self, metrics):
        snapshot = await metrics.get_snapshot()
        assert snapshot.total_executions == 0
        assert snapshot.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_successful_execution(self, metrics):
        await metrics.record_execution(
            broker_name="paper",
            success=True,
            latency_ms=50.0,
            broker_latency_ms=30.0,
            fill_latency_ms=20.0,
            volume=Decimal("1000"),
            commission=Decimal("0.7"),
        )
        snapshot = await metrics.get_snapshot()
        assert snapshot.total_executions == 1
        assert snapshot.successful_executions == 1
        assert snapshot.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_record_failed_execution(self, metrics):
        await metrics.record_execution(
            broker_name="paper",
            success=False,
            latency_ms=100.0,
        )
        snapshot = await metrics.get_snapshot()
        assert snapshot.total_executions == 1
        assert snapshot.failed_executions == 1
        assert snapshot.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_record_retry_and_recovery(self, metrics):
        await metrics.record_execution(
            broker_name="paper",
            success=True,
            latency_ms=50.0,
            was_retry=True,
            was_recovery=True,
        )
        snapshot = await metrics.get_snapshot()
        assert snapshot.total_retries == 1
        assert snapshot.total_recoveries == 1

    @pytest.mark.asyncio
    async def test_record_partial_fill(self, metrics):
        await metrics.record_execution(
            broker_name="paper",
            success=True,
            latency_ms=30.0,
            is_partial_fill=True,
        )
        snapshot = await metrics.get_snapshot()
        assert snapshot.partial_fills == 1
        assert snapshot.full_fills == 0

    @pytest.mark.asyncio
    async def test_average_latency(self, metrics):
        for i in range(3):
            await metrics.record_execution(
                broker_name="paper",
                success=True,
                latency_ms=float(10 * (i + 1)),
                broker_latency_ms=float(5 * (i + 1)),
                fill_latency_ms=float(3 * (i + 1)),
            )
        snapshot = await metrics.get_snapshot()
        assert snapshot.average_execution_latency_ms == 20.0  # (10+20+30)/3
        assert snapshot.average_broker_latency_ms == 10.0  # (5+10+15)/3

    @pytest.mark.asyncio
    async def test_active_connections(self, metrics):
        await metrics.set_active_connections(3)
        snapshot = await metrics.get_snapshot()
        assert snapshot.active_connections == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_state(self, metrics):
        await metrics.set_circuit_breaker_state(True)
        snapshot = await metrics.get_snapshot()
        assert snapshot.circuit_breaker_open

    @pytest.mark.asyncio
    async def test_broker_breakdown(self, metrics):
        await metrics.record_execution(
            broker_name="broker1",
            success=True,
            latency_ms=10.0,
        )
        await metrics.record_execution(
            broker_name="broker2",
            success=False,
            latency_ms=20.0,
        )
        await metrics.record_execution(
            broker_name="broker1",
            success=True,
            latency_ms=15.0,
        )
        snapshot = await metrics.get_snapshot()
        assert "broker1" in snapshot.broker_breakdown
        assert "broker2" in snapshot.broker_breakdown
        assert snapshot.broker_breakdown["broker1"].total_orders == 2
        assert snapshot.broker_breakdown["broker2"].total_orders == 1

    @pytest.mark.asyncio
    async def test_reset(self, metrics):
        await metrics.record_execution(
            broker_name="paper",
            success=True,
            latency_ms=50.0,
        )
        await metrics.reset()
        snapshot = await metrics.get_snapshot()
        assert snapshot.total_executions == 0
        assert snapshot.total_volume == Decimal("0")
