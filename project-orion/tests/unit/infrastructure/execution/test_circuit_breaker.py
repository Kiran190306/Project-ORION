"""Tests for the execution circuit breaker."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.execution.broker_adapter import (
    AdapterConnectionError,
    AdapterTimeoutError,
)
from libraries.infrastructure.execution.circuit_breaker import (
    CircuitBreakerOpenError,
    ExecutionCircuitBreaker,
    ExecutionCircuitBreakerConfig,
    ExecutionCircuitBreakerState,
)


class TestExecutionCircuitBreaker:
    """Test suite for ExecutionCircuitBreaker."""

    @pytest.fixture
    def cb(self):
        config = ExecutionCircuitBreakerConfig(
            name="test",
            failure_threshold=3,
            success_threshold=2,
            recovery_timeout_seconds=0.1,
            half_open_max_calls=1,
        )
        return ExecutionCircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_initial_state_closed(self, cb):
        assert cb.state == ExecutionCircuitBreakerState.CLOSED
        assert cb.is_available

    @pytest.mark.asyncio
    async def test_successful_call(self, cb):
        async def success():
            return "result"

        result = await cb.execute(success)
        assert result == "result"
        stats = await cb.get_stats()
        assert stats.total_successes == 1
        assert stats.total_failures == 0

    @pytest.mark.asyncio
    async def test_failure_trips_to_open(self, cb):
        async def fail():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await cb.execute(fail)
        with pytest.raises(ValueError):
            await cb.execute(fail)
        with pytest.raises(ValueError):
            await cb.execute(fail)

        assert cb.state == ExecutionCircuitBreakerState.OPEN
        assert not cb.is_available

    @pytest.mark.asyncio
    async def test_open_state_rejects_calls(self, cb):
        async def fail():
            raise ValueError("test error")

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.execute(fail)

        assert cb.state == ExecutionCircuitBreakerState.OPEN

        # Should be rejected
        with pytest.raises(CircuitBreakerOpenError):
            await cb.execute(lambda: "should not run")

    @pytest.mark.asyncio
    async def test_recovery_to_half_open(self, cb):
        async def fail():
            raise ValueError("test error")

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.execute(fail)

        assert cb.state == ExecutionCircuitBreakerState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        assert cb.state == ExecutionCircuitBreakerState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_resets_to_closed(self, cb):
        async def fail():
            raise ValueError("test error")

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.execute(fail)

        # Wait for recovery
        await asyncio.sleep(0.15)
        assert cb.state == ExecutionCircuitBreakerState.HALF_OPEN

        # Succeed in half-open (need 2 successive successes to close)
        async def success():
            return "ok"

        result = await cb.execute(success)
        assert result == "ok"

        # Check is still HALF_OPEN after first success
        result = await cb.execute(success)
        assert result == "ok"

        # After 2 successes, should transition to CLOSED
        stats = await cb.get_stats()
        assert stats.state == ExecutionCircuitBreakerState.CLOSED.value

    @pytest.mark.asyncio
    async def test_half_open_failure_trips_again(self, cb):
        async def fail():
            raise ValueError("test error")

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.execute(fail)

        # Wait for recovery
        await asyncio.sleep(0.15)

        async def also_fail():
            raise AdapterConnectionError("still broken", broker_name="test")

        with pytest.raises(AdapterConnectionError):
            await cb.execute(also_fail)

        assert cb.state == ExecutionCircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_force_open(self, cb):
        await cb.force_open()
        assert cb.state == ExecutionCircuitBreakerState.OPEN

    @pytest.mark.asyncio
    async def test_force_close(self, cb):
        await cb.force_open()
        await cb.force_close()
        assert cb.state == ExecutionCircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_stats(self, cb):
        stats = await cb.get_stats()
        assert stats.name == "test"
        assert stats.state == ExecutionCircuitBreakerState.CLOSED.value
        assert stats.total_calls == 0

    @pytest.mark.asyncio
    async def test_connection_error_tracking(self, cb):
        async def fail():
            raise AdapterConnectionError("conn lost", broker_name="test")

        with pytest.raises(AdapterConnectionError):
            await cb.execute(fail)

        stats = await cb.get_stats()
        assert stats.total_failures == 1

    def test_config_validation(self):
        with pytest.raises(ValueError):
            ExecutionCircuitBreakerConfig(name="test", failure_threshold=0)
        with pytest.raises(ValueError):
            ExecutionCircuitBreakerConfig(name="test", recovery_timeout_seconds=-1)
