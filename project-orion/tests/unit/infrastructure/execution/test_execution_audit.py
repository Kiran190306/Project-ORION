"""Tests for the execution auditor."""

from __future__ import annotations

import pytest

from libraries.infrastructure.execution.execution_audit import (
    AuditEventType,
    ExecutionAuditor,
)


class TestExecutionAuditor:
    """Test suite for ExecutionAuditor."""

    @pytest.fixture
    def auditor(self):
        return ExecutionAuditor()

    @pytest.mark.asyncio
    async def test_record_submission(self, auditor):
        entry = await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        assert entry.event_type == AuditEventType.SUBMISSION
        assert entry.broker_name == "paper"
        assert entry.order_id == "order_001"

    @pytest.mark.asyncio
    async def test_record_execution(self, auditor):
        entry = await auditor.record_execution(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
            filled_qty="0.1",
            fill_price="1.2000",
            latency_ms=45.0,
        )
        assert entry.event_type == AuditEventType.EXECUTION
        assert entry.latency_ms == 45.0
        assert "0.1" in entry.details

    @pytest.mark.asyncio
    async def test_record_failure(self, auditor):
        entry = await auditor.record_failure(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            error="Connection timeout",
        )
        assert entry.event_type == AuditEventType.FAILURE
        assert "timeout" in entry.error.lower()

    @pytest.mark.asyncio
    async def test_record_retry(self, auditor):
        entry = await auditor.record_retry(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            attempt=2,
            delay_ms=500.0,
            error="temporary error",
        )
        assert entry.event_type == AuditEventType.RETRY
        assert "attempt 2" in entry.details.lower()

    @pytest.mark.asyncio
    async def test_record_recovery(self, auditor):
        entry = await auditor.record_recovery(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            recovery_type="network_interruption",
        )
        assert entry.event_type == AuditEventType.RECOVERY

    @pytest.mark.asyncio
    async def test_record_cancellation(self, auditor):
        entry = await auditor.record_cancellation(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            reason="User requested",
        )
        assert entry.event_type == AuditEventType.CANCELLATION

    @pytest.mark.asyncio
    async def test_record_broker_response(self, auditor):
        entry = await auditor.record_broker_response(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            response='{"status": "filled"}',
            latency_ms=30.0,
        )
        assert entry.event_type == AuditEventType.BROKER_RESPONSE
        assert entry.broker_response == '{"status": "filled"}'

    @pytest.mark.asyncio
    async def test_get_execution_audit(self, auditor):
        await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        await auditor.record_execution(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
            filled_qty="0.1",
            fill_price="1.2000",
            latency_ms=45.0,
        )
        record = await auditor.get_execution_audit("exec_001")
        assert record.entry_count == 2
        assert len(record.entries) == 2

    @pytest.mark.asyncio
    async def test_get_all_entries_filtered(self, auditor):
        await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        await auditor.record_failure(
            broker_name="mt5",
            order_id="order_002",
            execution_id="exec_002",
            error="error",
        )
        entries = await auditor.get_all_entries(broker_name="paper")
        assert len(entries) == 1
        assert entries[0].broker_name == "paper"

    @pytest.mark.asyncio
    async def test_entry_count(self, auditor):
        await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        count = await auditor.entry_count()
        assert count == 1

    @pytest.mark.asyncio
    async def test_clear(self, auditor):
        await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        await auditor.clear()
        assert await auditor.entry_count() == 0

    @pytest.mark.asyncio
    async def test_entries_are_immutable(self, auditor):
        entry = await auditor.record_submission(
            broker_name="paper",
            order_id="order_001",
            execution_id="exec_001",
            symbol="EURUSD",
        )
        with pytest.raises(AttributeError):
            entry.details = "modified"

