"""Tests for the idempotency guard."""

from __future__ import annotations

import pytest

from libraries.infrastructure.execution.idempotency import (
    DuplicateExecutionError,
    IdempotencyConfig,
    IdempotencyGuard,
)


class TestIdempotencyGuard:
    """Test suite for IdempotencyGuard."""

    @pytest.fixture
    def guard(self):
        config = IdempotencyConfig(window_seconds=3600, max_entries=1000)
        return IdempotencyGuard(config)

    @pytest.mark.asyncio
    async def test_check_and_register_first_time(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        assert await guard.record_count() > 0

    @pytest.mark.asyncio
    async def test_duplicate_execution_id(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        with pytest.raises(DuplicateExecutionError) as exc:
            await guard.check_and_register(
                execution_id="exec_001",
                order_id="order_002",
                request_hash="hash_002",
            )
        assert "Duplicate execution ID" in str(exc.value)

    @pytest.mark.asyncio
    async def test_duplicate_order_id(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        with pytest.raises(DuplicateExecutionError) as exc:
            await guard.check_and_register(
                execution_id="exec_002",
                order_id="order_001",
                request_hash="hash_002",
            )
        assert "Duplicate order ID" in str(exc.value)

    @pytest.mark.asyncio
    async def test_duplicate_request_hash(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        with pytest.raises(DuplicateExecutionError) as exc:
            await guard.check_and_register(
                execution_id="exec_002",
                order_id="order_002",
                request_hash="hash_001",
            )
        assert "Duplicate request hash" in str(exc.value)

    @pytest.mark.asyncio
    async def test_is_duplicate(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        assert await guard.is_duplicate("exec_001", "order_001", "hash_001")
        assert not await guard.is_duplicate("exec_002", "order_002", "hash_002")

    @pytest.mark.asyncio
    async def test_get_record(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        record = await guard.get_record("exec_001")
        assert record is not None
        assert record.execution_id == "exec_001"
        assert record.order_id == "order_001"

    @pytest.mark.asyncio
    async def test_update_status(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        await guard.update_status(
            execution_id="exec_001",
            status="filled",
            broker_order_id="broker_001",
        )
        record = await guard.get_record("exec_001")
        assert record is not None
        assert record.status == "filled"
        assert record.broker_order_id == "broker_001"

    @pytest.mark.asyncio
    async def test_remove(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        await guard.remove("exec_001")
        assert not await guard.is_duplicate("exec_001", "order_001", "hash_001")

    @pytest.mark.asyncio
    async def test_clear(self, guard):
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        await guard.clear()
        assert await guard.record_count() == 0

    @pytest.mark.asyncio
    async def test_expired_entries_cleaned(self):
        config = IdempotencyConfig(window_seconds=0.0)
        guard = IdempotencyGuard(config)
        await guard.check_and_register(
            execution_id="exec_001",
            order_id="order_001",
            request_hash="hash_001",
        )
        assert await guard.record_count() == 0

    def test_compute_request_hash(self):
        data = {"symbol": "EURUSD", "quantity": 0.1, "side": "buy"}
        hash1 = IdempotencyGuard.compute_request_hash(data)
        hash2 = IdempotencyGuard.compute_request_hash(data)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_compute_request_hash_different(self):
        data1 = {"symbol": "EURUSD", "quantity": 0.1}
        data2 = {"symbol": "EURUSD", "quantity": 0.2}
        hash1 = IdempotencyGuard.compute_request_hash(data1)
        hash2 = IdempotencyGuard.compute_request_hash(data2)
        assert hash1 != hash2
