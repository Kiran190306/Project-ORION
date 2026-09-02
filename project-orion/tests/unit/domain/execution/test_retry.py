"""Tests for retry handler."""

from __future__ import annotations

import pytest

from libraries.domain.execution.exceptions import RetryExhaustedError
from libraries.domain.execution.retry import RetryConfig, RetryHandler


class TestRetryHandler:
    async def test_successful_execution(self) -> None:
        handler = RetryHandler()

        async def _success() -> str:
            return "success"

        result = await handler.execute(_success, "test")
        assert result == "success"

    async def test_retry_on_failure(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=3, base_delay_ms=1.0))
        attempts = 0

        async def fail_twice() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("Not yet")
            return "success"

        result = await handler.execute(fail_twice, "test")
        assert result == "success"
        assert attempts == 3

    async def test_exhausted_retries_raises(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay_ms=1.0))

        async def always_fail() -> str:
            raise ValueError("Always fails")

        with pytest.raises(RetryExhaustedError) as exc:
            await handler.execute(always_fail, "test-fail")
        assert "Retry exhausted" in str(exc.value)

    async def test_calculate_delay(self) -> None:
        handler = RetryHandler(
            config=RetryConfig(exponential_base=2.0, base_delay_ms=100.0, jitter=False)
        )
        d1 = handler.calculate_delay(0)
        d2 = handler.calculate_delay(1)
        d3 = handler.calculate_delay(2)
        assert d1 == 100.0
        assert d2 == 200.0
        assert d3 == 400.0

    async def test_delay_capped_at_max(self) -> None:
        handler = RetryHandler(
            config=RetryConfig(
                base_delay_ms=1000.0, max_delay_ms=5000.0, exponential_base=10.0, jitter=False
            )
        )
        d = handler.calculate_delay(3)
        assert d <= 5000.0

    async def test_attempt_count(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=3, base_delay_ms=1.0))

        async def fail() -> str:
            raise ValueError("fail")

        with pytest.raises(RetryExhaustedError):
            await handler.execute(fail, "test")
        assert handler.attempt_count == 3

    async def test_is_exhausted(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay_ms=1.0))
        assert not handler.is_exhausted

        async def fail() -> str:
            raise ValueError("fail")

        with pytest.raises(RetryExhaustedError):
            await handler.execute(fail, "test")
        assert handler.is_exhausted

    async def test_reset(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=2, base_delay_ms=1.0))

        async def fail() -> str:
            raise ValueError("fail")

        with pytest.raises(RetryExhaustedError):
            await handler.execute(fail, "test")
        assert handler.attempt_count > 0
        await handler.reset()
        assert handler.attempt_count == 0

    async def test_get_state(self) -> None:
        handler = RetryHandler(config=RetryConfig(max_retries=3, base_delay_ms=100.0))
        state = await handler.get_state()
        assert state.max_retries == 3
        assert not state.is_exhausted
