"""Tests for the execution retry policy."""

from __future__ import annotations

import pytest

from libraries.infrastructure.execution.broker_adapter import (
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
    AdapterTimeoutError,
)
from libraries.infrastructure.execution.retry_policy import (
    ExecutionRetryConfig,
    ExecutionRetryPolicy,
    NonRetryableError,
    RetryExhaustedError,
)


class TestExecutionRetryPolicy:
    """Test suite for ExecutionRetryPolicy."""

    @pytest.fixture
    def policy(self):
        return ExecutionRetryPolicy()

    def test_default_config(self, policy):
        config = policy.config
        assert config.max_retries == 3
        assert config.base_delay_ms == 200.0
        assert config.max_delay_ms == 10000.0
        assert config.jitter

    def test_calculate_delay(self, policy):
        delay = policy.calculate_delay(0)
        assert delay >= 0

        delay1 = policy.calculate_delay(1)
        delay2 = policy.calculate_delay(2)
        assert delay2 >= delay1  # Exponential backoff

    def test_is_retryable_auth_error(self, policy):
        assert not policy.is_retryable(AdapterAuthenticationError("auth failed", broker_name="test"))

    def test_is_retryable_connection_error(self, policy):
        config = ExecutionRetryConfig(retry_on_connection_error=True)
        policy = ExecutionRetryPolicy(config)
        assert policy.is_retryable(AdapterConnectionError("conn failed", broker_name="test"))

    def test_is_retryable_timeout(self, policy):
        config = ExecutionRetryConfig(retry_on_timeout=True)
        policy = ExecutionRetryPolicy(config)
        assert policy.is_retryable(AdapterTimeoutError("timeout", broker_name="test"))

    def test_is_retryable_not_connected(self, policy):
        config = ExecutionRetryConfig(retry_on_not_connected=True)
        policy = ExecutionRetryPolicy(config)
        assert policy.is_retryable(AdapterNotConnectedError("not connected", broker_name="test"))

    def test_is_retryable_rejected_default_false(self, policy):
        assert not policy.is_retryable(AdapterOrderRejectedError("rejected", broker_name="test"))

    def test_is_retryable_rejected_when_enabled(self):
        config = ExecutionRetryConfig(retry_on_rejected=True)
        policy = ExecutionRetryPolicy(config)
        assert policy.is_retryable(AdapterOrderRejectedError("rejected", broker_name="test"))

    @pytest.mark.asyncio
    async def test_execute_success(self, policy):
        async def operation():
            return "success"

        result, attempts = await policy.execute(operation, context="test")
        assert result == "success"
        assert len(attempts) == 1
        assert attempts[0].outcome.value == "success"

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self, policy):
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AdapterConnectionError("temporary", broker_name="test")
            return "success"

        config = ExecutionRetryConfig(
            max_retries=3,
            retry_on_connection_error=True,
            base_delay_ms=1.0,
        )
        policy = ExecutionRetryPolicy(config)
        result, attempts = await policy.execute(operation, context="test")
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_exhausted(self, policy):
        async def operation():
            raise AdapterConnectionError("persistent", broker_name="test")

        config = ExecutionRetryConfig(
            max_retries=2,
            retry_on_connection_error=True,
            base_delay_ms=1.0,
        )
        policy = ExecutionRetryPolicy(config)
        with pytest.raises(RetryExhaustedError):
            await policy.execute(operation, context="test")

    @pytest.mark.asyncio
    async def test_execute_non_retryable(self, policy):
        async def operation():
            raise AdapterAuthenticationError("bad auth", broker_name="test")

        with pytest.raises(NonRetryableError):
            await policy.execute(operation, context="test")

    @pytest.mark.asyncio
    async def test_reset(self, policy):
        async def op():
            return "ok"

        await policy.execute(op, context="test")
        assert policy.attempt_count > 0
        await policy.reset()
        assert policy.attempt_count == 0

    @pytest.mark.asyncio
    async def test_is_exhausted(self):
        config = ExecutionRetryConfig(max_retries=1, base_delay_ms=1.0)
        policy = ExecutionRetryPolicy(config)

        async def op():
            raise AdapterConnectionError("fail", broker_name="test")

        with pytest.raises(RetryExhaustedError):
            await policy.execute(op, context="test")
        assert policy.is_exhausted

