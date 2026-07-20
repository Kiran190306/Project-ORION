"""Circuit breaker for the event streaming layer.

Implements the circuit breaker pattern with CLOSED, OPEN, and HALF_OPEN
states for protecting downstream dependencies from cascading failures.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""

    name: str
    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout_seconds: float = 30.0
    half_open_max_calls: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        if self.recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive")
        if self.half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be positive")


@dataclass(frozen=True, slots=True)
class CircuitBreakerStats:
    """Snapshot of circuit breaker statistics."""

    name: str
    state: str
    failure_count: int
    success_count: int
    failure_threshold: int
    success_threshold: int
    recovery_timeout_seconds: float
    total_calls: int
    total_failures: int
    total_successes: int
    total_timeouts: int
    last_failure_time: str | None
    last_success_time: str | None
    state_changed_at: str | None


class CircuitBreaker:
    """Circuit breaker for protecting downstream dependencies.

    Implements three states:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Circuit tripped, calls fail fast
    - HALF_OPEN: Testing recovery, limited calls allowed

    Supports:
    - Automatic recovery after timeout
    - Configurable failure/success thresholds
    - State change tracking
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state: CircuitState = CircuitState.CLOSED
        self._lock = asyncio.Lock()
        self._failure_count: int = 0
        self._success_count: int = 0
        self._total_calls: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._total_timeouts: int = 0
        self._last_failure_time: datetime | None = None
        self._last_success_time: datetime | None = None
        self._state_changed_at: float | None = None  # time.monotonic()
        self._half_open_calls: int = 0

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def state(self) -> CircuitState:
        # Trigger auto-recovery check on property access so test assertions see expected state
        self._check_state_sync()
        return self._state

    def _check_state_sync(self) -> None:
        """Synchronous version of _check_state for property access."""
        if self._state == CircuitState.OPEN and self._state_changed_at is not None:
            elapsed = time.monotonic() - self._state_changed_at
            if elapsed >= self._config.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._state_changed_at = time.monotonic()

    async def call(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        """Execute a call through the circuit breaker.

        Args:
            fn: Async callable to execute.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            Result of the call.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        async with self._lock:
            await self._check_state()

            if self._state == CircuitState.OPEN:
                self._total_calls += 1
                raise CircuitBreakerOpenError(
                    self._config.name, self._config.recovery_timeout_seconds
                )

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self._config.half_open_max_calls:
                    self._total_calls += 1
                    raise CircuitBreakerOpenError(
                        self._config.name, self._config.recovery_timeout_seconds
                    )
                self._half_open_calls += 1

        try:
            result = await fn(*args, **kwargs)
            await self._on_success()
            return result
        except CircuitBreakerOpenError:
            raise
        except asyncio.CancelledError:
            # Handle cancellation (e.g. from asyncio.wait_for timeout)
            await self._on_failure()
            self._total_timeouts += 1
            raise
        except asyncio.TimeoutError:
            await self._on_failure()
            self._total_timeouts += 1
            raise
        except Exception:
            await self._on_failure()
            raise

    async def _check_state(self) -> None:
        """Transition from OPEN to HALF_OPEN if recovery timeout has elapsed."""
        if self._state == CircuitState.OPEN and self._state_changed_at is not None:
            elapsed = time.monotonic() - self._state_changed_at
            if elapsed >= self._config.recovery_timeout_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._state_changed_at = time.monotonic()

    async def _on_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._total_calls += 1
            self._total_successes += 1
            self._last_success_time = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._reset_to_closed()
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._total_calls += 1
            self._total_failures += 1
            self._last_failure_time = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                self._trip_to_open()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._config.failure_threshold:
                    self._trip_to_open()

    def _trip_to_open(self) -> None:
        """Transition to OPEN state."""
        self._state = CircuitState.OPEN
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._state_changed_at = time.monotonic()

    def _reset_to_closed(self) -> None:
        """Reset to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._state_changed_at = None

    async def force_open(self) -> None:
        """Manually force the circuit to OPEN state."""
        async with self._lock:
            self._trip_to_open()

    async def force_close(self) -> None:
        """Manually force the circuit to CLOSED state."""
        async with self._lock:
            self._reset_to_closed()

    async def get_stats(self) -> CircuitBreakerStats:
        """Return current circuit breaker statistics."""
        async with self._lock:
            return CircuitBreakerStats(
                name=self._config.name,
                state=self._state.value,
                failure_count=self._failure_count,
                success_count=self._success_count,
                failure_threshold=self._config.failure_threshold,
                success_threshold=self._config.success_threshold,
                recovery_timeout_seconds=self._config.recovery_timeout_seconds,
                total_calls=self._total_calls,
                total_failures=self._total_failures,
                total_successes=self._total_successes,
                total_timeouts=self._total_timeouts,
                last_failure_time=(
                    self._last_failure_time.isoformat() if self._last_failure_time else None
                ),
                last_success_time=(
                    self._last_success_time.isoformat() if self._last_success_time else None
                ),
                state_changed_at=(
                    datetime.fromtimestamp(self._state_changed_at, tz=timezone.utc).isoformat()
                    if self._state_changed_at is not None
                    else None
                ),
            )


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, name: str, retry_after_seconds: float = 0.0) -> None:
        self.name = name
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. " f"Retry after {retry_after_seconds:.1f}s"
        )
