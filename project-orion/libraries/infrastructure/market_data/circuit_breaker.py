"""Circuit breaker pattern implementation for market data provider resilience."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from enum import StrEnum
import time
from typing import Any, TypeVar

from libraries.domain.market_data.exceptions import CircuitBreakerOpenError

T = TypeVar("T")


class CircuitState(StrEnum):
    """Circuit breaker operational state."""

    CLOSED = "closed"        # Normal operations
    OPEN = "open"            # Failing; rejecting calls
    HALF_OPEN = "half_open"  # Probing recovery


class CircuitBreaker:
    """Asynchronous circuit breaker guarding provider calls against cascading failures.

    Args:
        failure_threshold: Consecutive failures needed to trip circuit to OPEN.
        recovery_timeout: Seconds in OPEN state before testing with HALF_OPEN probe.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def execute(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        """Execute async function wrapped with circuit breaker protection."""
        async with self._lock:
            now = time.monotonic()
            if self._state == CircuitState.OPEN:
                if now - self._last_failure_time >= self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. Recovery probe allowed in "
                        f"{max(0.0, self._recovery_timeout - (now - self._last_failure_time)):.1f}s"
                    )

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                elif self._state == CircuitState.CLOSED:
                    self._failure_count = 0
            return result
        except Exception as exc:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
                    if self._failure_count >= self._failure_threshold or self._state == CircuitState.HALF_OPEN:
                        self._state = CircuitState.OPEN
            raise exc
