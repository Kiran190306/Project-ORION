"""Tests for CircuitBreaker."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)


class TestCircuitBreaker:
    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker(
            CircuitBreakerConfig(name="test", failure_threshold=3, success_threshold=2)
        )
        assert cb.state == CircuitState.CLOSED

    def test_trips_to_open_on_failures(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="test", failure_threshold=3, success_threshold=2)
            )

            async def failing_fn() -> None:
                raise ValueError("test error")

            for _ in range(3):
                with pytest.raises(ValueError):
                    await cb.call(failing_fn)

            assert cb.state == CircuitState.OPEN

        asyncio.run(exercise())

    def test_open_circuit_rejects_calls(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="test", failure_threshold=1, success_threshold=2)
            )

            async def failing_fn() -> None:
                raise ValueError("test error")

            with pytest.raises(ValueError):
                await cb.call(failing_fn)

            with pytest.raises(CircuitBreakerOpenError):
                await cb.call(failing_fn)

        asyncio.run(exercise())

    def test_half_open_allows_limited_calls(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(
                    name="test",
                    failure_threshold=1,
                    success_threshold=2,
                    recovery_timeout_seconds=0.01,
                    half_open_max_calls=1,
                )
            )

            async def failing_fn() -> None:
                raise ValueError("test error")

            async def succeeding_fn() -> str:
                return "ok"

            # Trip to open
            with pytest.raises(ValueError):
                await cb.call(failing_fn)

            assert cb.state == CircuitState.OPEN

            # Wait for recovery timeout
            await asyncio.sleep(0.02)

            # Should be half-open now
            assert cb.state == CircuitState.HALF_OPEN

            # First call succeeds -> stays half-open
            result = await cb.call(succeeding_fn)
            assert result == "ok"

        asyncio.run(exercise())

    def test_recovery_from_half_open_to_closed(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(
                    name="test",
                    failure_threshold=1,
                    success_threshold=2,
                    recovery_timeout_seconds=0.01,
                    half_open_max_calls=2,
                )
            )

            async def failing_fn() -> None:
                raise ValueError("test error")

            async def succeeding_fn() -> str:
                return "ok"

            # Trip to open
            with pytest.raises(ValueError):
                await cb.call(failing_fn)

            # Wait for half-open
            await asyncio.sleep(0.02)

            # Succeed twice to close
            await cb.call(succeeding_fn)
            await cb.call(succeeding_fn)

            assert cb.state == CircuitState.CLOSED

        asyncio.run(exercise())

    def test_force_open_and_force_close(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="test", failure_threshold=5, success_threshold=3)
            )

            await cb.force_open()
            assert cb.state == CircuitState.OPEN

            await cb.force_close()
            assert cb.state == CircuitState.CLOSED

        asyncio.run(exercise())

    def test_get_stats_returns_accurate_data(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="stats_test", failure_threshold=3, success_threshold=2)
            )

            async def failing_fn() -> None:
                raise ValueError("error")

            async def succeeding_fn() -> str:
                return "ok"

            with pytest.raises(ValueError):
                await cb.call(failing_fn)

            stats = await cb.get_stats()
            assert stats.name == "stats_test"
            assert stats.state == CircuitState.CLOSED.value
            assert stats.total_calls == 1
            assert stats.total_failures == 1

        asyncio.run(exercise())

    def test_validates_config(self) -> None:
        with pytest.raises(ValueError):
            CircuitBreakerConfig(name="test", failure_threshold=0)
        with pytest.raises(ValueError):
            CircuitBreakerConfig(name="test", success_threshold=0)
        with pytest.raises(ValueError):
            CircuitBreakerConfig(name="test", recovery_timeout_seconds=0)
        with pytest.raises(ValueError):
            CircuitBreakerConfig(name="test", half_open_max_calls=0)

    def test_success_counters_reset_on_failure_in_closed(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="test", failure_threshold=3, success_threshold=2)
            )

            async def succeed() -> str:
                return "ok"

            async def fail() -> None:
                raise ValueError("err")

            # Succeed then fail
            await cb.call(succeed)
            with pytest.raises(ValueError):
                await cb.call(fail)

            stats = await cb.get_stats()
            assert stats.total_successes == 1
            assert stats.total_failures == 1

        asyncio.run(exercise())

    def test_timeout_counted_as_failure(self) -> None:
        async def exercise() -> None:
            cb = CircuitBreaker(
                CircuitBreakerConfig(name="test", failure_threshold=1, success_threshold=1)
            )

            async def slow_fn() -> None:
                await asyncio.sleep(10)

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(cb.call(slow_fn), timeout=0.01)

            assert cb.state == CircuitState.OPEN

        asyncio.run(exercise())
