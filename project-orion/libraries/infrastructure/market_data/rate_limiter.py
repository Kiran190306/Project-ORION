"""Asynchronous token bucket rate limiter for market data providers."""

from __future__ import annotations

import asyncio
import time


class AsyncTokenBucketRateLimiter:
    """Thread-safe, async token bucket rate limiter.

    Args:
        rate_per_minute: Maximum allowed requests per 60-second window.
        capacity: Maximum burst capacity (defaults to rate_per_minute).
    """

    def __init__(self, rate_per_minute: int = 60, capacity: int | None = None) -> None:
        self._rate_per_second = rate_per_minute / 60.0
        self._capacity = float(capacity or rate_per_minute)
        self._tokens = self._capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire 1 token, awaiting token replenishment if bucket is exhausted."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_second)
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # Calculate required sleep time for 1 token
                needed = 1.0 - self._tokens
                wait_time = needed / self._rate_per_second

            await asyncio.sleep(max(0.01, wait_time))
