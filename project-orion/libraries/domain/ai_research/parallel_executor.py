"""Async parallel execution framework.

Provides a worker pool abstraction with cancellation, progress callbacks,
exception isolation, and result aggregation. No direct threading assumptions.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Callable, Coroutine

from libraries.domain.ai_research.exceptions import ParallelExecutionError
from libraries.domain.ai_research.models import ProgressReport, TaskResult


class ParallelExecutor:
    """Async-aware worker pool for parallel task execution.

    Supports:
        - Worker pool abstraction
        - Async execution
        - Cancellation
        - Progress callbacks
        - Exception isolation
        - Result aggregation
    """

    def __init__(
        self,
        max_workers: int = 4,
        progress_callback: Callable[[ProgressReport], None] | None = None,
    ) -> None:
        if max_workers < 1:
            raise ParallelExecutionError("max_workers must be at least 1")
        self._max_workers = max_workers
        self._progress_callback = progress_callback
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Cancel all pending and running tasks."""
        self._cancelled = True

    async def execute(
        self,
        tasks: tuple[Callable[[], Coroutine[Any, Any, Any]] | Coroutine[Any, Any, Any], ...],
    ) -> tuple[TaskResult, ...]:
        """Execute a batch of tasks concurrently.

        Args:
            tasks: Tuple of async callables or coroutines to execute.

        Returns:
            Tuple of task results.
        """
        if not tasks:
            return ()

        total = len(tasks)
        completed = 0
        errors = 0
        results: list[TaskResult] = []

        semaphore = asyncio.Semaphore(self._max_workers)

        async def _run(
            task: Callable[[], Coroutine[Any, Any, Any]] | Coroutine[Any, Any, Any], task_id: str
        ) -> TaskResult:
            nonlocal completed, errors

            if self._cancelled:
                return TaskResult(task_id=task_id, success=False, error="cancelled")

            async with semaphore:
                if self._cancelled:
                    return TaskResult(task_id=task_id, success=False, error="cancelled")
                try:
                    if asyncio.iscoroutine(task):
                        result = await task
                    else:
                        result = await task()
                    completed += 1
                    self._report_progress(completed, total, errors)
                    return TaskResult(task_id=task_id, success=True, result=result)
                except Exception as exc:
                    errors += 1
                    completed += 1
                    self._report_progress(completed, total, errors)
                    return TaskResult(
                        task_id=task_id,
                        success=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )

        # Assign task IDs and create coroutines
        coros = []
        for i, task in enumerate(tasks):
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            coros.append(_run(task, task_id))

        # Run concurrently with semaphore limiting
        raw_results = await asyncio.gather(*coros, return_exceptions=False)

        # Add results
        for result in raw_results:
            if isinstance(result, TaskResult):
                results.append(result)

        # Final progress report
        self._report_progress(completed, total, errors, message="completed")

        return tuple(results)

    def _report_progress(self, completed: int, total: int, errors: int, message: str = "") -> None:
        """Report progress via callback if set."""
        if self._progress_callback:
            self._progress_callback(
                ProgressReport(
                    completed=completed,
                    total=total,
                    errors=errors,
                    message=message,
                )
            )
