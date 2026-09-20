"""Worker lifecycle state machine.

Manages atomic state transitions for the autonomous trading worker:
  STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED

Thread-safe via asyncio.Lock. No global mutable state.
"""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger("trading_engine.worker.lifecycle")


class WorkerState(StrEnum):
    """States for the autonomous trading worker."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class WorkerLifecycle:
    """Manages the lifecycle state of the autonomous worker.

    Provides atomic state transitions guarded by asyncio.Lock.
    Tracks spawned background tasks for clean drainage on shutdown.
    """

    def __init__(self) -> None:
        self._state = WorkerState.STOPPED
        self._lock = asyncio.Lock()
        self._tasks: list[asyncio.Task[Any]] = []

    @property
    def state(self) -> WorkerState:
        """Return the current worker state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Return True if the worker is currently running."""
        return self._state == WorkerState.RUNNING

    @property
    def is_stopped(self) -> bool:
        """Return True if the worker is stopped."""
        return self._state == WorkerState.STOPPED

    async def transition_to(self, new_state: WorkerState) -> bool:
        """Atomically transition to new_state if the transition is valid.

        Valid transitions:
            STOPPED -> STARTING
            STARTING -> RUNNING
            STARTING -> STOPPED  (startup error)
            RUNNING -> STOPPING
            STOPPING -> STOPPED

        Returns True if the transition succeeded, False if it was invalid.
        """
        async with self._lock:
            valid = _VALID_TRANSITIONS.get(self._state, set())
            if new_state not in valid:
                logger.warning(
                    "Invalid state transition %s -> %s; ignoring.",
                    self._state,
                    new_state,
                )
                return False
            old = self._state
            self._state = new_state
            logger.info("Worker state: %s -> %s", old, new_state)
            return True

    def register_task(self, task: asyncio.Task[Any]) -> None:
        """Register a managed background task."""
        self._tasks.append(task)

    async def drain_tasks(self, timeout_seconds: float = 5.0) -> None:
        """Cancel all registered tasks and wait for them to finish.

        Args:
            timeout_seconds: Maximum time to wait for task cancellation.
        """
        active = [t for t in self._tasks if not t.done()]
        if not active:
            self._tasks.clear()
            return

        logger.info("Draining %d worker task(s)...", len(active))
        for task in active:
            task.cancel()

        await asyncio.wait(active, timeout=timeout_seconds)

        still_pending = [t for t in active if not t.done()]
        if still_pending:
            logger.warning("%d task(s) did not cancel within timeout.", len(still_pending))

        self._tasks.clear()
        logger.info("Worker task drainage complete.")


# Valid state machine transitions
_VALID_TRANSITIONS: dict[WorkerState, set[WorkerState]] = {
    WorkerState.STOPPED: {WorkerState.STARTING},
    WorkerState.STARTING: {WorkerState.RUNNING, WorkerState.STOPPED},
    WorkerState.RUNNING: {WorkerState.STOPPING},
    WorkerState.STOPPING: {WorkerState.STOPPED},
}
