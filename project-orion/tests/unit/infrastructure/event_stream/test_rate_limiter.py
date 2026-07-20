"""Tests for RateLimiter."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.rate_limiter import (
    RateLimiter,
    RateLimiterConfig,
)


class TestRateLimiter:
    def test_acquire_allows_within_limit(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=100.0,
                    max_burst=100,
                )
            )
            result = await limiter.acquire()
            assert result is True

        asyncio.run(exercise())

    def test_acquire_rejects_when_exhausted(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=10.0,
                    max_burst=1,
                    enabled=True,
                )
            )
            assert await limiter.acquire()  # Consumes the burst token
            assert not await limiter.acquire()  # Should be rejected

        asyncio.run(exercise())

    def test_disabled_always_allows(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=0.0,
                    max_burst=0,
                    enabled=False,
                )
            )
            for _ in range(10):
                assert await limiter.acquire()

        asyncio.run(exercise())

    def test_tokens_refill_over_time(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=100.0,
                    max_burst=100,
                )
            )
            # Consume all tokens
            consumed = 0
            while await limiter.acquire():
                consumed += 1
                if consumed > 200:
                    break

            stats = await limiter.get_stats()
            assert stats.total_rejected > 0

        asyncio.run(exercise())

    def test_acquire_blocking_waits_for_tokens(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=1000.0,
                    max_burst=1,
                )
            )
            await limiter.acquire()

            # This should block briefly then succeed
            await limiter.acquire_blocking()
            stats = await limiter.get_stats()
            assert stats.total_accepted >= 2

        asyncio.run(exercise())

    def test_get_stats_returns_accurate_counts(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="stats_test",
                    tokens_per_second=100.0,
                    max_burst=50,
                )
            )
            await limiter.acquire()
            await limiter.acquire()

            stats = await limiter.get_stats()
            assert stats.provider == "stats_test"
            assert stats.total_accepted == 2
            assert stats.max_burst == 50

        asyncio.run(exercise())

    def test_reset_clears_state(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=100.0,
                    max_burst=10,
                )
            )
            await limiter.acquire(tokens=5)
            await limiter.reset()

            stats = await limiter.get_stats()
            assert stats.total_accepted == 0
            assert stats.total_rejected == 0

        asyncio.run(exercise())

    def test_set_rate_updates_tokens_per_second(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=10.0,
                    max_burst=10,
                )
            )
            await limiter.set_rate(50.0)
            stats = await limiter.get_stats()
            assert stats.tokens_per_second == 50.0

        asyncio.run(exercise())

    def test_estimate_wait_returns_zero_if_available(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=100.0,
                    max_burst=10,
                )
            )
            wait = await limiter.estimate_wait(1)
            assert wait == 0.0

        asyncio.run(exercise())

    def test_enable_disable_toggle(self) -> None:
        async def exercise() -> None:
            limiter = RateLimiter(
                RateLimiterConfig(
                    provider="test",
                    tokens_per_second=0.0,
                    max_burst=0,
                    enabled=True,
                )
            )
            # With 0 tokens, should reject
            assert not await limiter.acquire()

            await limiter.disable()
            assert await limiter.acquire()  # Disabled = pass through

            await limiter.enable()
            assert not await limiter.acquire()  # Enabled again = rejected

        asyncio.run(exercise())
