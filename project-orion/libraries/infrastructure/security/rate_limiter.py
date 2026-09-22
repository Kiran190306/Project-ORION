"""Production-grade rate limiters for Project ORION.

Provides:
- RedisRateLimiter: Distributed, atomic sliding-window counter using Lua script and sorted sets.
- InMemoryRateLimiter: Bounded, thread/async-safe in-memory sliding-window cache with TTL pruning and OOM defense.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
import uuid
from collections import OrderedDict
from collections.abc import Callable
from typing import Protocol

from libraries.domain.security.rate_limit import RateLimitResult
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.caching.exceptions import RedisError

logger = logging.getLogger("trading_engine.security.rate_limiter")

# Atomic Sliding Window Lua Script
# KEYS[1] = key
# ARGV[1] = now_ms
# ARGV[2] = window_ms
# ARGV[3] = limit
# ARGV[4] = member
SLIDING_WINDOW_LUA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)

local current_count = redis.call('ZCARD', key)

if current_count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    local remaining = limit - current_count - 1
    local reset_after = math.ceil(window / 1000)
    return {1, remaining, 0, reset_after}
else
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = 1
    if oldest and #oldest >= 2 then
        local oldest_time = tonumber(oldest[2])
        local wait_ms = (oldest_time + window) - now
        if wait_ms > 0 then
            retry_after = math.ceil(wait_ms / 1000)
        end
    end
    local reset_after = retry_after
    return {0, 0, retry_after, reset_after}
end
"""


class RateLimiterPort(Protocol):
    """Protocol for atomic rate limit evaluation."""

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Evaluate rate limit atomically for given key, limit, and window."""
        ...


class RedisRateLimiter:
    """Atomic distributed sliding-window rate limiter using Redis sorted sets and Lua."""

    def __init__(
        self,
        redis_client: RedisClient,
        time_provider: Callable[[], float] | None = None,
    ) -> None:
        self._redis = redis_client
        self._time_provider = time_provider or time.time

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Execute atomic sliding-window rate check via Redis Lua script."""
        now_sec = self._time_provider()
        now_ms = int(now_sec * 1000)
        window_ms = int(window_seconds * 1000)
        unique_member = f"{now_ms}:{uuid.uuid4().hex[:8]}"

        try:
            res = await self._redis.eval_script(
                script=SLIDING_WINDOW_LUA_SCRIPT,
                keys=[key],
                args=[str(now_ms), str(window_ms), str(limit), unique_member],
            )

            # Response is [allowed (1/0), remaining, retry_after_sec, reset_after_sec]
            if not isinstance(res, (list, tuple)) or len(res) < 4:
                raise RedisError(f"Unexpected Redis Lua rate limit response structure: {res!r}")

            allowed = bool(res[0] == 1)
            remaining = int(res[1])
            retry_after = int(res[2])
            reset_after = int(res[3])
            reset_ts = int(now_sec) + reset_after

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=retry_after,
                reset_after_seconds=reset_after,
                reset_timestamp=reset_ts,
                source="redis",
            )
        except RedisError:
            raise
        except Exception as exc:
            logger.warning("Redis rate limit check failed for key %s: %s", key, exc)
            raise RedisError(f"Redis rate limiter evaluation failed: {exc}") from exc


class InMemoryRateLimiter:
    """Bounded, thread/async-safe in-memory sliding-window rate limiter.

    Used as a high-resilience fallback when Redis is unreachable.
    Defends against OOM attacks with bounded key capacity and active LRU eviction.
    """

    def __init__(
        self,
        max_keys: int = 10000,
        time_provider: Callable[[], float] | None = None,
    ) -> None:
        self._max_keys = max_keys
        self._time_provider = time_provider or time.time
        self._storage: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def key_count(self) -> int:
        """Return the current number of tracked keys in memory."""
        return len(self._storage)

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Evaluate sliding window in local memory with bounded capacity."""
        now = self._time_provider()
        clear_before = now - window_seconds

        async with self._lock:
            timestamps = self._storage.get(key, [])
            # Prune timestamps outside sliding window
            valid_timestamps = [t for t in timestamps if t > clear_before]

            if len(valid_timestamps) < limit:
                valid_timestamps.append(now)
                self._storage[key] = valid_timestamps
                self._storage.move_to_end(key)
                self._prune_capacity()

                remaining = limit - len(valid_timestamps)
                return RateLimitResult(
                    allowed=True,
                    limit=limit,
                    remaining=remaining,
                    retry_after_seconds=0,
                    reset_after_seconds=window_seconds,
                    reset_timestamp=int(now) + window_seconds,
                    source="memory_fallback",
                )
            else:
                self._storage[key] = valid_timestamps
                self._storage.move_to_end(key)
                oldest_timestamp = valid_timestamps[0]
                wait_time = (oldest_timestamp + window_seconds) - now
                retry_after = max(1, math.ceil(wait_time))

                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                    reset_after_seconds=retry_after,
                    reset_timestamp=int(now) + retry_after,
                    source="memory_fallback",
                )

    def _prune_capacity(self) -> None:
        """Evict oldest entries if capacity exceeds maximum allowed keys."""
        while len(self._storage) > self._max_keys:
            self._storage.popitem(last=False)

    async def clear(self) -> None:
        """Clear all stored rate limits (useful for testing)."""
        async with self._lock:
            self._storage.clear()
