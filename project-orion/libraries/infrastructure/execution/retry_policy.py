"""Configurable retry strategy for broker execution.

Supports exponential backoff, maximum retry count, timeout handling,
retryable/non-retryable exceptions, and retry metrics collection.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Awaitable, Callable

from libraries.infrastructure.execution.broker_adapter import (
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
    AdapterTimeoutError,
    ExecutionAdapterError,
)


class RetryOutcome(StrEnum):
    """Outcome of a retry attempt."""

    SUCCESS = "success"
    RETRYING = "retrying"
    EXHAUSTED = "exhausted"
    NON_RETRYABLE = "non_retryable"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class RetryAttemptRecord:
    """Record of a single retry attempt."""

    attempt_number: int
    delay_ms: float
    outcome: RetryOutcome
    error: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class ExecutionRetryConfig:
    """Configuration for the execution retry policy."""

    max_retries: int = 3
    base_delay_ms: float = 200.0
    max_delay_ms: float = 10000.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range_ms: float = 50.0
    timeout_seconds: float = 30.0
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_not_connected: bool = True
    retry_on_rejected: bool = False


class ExecutionRetryPolicy:
    """Configurable retry strategy for broker execution.

    Determines if a failed operation should be retried, calculates
    appropriate delays with exponential backoff and jitter, and
    categorizes errors as retryable or non-retryable.
    """

    def __init__(self, config: ExecutionRetryConfig | None = None) -> None:
        self._config = config or ExecutionRetryConfig()
        self._attempts: list[RetryAttemptRecord] = []
        self._lock = asyncio.Lock()

    @property
    def config(self) -> ExecutionRetryConfig:
        return self._config

    @property
    def attempts(self) -> tuple[RetryAttemptRecord, ...]:
        return tuple(self._attempts)

    @property
    def attempt_count(self) -> int:
        return len(self._attempts)

    @property
    def is_exhausted(self) -> bool:
        return self.attempt_count >= self._config.max_retries

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay for retry attempt using exponential backoff.

        delay = base * (exponential_base ^ attempt) + jitter

        Args:
            attempt_number: Zero-based attempt number.

        Returns:
            Delay in milliseconds.
        """
        delay = self._config.base_delay_ms * (self._config.exponential_base**attempt_number)
        delay = min(delay, self._config.max_delay_ms)

        if self._config.jitter:
            jitter = random.uniform(
                -self._config.jitter_range_ms,
                self._config.jitter_range_ms,
            )
            delay += jitter

        return max(0.0, delay)

    def is_retryable(self, error: Exception) -> bool:
        """Determine if an error is retryable.

        Args:
            error: The exception to evaluate.

        Returns:
            True if the error should trigger a retry.
        """
        if isinstance(error, AdapterAuthenticationError):
            return False
        if isinstance(error, AdapterOrderRejectedError):
            return self._config.retry_on_rejected
        if isinstance(error, AdapterTimeoutError):
            return self._config.retry_on_timeout
        if isinstance(error, (AdapterConnectionError, ConnectionError, ConnectionRefusedError)):
            return self._config.retry_on_connection_error
        if isinstance(error, AdapterNotConnectedError):
            return self._config.retry_on_not_connected
        if isinstance(error, ExecutionAdapterError):
            return False
        # Retryable network-level errors
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return self._config.retry_on_timeout
        # Unknown errors are not retryable by default
        return False

    async def execute(
        self,
        operation: Callable[[], Awaitable[Any]],
        context: str = "",
    ) -> tuple[Any, list[RetryAttemptRecord]]:
        """Execute an operation with retry logic.

        Args:
            operation: Async callable to execute.
            context: Human-readable context for logging.

        Returns:
            Tuple of (result, list_of_attempts).

        Raises:
            RetryExhaustedError: After all retries are exhausted.
            NonRetryableError: If a non-retryable error occurs.
            asyncio.TimeoutError: If the operation times out.
        """
        attempts: list[RetryAttemptRecord] = []
        last_error: Exception | None = None

        for attempt in range(1, self._config.max_retries + 1):
            delay = self.calculate_delay(attempt - 1)
            start_time = time.monotonic()

            if attempt > 1:
                await asyncio.sleep(delay / 1000.0)

            try:
                # Apply timeout
                result = await asyncio.wait_for(
                    operation(),
                    timeout=self._config.timeout_seconds,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                record = RetryAttemptRecord(
                    attempt_number=attempt,
                    delay_ms=delay,
                    outcome=RetryOutcome.SUCCESS,
                    latency_ms=round(elapsed_ms, 2),
                )
                async with self._lock:
                    self._attempts.append(record)
                return result, attempts + [record]

            except asyncio.TimeoutError as e:
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                last_error = e
                if self._config.retry_on_timeout and attempt < self._config.max_retries:
                    record = RetryAttemptRecord(
                        attempt_number=attempt,
                        delay_ms=delay,
                        outcome=RetryOutcome.RETRYING,
                        error="Timeout",
                        latency_ms=round(elapsed_ms, 2),
                    )
                else:
                    record = RetryAttemptRecord(
                        attempt_number=attempt,
                        delay_ms=delay,
                        outcome=RetryOutcome.TIMEOUT,
                        error="Timeout",
                        latency_ms=round(elapsed_ms, 2),
                    )
                attempts.append(record)

            except Exception as e:
                elapsed_ms = (time.monotonic() - start_time) * 1000.0
                last_error = e

                if self.is_retryable(e) and attempt < self._config.max_retries:
                    record = RetryAttemptRecord(
                        attempt_number=attempt,
                        delay_ms=delay,
                        outcome=RetryOutcome.RETRYING,
                        error=str(e),
                        latency_ms=round(elapsed_ms, 2),
                    )
                elif self.is_retryable(e):
                    record = RetryAttemptRecord(
                        attempt_number=attempt,
                        delay_ms=delay,
                        outcome=RetryOutcome.EXHAUSTED,
                        error=str(e),
                        latency_ms=round(elapsed_ms, 2),
                    )
                else:
                    record = RetryAttemptRecord(
                        attempt_number=attempt,
                        delay_ms=delay,
                        outcome=RetryOutcome.NON_RETRYABLE,
                        error=str(e),
                        latency_ms=round(elapsed_ms, 2),
                    )
                attempts.append(record)

                if not self.is_retryable(e):
                    raise NonRetryableError(f"Non-retryable error in '{context}': {e}") from e

        async with self._lock:
            self._attempts.extend(attempts)

        raise RetryExhaustedError(
            f"Retry exhausted for '{context}' after "
            f"{self._config.max_retries} attempts: {last_error}"
        ) from last_error

    async def reset(self) -> None:
        """Reset retry attempt tracking."""
        async with self._lock:
            self._attempts.clear()


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""


class NonRetryableError(Exception):
    """Raised when a non-retryable error occurs."""
