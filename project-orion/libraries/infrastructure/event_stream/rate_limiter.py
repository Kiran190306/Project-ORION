"""Token bucket rate limiter for the event streaming layer.

Implements a per-provider token bucket algorithm for rate limiting
outgoing requests to broker/providers with burst handling.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RateLimiterConfig:
    """Configuration for a rate limiter."""

    provider: str
    tokens_per_second: float
    max_burst: int
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class RateLimiterStats:
    """Snapshot of rate limiter statistics."""

    provider: str
    tokens_remaining: float
    max_burst: int
    tokens_per_second: float
    total_accepted: int
    total_rejected: int
    current_burst: int
    enabled: bool


class RateLimiter:
    """Per-provider token bucket rate limiter.

    Supports:
    - Configurable tokens per second
    - Burst handling via max burst capacity
    - Provider-specific limits
    - Statistics tracking
    """

    def __init__(self, config: RateLimiterConfig) -> None:
        self._provider = config.provider
        self._tokens_per_second = config.tokens_per_second
        self._max_burst = config.max_burst
        self._enabled = config.enabled
        self._tokens: float = float(config.max_burst)
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()
        self._total_accepted: int = 0
        self._total_rejected: int = 0
        self._current_burst: int = 0

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def tokens_per_second(self) -> float:
        return self._tokens_per_second

    @property
    def max_burst(self) -> int:
        return self._max_burst

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire (default 1).

        Returns:
            True if tokens were acquired, False if rate limited.
        """
        if not self._enabled:
            self._total_accepted += tokens
            return True

        async with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                self._total_accepted += tokens
                self._current_burst = max(0, int(self._max_burst - self._tokens))
                return True

            self._total_rejected += tokens
            return False

    async def acquire_blocking(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking until available.

        Args:
            tokens: Number of tokens to acquire (default 1).
        """
        while not await self.acquire(tokens):
            wait_time = await self.estimate_wait(tokens)
            await asyncio.sleep(min(wait_time, 0.1))

    async def estimate_wait(self, tokens: int = 1) -> float:
        """Estimate the wait time in seconds for acquiring tokens.

        Args:
            tokens: Number of tokens to check for.

        Returns:
            Estimated wait time in seconds (0 if immediately available).
        """
        if not self._enabled:
            return 0.0

        async with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0

            deficit = tokens - self._tokens
            return deficit / self._tokens_per_second if self._tokens_per_shot > 0 else float("inf")

    @property
    def _tokens_per_shot(self) -> float:
        """Tokens per second (alias for rate)."""
        return self._tokens_per_second

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_burst,
            self._tokens + elapsed * self._tokens_per_second,
        )
        self._last_refill = now

    async def get_stats(self) -> RateLimiterStats:
        """Return current rate limiter statistics."""
        async with self._lock:
            self._refill()
            return RateLimiterStats(
                provider=self._provider,
                tokens_remaining=self._tokens,
                max_burst=self._max_burst,
                tokens_per_second=self._tokens_per_second,
                total_accepted=self._total_accepted,
                total_rejected=self._total_rejected,
                current_burst=self._current_burst,
                enabled=self._enabled,
            )

    async def reset(self) -> None:
        """Reset the rate limiter to its initial state."""
        async with self._lock:
            self._tokens = float(self._max_burst)
            self._last_refill = time.monotonic()
            self._total_accepted = 0
            self._total_rejected = 0
            self._current_burst = 0

    async def set_rate(self, tokens_per_second: float) -> None:
        """Update the tokens per second rate.

        Args:
            tokens_per_second: New rate.
        """
        if tokens_per_second <= 0:
            raise ValueError("tokens_per_second must be positive")
        async with self._lock:
            self._refill()
            self._tokens_per_second = tokens_per_second

    async def enable(self) -> None:
        """Enable rate limiting."""
        async with self._lock:
            self._enabled = True

    async def disable(self) -> None:
        """Disable rate limiting (all requests pass through)."""
        async with self._lock:
            self._enabled = False
