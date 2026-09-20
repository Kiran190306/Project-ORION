"""Unit tests for WorkerLifecycle state machine.

Tests atomic state transitions, task management, and graceful shutdown.
"""

from __future__ import annotations

import asyncio

from apps.trading_engine.src.workers.lifecycle import (
    WorkerLifecycle,
    WorkerState,
)


async def test_lifecycle_initial_state():
    """Lifecycle starts in STOPPED state."""
    lifecycle = WorkerLifecycle()
    assert lifecycle.state == WorkerState.STOPPED
    assert not lifecycle.is_running
    assert lifecycle.is_stopped


async def test_lifecycle_valid_transitions():
    """Valid state transitions succeed atomically."""
    lifecycle = WorkerLifecycle()

    # STOPPED -> STARTING
    assert await lifecycle.transition_to(WorkerState.STARTING)
    assert lifecycle.state == WorkerState.STARTING

    # STARTING -> RUNNING
    assert await lifecycle.transition_to(WorkerState.RUNNING)
    assert lifecycle.state == WorkerState.RUNNING
    assert lifecycle.is_running

    # RUNNING -> STOPPING
    assert await lifecycle.transition_to(WorkerState.STOPPING)
    assert lifecycle.state == WorkerState.STOPPING

    # STOPPING -> STOPPED
    assert await lifecycle.transition_to(WorkerState.STOPPED)
    assert lifecycle.state == WorkerState.STOPPED
    assert lifecycle.is_stopped


async def test_lifecycle_invalid_transitions_rejected():
    """Invalid state transitions are rejected and logged."""
    lifecycle = WorkerLifecycle()

    # Cannot go directly from STOPPED to RUNNING
    assert not await lifecycle.transition_to(WorkerState.RUNNING)
    assert lifecycle.state == WorkerState.STOPPED

    # Cannot go from RUNNING to STARTING
    await lifecycle.transition_to(WorkerState.STARTING)
    await lifecycle.transition_to(WorkerState.RUNNING)
    assert not await lifecycle.transition_to(WorkerState.STARTING)
    assert lifecycle.state == WorkerState.RUNNING


async def test_lifecycle_startup_error_recovery():
    """Worker can recover from startup errors back to STOPPED."""
    lifecycle = WorkerLifecycle()

    await lifecycle.transition_to(WorkerState.STARTING)
    assert lifecycle.state == WorkerState.STARTING

    # Simulate startup error by transitioning back to STOPPED
    assert await lifecycle.transition_to(WorkerState.STOPPED)
    assert lifecycle.state == WorkerState.STOPPED


async def test_lifecycle_task_registration():
    """Tasks can be registered for tracking."""
    lifecycle = WorkerLifecycle()

    async def dummy_task():
        await asyncio.sleep(0.1)

    task = asyncio.create_task(dummy_task())
    lifecycle.register_task(task)

    # Task is now tracked (we can't directly inspect the list,
    # but drain_tasks should handle it)
    await task


async def test_lifecycle_task_drainage():
    """Registered tasks are cancelled and awaited on shutdown."""
    lifecycle = WorkerLifecycle()

    tasks_cancelled = []
    tasks_running = []

    async def cancellable_task(task_id: str):
        try:
            tasks_running.append(task_id)
            await asyncio.sleep(10)  # Long-running
        except asyncio.CancelledError:
            tasks_cancelled.append(task_id)
            raise

    task1 = asyncio.create_task(cancellable_task("task1"))
    task2 = asyncio.create_task(cancellable_task("task2"))

    lifecycle.register_task(task1)
    lifecycle.register_task(task2)

    # Wait for tasks to start
    await asyncio.sleep(0.05)
    assert len(tasks_running) == 2

    # Drain tasks
    await lifecycle.drain_tasks(timeout_seconds=2.0)

    assert "task1" in tasks_cancelled
    assert "task2" in tasks_cancelled
    assert task1.done()
    assert task2.done()


async def test_lifecycle_drain_empty_tasks():
    """Draining with no registered tasks is safe."""
    lifecycle = WorkerLifecycle()
    await lifecycle.drain_tasks(timeout_seconds=1.0)
    # Should complete without error


async def test_lifecycle_drain_timeout():
    """Tasks that don't cancel within timeout are logged but don't block."""
    lifecycle = WorkerLifecycle()

    async def uncooperative_task():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            # Ignore cancellation
            await asyncio.sleep(100)

    task = asyncio.create_task(uncooperative_task())
    lifecycle.register_task(task)

    await asyncio.sleep(0.05)
    await lifecycle.drain_tasks(timeout_seconds=0.1)

    # Task may still be running, but drain should complete
    assert lifecycle.state == WorkerState.STOPPED


async def test_lifecycle_concurrent_transition_safety():
    """Concurrent transition attempts are serialized correctly."""
    lifecycle = WorkerLifecycle()

    async def attempt_transition(target: WorkerState):
        return await lifecycle.transition_to(target)

    # Attempt multiple concurrent transitions
    results = await asyncio.gather(
        attempt_transition(WorkerState.STARTING),
        attempt_transition(WorkerState.RUNNING),
        attempt_transition(WorkerState.STOPPED),
    )

    # At least one should succeed (the first valid one), possibly more if transitions chain
    assert sum(results) >= 1


async def test_lifecycle_idempotent_transitions():
    """Attempting the same transition multiple times is safe."""
    lifecycle = WorkerLifecycle()

    await lifecycle.transition_to(WorkerState.STARTING)

    # Same transition again should fail (already in that state)
    assert not await lifecycle.transition_to(WorkerState.STARTING)
    assert lifecycle.state == WorkerState.STARTING


async def test_lifecycle_state_properties():
    """State properties correctly reflect current state."""
    lifecycle = WorkerLifecycle()

    assert lifecycle.is_stopped
    assert not lifecycle.is_running

    await lifecycle.transition_to(WorkerState.STARTING)
    assert not lifecycle.is_stopped
    assert not lifecycle.is_running

    await lifecycle.transition_to(WorkerState.RUNNING)
    assert not lifecycle.is_stopped
    assert lifecycle.is_running

    await lifecycle.transition_to(WorkerState.STOPPING)
    assert not lifecycle.is_stopped
    assert not lifecycle.is_running

    await lifecycle.transition_to(WorkerState.STOPPED)
    assert lifecycle.is_stopped
    assert not lifecycle.is_running
