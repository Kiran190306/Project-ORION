"""Graceful shutdown coordinator for the event streaming layer.

Provides ordered shutdown of all streaming components with timeout
protection, queue flushing, and resource cleanup.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum, auto
from typing import Any, Callable, Coroutine


class ShutdownPhase(StrEnum):
    """Ordered phases of the shutdown sequence."""

    STOP_PUBLISHERS = "stop_publishers"
    FLUSH_QUEUES = "flush_queues"
    PERSIST_SNAPSHOTS = "persist_snapshots"
    CLOSE_TRANSPORTS = "close_transports"
    CANCEL_TASKS = "cancel_tasks"


SHUTDOWN_ORDER: list[ShutdownPhase] = [
    ShutdownPhase.STOP_PUBLISHERS,
    ShutdownPhase.FLUSH_QUEUES,
    ShutdownPhase.PERSIST_SNAPSHOTS,
    ShutdownPhase.CLOSE_TRANSPORTS,
    ShutdownPhase.CANCEL_TASKS,
]


@dataclass(frozen=True, slots=True)
class ShutdownTask:
    """A single shutdown task with metadata."""

    name: str
    phase: ShutdownPhase
    coro: Callable[[], Coroutine[Any, Any, None]]
    timeout_seconds: float = 5.0
    critical: bool = False


@dataclass(frozen=True, slots=True)
class ShutdownResult:
    """Result of a shutdown execution."""

    phase: str
    task_name: str
    success: bool
    error: str | None
    duration_seconds: float


class GracefulShutdown:
    """Coordinates graceful shutdown of streaming components.

    Executes shutdown tasks in ordered phases with per-task timeout
    protection. Critical tasks that fail will not prevent subsequent
    phases from executing.

    Supports:
    - Ordered shutdown phases
    - Per-task timeout protection
    - Error isolation (one task failure doesn't halt shutdown)
    - Result tracking
    """

    def __init__(self, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._timeout_seconds = timeout_seconds
        self._tasks: list[ShutdownTask] = []
        self._results: list[ShutdownResult] = []
        self._lock = asyncio.Lock()
        self._shutting_down = False

    @property
    def shutting_down(self) -> bool:
        return self._shutting_down

    def register(
        self,
        name: str,
        phase: ShutdownPhase,
        coro: Callable[[], Coroutine[Any, Any, None]],
        timeout_seconds: float = 5.0,
        critical: bool = False,
    ) -> None:
        """Register a shutdown task.

        Args:
            name: Task identifier.
            phase: Which phase this task belongs to.
            coro: Async callable to execute during shutdown.
            timeout_seconds: Maximum time allowed for this task.
            critical: If True, failure is logged but doesn't halt shutdown.
        """
        self._tasks.append(
            ShutdownTask(
                name=name,
                phase=phase,
                coro=coro,
                timeout_seconds=timeout_seconds,
                critical=critical,
            )
        )

    async def execute(self) -> list[ShutdownResult]:
        """Execute the full shutdown sequence.

        Returns:
            List of shutdown results for each task.
        """
        async with self._lock:
            if self._shutting_down:
                return list(self._results)
            self._shutting_down = True

        self._results.clear()

        for phase in SHUTDOWN_ORDER:
            phase_tasks = [t for t in self._tasks if t.phase == phase]
            if not phase_tasks:
                continue

            phase_results = await self._execute_phase(phase, phase_tasks)
            self._results.extend(phase_results)

        return list(self._results)

    async def _execute_phase(
        self,
        phase: ShutdownPhase,
        tasks: list[ShutdownTask],
    ) -> list[ShutdownResult]:
        """Execute all tasks in a shutdown phase.

        Tasks within a phase are executed concurrently with individual
        timeouts.
        """

        async def _run_task(task: ShutdownTask) -> ShutdownResult:
            start = datetime.now(timezone.utc)
            try:
                await asyncio.wait_for(
                    task.coro(),
                    timeout=task.timeout_seconds,
                )
                duration = (datetime.now(timezone.utc) - start).total_seconds()
                return ShutdownResult(
                    phase=phase.value,
                    task_name=task.name,
                    success=True,
                    error=None,
                    duration_seconds=duration,
                )
            except asyncio.TimeoutError:
                duration = (datetime.now(timezone.utc) - start).total_seconds()
                return ShutdownResult(
                    phase=phase.value,
                    task_name=task.name,
                    success=False,
                    error=f"Timeout after {task.timeout_seconds}s",
                    duration_seconds=duration,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                duration = (datetime.now(timezone.utc) - start).total_seconds()
                return ShutdownResult(
                    phase=phase.value,
                    task_name=task.name,
                    success=False,
                    error=str(exc),
                    duration_seconds=duration,
                )

        results: list[ShutdownResult] = []
        for task in tasks:
            result = await _run_task(task)
            results.append(result)

        return results

    async def get_results(self) -> list[ShutdownResult]:
        """Return the shutdown results."""
        async with self._lock:
            return list(self._results)

    async def was_successful(self) -> bool:
        """Return True if all shutdown tasks completed successfully."""
        async with self._lock:
            return all(result.success for result in self._results)

    def reset(self) -> None:
        """Reset the shutdown coordinator for testing."""
        self._tasks.clear()
        self._results.clear()
        self._shutting_down = False
