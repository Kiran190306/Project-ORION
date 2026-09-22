"""Unit tests for RateLimiter implementations (InMemoryRateLimiter & RedisRateLimiter)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from libraries.domain.security.rate_limit import (
    FallbackMode,
    RateLimitPolicy,
    RateLimitScope,
)
from libraries.infrastructure.caching.exceptions import RedisError
from libraries.infrastructure.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
)


@pytest.fixture
def sample_policy() -> RateLimitPolicy:
    return RateLimitPolicy(
        name="test_policy",
        limit=5,
        window_seconds=60,
        scope=RateLimitScope.IP,
        fallback_mode=FallbackMode.BOUNDED_FALLBACK,
    )


class TestInMemoryRateLimiter:
    """Test suite for InMemoryRateLimiter sliding window and memory bounding."""

    @pytest.mark.asyncio
    async def test_allows_up_to_limit_then_rejects(self, sample_policy: RateLimitPolicy) -> None:
        """Sequential requests up to limit are allowed; subsequent requests are rejected."""
        limiter = InMemoryRateLimiter(max_keys=100)
        key = "rl:test:client1"

        # First 5 should succeed
        for i in range(5):
            res = await limiter.check_rate_limit(key, sample_policy.limit, sample_policy.window_seconds)
            assert res.allowed is True
            assert res.remaining == 5 - (i + 1)
            assert res.source == "memory_fallback"

        # 6th should be rejected
        res = await limiter.check_rate_limit(key, sample_policy.limit, sample_policy.window_seconds)
        assert res.allowed is False
        assert res.remaining == 0
        assert res.retry_after_seconds > 0
        assert res.source == "memory_fallback"

    @pytest.mark.asyncio
    async def test_sliding_window_expiration(self) -> None:
        """Requests after window expires are allowed again."""
        current_time = 1000.0

        def mock_time() -> float:
            return current_time

        policy = RateLimitPolicy(
            name="test_expiry",
            limit=2,
            window_seconds=10,
            scope=RateLimitScope.IP,
        )
        limiter = InMemoryRateLimiter(max_keys=100, time_provider=mock_time)
        key = "rl:test:client_exp"

        res1 = await limiter.check_rate_limit(key, policy.limit, policy.window_seconds)
        assert res1.allowed is True
        res2 = await limiter.check_rate_limit(key, policy.limit, policy.window_seconds)
        assert res2.allowed is True

        res3 = await limiter.check_rate_limit(key, policy.limit, policy.window_seconds)
        assert res3.allowed is False

        # Advance time beyond window
        current_time += 11.0
        res4 = await limiter.check_rate_limit(key, policy.limit, policy.window_seconds)
        assert res4.allowed is True
        assert res4.remaining == 1

    @pytest.mark.asyncio
    async def test_concurrent_requests_atomicity(self, sample_policy: RateLimitPolicy) -> None:
        """High concurrency across 20 tasks with limit of 5 admits exactly 5 and rejects 15."""
        limiter = InMemoryRateLimiter(max_keys=100)
        key = "rl:test:concurrent"

        async def _call() -> bool:
            result = await limiter.check_rate_limit(key, sample_policy.limit, sample_policy.window_seconds)
            return result.allowed

        results = await asyncio.gather(*[_call() for _ in range(20)])
        allowed_count = sum(1 for r in results if r is True)
        rejected_count = sum(1 for r in results if r is False)

        assert allowed_count == 5
        assert rejected_count == 15

    @pytest.mark.asyncio
    async def test_capacity_bounding_and_lru_pruning(self) -> None:
        """InMemoryRateLimiter bounds maximum keys and prunes oldest entries to prevent OOM."""
        # Limiter with max_keys=5
        limiter = InMemoryRateLimiter(max_keys=5)
        policy = RateLimitPolicy(
            name="test_bound",
            limit=10,
            window_seconds=60,
            scope=RateLimitScope.IP,
        )

        # Insert 10 different keys
        for i in range(10):
            res = await limiter.check_rate_limit(f"key_{i}", policy.limit, policy.window_seconds)
            assert res.allowed is True

        # Ensure internal cache size does not exceed max_keys
        assert limiter.key_count <= 5


class TestRedisRateLimiter:
    """Test suite for RedisRateLimiter Lua script evaluation and error handling."""

    @pytest.mark.asyncio
    async def test_redis_allowed_response_parsing(self, sample_policy: RateLimitPolicy) -> None:
        """Redis Lua response indicating success is parsed into RateLimitResult."""
        mock_redis = MagicMock()
        # Lua script returns: [allowed (1), remaining (3), retry_after (0), reset_after (45)]
        mock_redis.eval_script = AsyncMock(return_value=[1, 3, 0, 45])

        limiter = RedisRateLimiter(redis_client=mock_redis)
        result = await limiter.check_rate_limit("rl:test:redis1", sample_policy.limit, sample_policy.window_seconds)

        assert result.allowed is True
        assert result.remaining == 3
        assert result.retry_after_seconds == 0
        assert result.reset_after_seconds == 45
        assert result.source == "redis"
        mock_redis.eval_script.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_redis_rejected_response_parsing(self, sample_policy: RateLimitPolicy) -> None:
        """Redis Lua response indicating rejection is parsed with Retry-After seconds."""
        mock_redis = MagicMock()
        # Lua script returns: [allowed (0), remaining (0), retry_after (15), reset_after (15)]
        mock_redis.eval_script = AsyncMock(return_value=[0, 0, 15, 15])

        limiter = RedisRateLimiter(redis_client=mock_redis)
        result = await limiter.check_rate_limit("rl:test:redis_rej", sample_policy.limit, sample_policy.window_seconds)

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after_seconds == 15
        assert result.reset_after_seconds == 15
        assert result.source == "redis"

    @pytest.mark.asyncio
    async def test_redis_exception_propagates_for_fallback(self, sample_policy: RateLimitPolicy) -> None:
        """Redis infrastructure error raises exception to trigger fallback service layer."""
        mock_redis = MagicMock()
        mock_redis.eval_script = AsyncMock(side_effect=ConnectionError("Redis unreachable"))

        limiter = RedisRateLimiter(redis_client=mock_redis)
        with pytest.raises(RedisError, match="Redis unreachable"):
            await limiter.check_rate_limit("rl:test:fail", sample_policy.limit, sample_policy.window_seconds)
