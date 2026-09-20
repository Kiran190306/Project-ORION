"""Unit tests for the AsyncScheduler.

Tests cancellation-safe periodic task scheduling with overlap protection,
bounded backoff, and error isolation.
"""

from __future__ import annotations

import asyncio

import pytest
from apps.trading_engine.src.workers.scheduler import AsyncScheduler


async def test_scheduler_rejects_non_positive_interval():
    """Scheduler must reject intervals <= 0."""
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        AsyncScheduler(
            name="test",
            callback=lambda: asyncio.sleep(0),
            interval_seconds=0.0,
        )


async def test_scheduler_lifecycle_start_stop():
    """Scheduler starts and stops cleanly with background task management."""
    call_count = 0

    async def callback():
        nonlocal call_count
        call_count += 1

    scheduler = AsyncScheduler(
        name="test_lifecycle",
        callback=callback,
        interval_seconds=0.1,
    )

    assert not scheduler.is_running
    assert scheduler.cycles_started == 0

    await scheduler.start()
    assert scheduler.is_running
    assert scheduler.cycles_started == 0  # No immediate execution

    # Wait for at least one cycle
    await asyncio.sleep(0.15)
    assert scheduler.cycles_started >= 1
    assert scheduler.cycles_completed >= 1

    await scheduler.stop()
    assert not scheduler.is_running
    assert scheduler.cycles_completed >= 1


async def test_scheduler_overlap_protection():
    """Scheduler prevents overlapping executions when callback exceeds interval."""
    callback_running = asyncio.Event()
    callback_can_finish = asyncio.Event()
    max_concurrent = 0
    active_count = 0

    async def slow_callback():
        nonlocal max_concurrent, active_count
        active_count += 1
        max_concurrent = max(max_concurrent, active_count)
        callback_running.set()
        await callback_can_finish.wait()
        active_count -= 1

    scheduler = AsyncScheduler(
        name="overlap_test",
        callback=slow_callback,
        interval_seconds=0.05,  # Short interval
    )

    await scheduler.start()
    await callback_running.wait()  # Wait for first cycle to start

    # Let it try to start another cycle while first is still running
    await asyncio.sleep(0.1)

    callback_can_finish.set()  # Allow first cycle to finish
    await asyncio.sleep(0.05)  # Allow cleanup

    await scheduler.stop()

    # Should never have more than 1 concurrent execution
    assert max_concurrent == 1


async def test_scheduler_backoff_on_failures():
    """Scheduler applies exponential backoff with jitter on consecutive failures."""
    failure_count = 0

    async def failing_callback():
        nonlocal failure_count
        failure_count += 1
        if failure_count < 3:
            raise RuntimeError("Simulated failure")

    scheduler = AsyncScheduler(
        name="backoff_test",
        callback=failing_callback,
        interval_seconds=0.05,  # Shorter interval for faster testing
        max_backoff_seconds=2.0,
    )

    await scheduler.start()
    await asyncio.sleep(1.0)  # Allow more time for attempts with backoff
    await scheduler.stop()

    assert failure_count >= 2  # At least 2 failures occurred
    assert scheduler.cycles_failed >= 1


async def test_scheduler_error_hook_invocation():
    """Error hook is called after each failure."""
    errors_caught = []

    async def error_hook(exc: Exception):
        errors_caught.append(exc)

    async def failing_callback():
        raise ValueError("Test error")

    scheduler = AsyncScheduler(
        name="error_hook_test",
        callback=failing_callback,
        interval_seconds=0.1,
        error_hook=error_hook,
    )

    await scheduler.start()
    await asyncio.sleep(0.3)
    await scheduler.stop()

    assert len(errors_caught) >= 1
    assert all(isinstance(e, ValueError) for e in errors_caught)


async def test_scheduler_cancellation_safety():
    """Scheduler handles cancellation gracefully without hanging."""
    started = asyncio.Event()
    should_block = asyncio.Event()

    async def blocking_callback():
        started.set()
        await should_block.wait()

    scheduler = AsyncScheduler(
        name="cancel_test",
        callback=blocking_callback,
        interval_seconds=0.1,
    )

    await scheduler.start()
    await started.wait()

    # Cancel while callback is running
    stop_task = asyncio.create_task(scheduler.stop())
    should_block.set()  # Allow callback to finish

    await asyncio.wait_for(stop_task, timeout=2.0)
    assert not scheduler.is_running


async def test_scheduler_idempotent_start_stop():
    """Multiple start/stop calls are safe and idempotent."""
    async def callback():
        pass

    scheduler = AsyncScheduler(
        name="idempotent_test",
        callback=callback,
        interval_seconds=0.1,
    )

    # Multiple starts
    await scheduler.start()
    await scheduler.start()
    assert scheduler.is_running

    # Multiple stops
    await scheduler.stop()
    await scheduler.stop()
    assert not scheduler.is_running


async def test_scheduler_metrics_tracking():
    """Scheduler accurately tracks cycle metrics."""
    successes = 0
    failures = 0

    async def mixed_callback():
        nonlocal successes, failures
        if successes < 2:
            successes += 1
        else:
            failures += 1
            raise RuntimeError("Intentional failure")

    scheduler = AsyncScheduler(
        name="metrics_test",
        callback=mixed_callback,
        interval_seconds=0.05,
    )

    await scheduler.start()
    await asyncio.sleep(0.3)
    await scheduler.stop()

    assert scheduler.cycles_started >= 3
    assert scheduler.cycles_completed >= 2
    assert scheduler.cycles_failed >= 1
    assert scheduler.last_cycle_duration >= 0


async def test_scheduler_zero_interval_rejection():
    """Zero interval is rejected with clear error message."""
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        AsyncScheduler(
            name="zero_interval",
            callback=lambda: asyncio.sleep(0),
            interval_seconds=0.0,
        )


async def test_scheduler_negative_interval_rejection():
    """Negative interval is rejected with clear error message."""
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        AsyncScheduler(
            name="negative_interval",
            callback=lambda: asyncio.sleep(0),
            interval_seconds=-1.0,
        )
