"""Unit tests for RateLimiter and CircuitBreaker."""

from __future__ import annotations

import asyncio
import time
import pytest

from libraries.domain.market_data.exceptions import CircuitBreakerOpenError
from libraries.infrastructure.market_data.circuit_breaker import CircuitBreaker, CircuitState
from libraries.infrastructure.market_data.rate_limiter import AsyncTokenBucketRateLimiter


@pytest.mark.asyncio
class TestRateLimiter:
    """Test AsyncTokenBucketRateLimiter behavior."""

    async def test_acquire_burst_capacity(self) -> None:
        limiter = AsyncTokenBucketRateLimiter(rate_per_minute=60, capacity=3)
        start = time.monotonic()
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # Immediate consumption from capacity

    async def test_throttling_when_exhausted(self) -> None:
        limiter = AsyncTokenBucketRateLimiter(rate_per_minute=120, capacity=1)  # 2 tokens per sec
        await limiter.acquire()  # takes the 1 token

        start = time.monotonic()
        await limiter.acquire()  # must wait ~0.5s
        elapsed = time.monotonic() - start
        assert elapsed >= 0.4


@pytest.mark.asyncio
class TestCircuitBreaker:
    """Test CircuitBreaker state transitions."""

    async def test_successful_execution_remains_closed(self) -> None:
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)

        async def _success() -> str:
            return "ok"

        res = await breaker.execute(_success)
        assert res == "ok"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    async def test_trips_to_open_after_threshold(self) -> None:
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2)

        async def _failing() -> None:
            raise RuntimeError("network down")

        with pytest.raises(RuntimeError):
            await breaker.execute(_failing)
        assert breaker.state == CircuitState.CLOSED

        with pytest.raises(RuntimeError):
            await breaker.execute(_failing)
        assert breaker.state == CircuitState.OPEN

        # Call while OPEN immediately raises CircuitBreakerOpenError without invoking func
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.execute(_failing)

    async def test_half_open_recovery(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def _failing() -> None:
            raise RuntimeError("fail")

        async def _recovering() -> str:
            return "recovered"

        with pytest.raises(RuntimeError):
            await breaker.execute(_failing)
        assert breaker.state == CircuitState.OPEN

        # Wait recovery timeout
        await asyncio.sleep(0.15)

        # First call transitions to HALF_OPEN and then CLOSED on success
        res = await breaker.execute(_recovering)
        assert res == "recovered"
        assert breaker.state == CircuitState.CLOSED
