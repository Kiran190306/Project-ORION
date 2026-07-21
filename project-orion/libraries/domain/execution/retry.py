"""Order submission retry strategy.

Implements configurable retry with exponential backoff for
failed order submissions. Supports max retry count, backoff
calculation, and jitter.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.execution.exceptions import RetryExhaustedError


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay_ms: float = 100.0  # 100ms
    max_delay_ms: float = 5000.0  # 5s
    jitter: bool = True
    jitter_range_ms: float = 50.0
    exponential_base: float = 2.0
    retryable_statuses: frozenset[str] = frozenset(
        {"rejected", "expired", "timeout"}
    )


@dataclass(frozen=True, slots=True)
class RetryAttempt:
    """Record of a single retry attempt."""

    attempt_number: int
    delay_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str = ""
    success: bool = False


@dataclass(frozen=True, slots=True)
class RetryState:
    """Current state of retry tracking."""

    attempt_count: int
    max_retries: int
    last_delay_ms: float
    next_delay_ms: float
    is_exhausted: bool
    attempts: tuple[RetryAttempt, ...] = ()


class RetryHandler:
    """Handles retry logic for order submission.

    Thread-safe.
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()
        self._attempts: list[RetryAttempt] = []
        self._lock = asyncio.Lock()

    @property
    def config(self) -> RetryConfig:
        return self._config

    @property
    def attempts(self) -> tuple[RetryAttempt, ...]:
        return tuple(self._attempts)

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def is_exhausted(self) -> bool:
        return self.attempt_count >= self._config.max_retries

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay for a given attempt using exponential backoff.

        delay = base * (exponential_base ^ attempt) + jitter
        """
        delay = self._config.base_delay_ms * (
            self._config.exponential_base ** attempt_number
        )
        delay = min(delay, self._config.max_delay_ms)

        if self._config.jitter:
            jitter = random.uniform(
                -self._config.jitter_range_ms,
                self._config.jitter_range_ms,
            )
            delay += jitter

        return max(0.0, delay)

    async def execute(
        self,
        coro_factory,  # Callable[[], Awaitable[Any]]
        context: str = "",
    ) -> Any:
        """Execute a callable with retry logic.

        Args:
            coro_factory: Async callable that returns the result.
            context: Human-readable context for error messages.

        Returns:
            Result of the callable.

        Raises:
            RetryExhaustedError: After all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            delay = self.calculate_delay(attempt - 1)

            if attempt > 1:
                await asyncio.sleep(delay / 1000.0)

            try:
                result = await coro_factory()
                async with self._lock:
                    self._attempts.append(
                        RetryAttempt(
                            attempt_number=attempt,
                            delay_ms=delay,
                            success=True,
                        )
                    )
                return result
            except Exception as e:
                last_error = e
                async with self._lock:
                    self._attempts.append(
                        RetryAttempt(
                            attempt_number=attempt,
                            delay_ms=delay,
                            error=str(e),
                            success=False,
                        )
                    )

        raise RetryExhaustedError(
            f"Retry exhausted for '{context}' after "
            f"{self._config.max_retries} attempts: {last_error}"
        ) from last_error

    async def reset(self) -> None:
        """Reset retry attempt tracking."""
        async with self._lock:
            self._attempts.clear()

    async def get_state(self) -> RetryState:
        """Return current retry state."""
        async with self._lock:
            next_delay = self.calculate_delay(self.attempt_count)
            last_delay = (
                self._attempts[-1].delay_ms if self._attempts else 0.0
            )
            return RetryState(
                attempt_count=self.attempt_count,
                max_retries=self._config.max_retries,
                last_delay_ms=last_delay,
                next_delay_ms=next_delay,
                is_exhausted=self.is_exhausted,
                attempts=tuple(self._attempts),
            )
