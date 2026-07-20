"""Retry policies for connector transports.

Async-first and cancellation-safe retry with exponential backoff and jitter.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class RetryError(Exception):
    """Raised when retry budget is exhausted."""


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 5
    initial_delay_seconds: float = 0.25
    max_delay_seconds: float = 10.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.initial_delay_seconds <= 0:
            raise ValueError("initial_delay_seconds must be positive")
        if self.max_delay_seconds <= 0:
            raise ValueError("max_delay_seconds must be positive")
        if self.backoff_multiplier < 1.0:
            raise ValueError("backoff_multiplier must be >= 1.0")
        if self.jitter_factor < 0.0:
            raise ValueError("jitter_factor must be >= 0")


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    retry_on: Callable[[BaseException], bool] | None = None,
    on_attempt: Callable[[int, BaseException | None], None] | None = None,
) -> T:
    """Retry an async function.

    Notes:
        - CancellationError is never retried.
        - The policy is applied per call.
    """

    retry_on = retry_on or (lambda exc: True)
    last_exc: BaseException | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            if on_attempt:
                on_attempt(attempt, None)
            return await fn()
        except asyncio.CancelledError:
            raise
        except BaseException as exc:  # noqa: BLE001
            last_exc = exc
            if not retry_on(exc):
                raise
            if attempt >= policy.max_attempts:
                raise RetryError("Retry budget exhausted") from exc
            if on_attempt:
                on_attempt(attempt, exc)

            delay = policy.initial_delay_seconds * (policy.backoff_multiplier ** (attempt - 1))
            delay = min(delay, policy.max_delay_seconds)

            if policy.jitter_factor > 0.0:
                jitter = 1.0 + random.uniform(-policy.jitter_factor, policy.jitter_factor)
                delay *= jitter

            await asyncio.sleep(max(0.0, delay))

    raise RetryError("Retry budget exhausted") from last_exc
