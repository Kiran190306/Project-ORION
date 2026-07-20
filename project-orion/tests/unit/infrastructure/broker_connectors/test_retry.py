"""Tests for retry policy and retry_async."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from libraries.infrastructure.broker_connectors.retry import RetryError, RetryPolicy, retry_async


def test_retry_async_success_after_failures() -> None:
    policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001, backoff_multiplier=1.0)

    attempts = 0

    async def flaky() -> int:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("boom")
        return 42

    result = asyncio.run(retry_async(lambda: flaky(), policy))
    assert result == 42
    assert attempts == 3


def test_retry_async_does_not_retry_cancelled_error() -> None:
    policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001)

    async def cancelled() -> int:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(retry_async(lambda: cancelled(), policy))


def test_retry_async_exhausted_raises_retry_error() -> None:
    policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001, backoff_multiplier=1.0)

    async def always_fails() -> int:
        raise ValueError("persistent")

    with pytest.raises(RetryError):
        asyncio.run(retry_async(lambda: always_fails(), policy))


def test_retry_async_retry_on_custom_predicate() -> None:
    policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001, backoff_multiplier=1.0)

    async def raises_value_error() -> int:
        raise ValueError("not retried")

    with pytest.raises(ValueError):
        asyncio.run(
            retry_async(
                lambda: raises_value_error(),
                policy,
                retry_on=lambda exc: isinstance(exc, RuntimeError),
            )
        )


def test_retry_async_on_attempt_callback() -> None:
    policy = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001, backoff_multiplier=1.0)

    attempts_log: list[tuple[int, Any]] = []

    async def always_fails() -> int:
        raise ValueError("fail")

    with pytest.raises(RetryError):
        asyncio.run(
            retry_async(
                lambda: always_fails(),
                policy,
                on_attempt=lambda attempt, exc: attempts_log.append((attempt, exc)),
            )
        )

    # on_attempt is called before each attempt (with None) and on each failure (with exc)
    # For 3 attempts: (1,None), (1,exc), (2,None), (2,exc), (3,None) = 5 entries
    assert len(attempts_log) == 5
    assert attempts_log[0] == (1, None)
    assert attempts_log[1][0] == 1 and isinstance(attempts_log[1][1], ValueError)
    assert attempts_log[2] == (2, None)
    assert attempts_log[3][0] == 2 and isinstance(attempts_log[3][1], ValueError)
    assert attempts_log[4] == (3, None)


def test_retry_policy_validation_max_attempts_zero() -> None:
    with pytest.raises(ValueError, match="max_attempts must be positive"):
        RetryPolicy(max_attempts=0)


def test_retry_policy_validation_initial_delay_zero() -> None:
    with pytest.raises(ValueError, match="initial_delay_seconds must be positive"):
        RetryPolicy(initial_delay_seconds=0)


def test_retry_policy_validation_backoff_multiplier() -> None:
    with pytest.raises(ValueError, match="backoff_multiplier must be >= 1.0"):
        RetryPolicy(backoff_multiplier=0.5)


def test_retry_policy_validation_jitter_negative() -> None:
    with pytest.raises(ValueError, match="jitter_factor must be >= 0"):
        RetryPolicy(jitter_factor=-0.1)


def test_retry_async_with_jitter_and_backoff() -> None:
    """Verify retry_async uses exponential backoff with jitter."""
    policy = RetryPolicy(
        max_attempts=3,
        initial_delay_seconds=0.01,
        max_delay_seconds=5.0,
        backoff_multiplier=4.0,
        jitter_factor=0.0,
    )

    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("timeout")
        return "ok"

    result = asyncio.run(retry_async(lambda: flaky(), policy))
    assert result == "ok"
    assert attempts == 3


def test_retry_async_success_first_attempt() -> None:
    policy = RetryPolicy(max_attempts=5, initial_delay_seconds=0.001)

    async def immediate() -> str:
        return "success"

    result = asyncio.run(retry_async(lambda: immediate(), policy))
    assert result == "success"
