"""Cancellation-safe periodic async scheduler.

Provides:
- AsyncScheduler: runs a coroutine at a fixed interval with overlap protection.
  Never spawns a new cycle while the previous one is still running.
  Uses bounded exponential backoff with jitter on repeated failures.
  Cancellation-safe: stops cleanly when the event loop is shutting down.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger("trading_engine.worker.scheduler")

# Maximum backoff duration so a worker never freezes for too long.
_MAX_BACKOFF_SECONDS = 60.0
_JITTER_FACTOR = 0.2


class AsyncScheduler:
    """Lightweight, cancellation-safe periodic task runner.

    Runs an async callback at ``interval_seconds`` intervals.
    Prevents overlapping executions: if a cycle exceeds the interval,
    the next cycle waits for the current one to finish before starting.

    Failures are tracked; repeated failures trigger exponential backoff
    (capped at ``max_backoff_seconds``) to avoid hammering broken dependencies.

    Args:
        name: Human-readable scheduler name for logging.
        callback: Async callable invoked each cycle.
        interval_seconds: Nominal interval between cycle starts.
        max_backoff_seconds: Maximum backoff on consecutive failures.
        error_hook: Optional async callable(exc) called after each failure.
    """

    def __init__(
        self,
        name: str,
        callback: Callable[[], Coroutine[Any, Any, None]],
        interval_seconds: float,
        max_backoff_seconds: float = _MAX_BACKOFF_SECONDS,
        error_hook: Callable[[Exception], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(f"interval_seconds must be positive, got {interval_seconds!r}")
        self._name = name
        self._callback = callback
        self._interval = interval_seconds
        self._max_backoff = max_backoff_seconds
        self._error_hook = error_hook
        self._consecutive_failures = 0
        self._cycles_started = 0
        self._cycles_completed = 0
        self._cycles_failed = 0
        self._last_cycle_duration: float = 0.0
        self._running = False
        self._task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def cycles_started(self) -> int:
        return self._cycles_started

    @property
    def cycles_completed(self) -> int:
        return self._cycles_completed

    @property
    def cycles_failed(self) -> int:
        return self._cycles_failed

    @property
    def last_cycle_duration(self) -> float:
        return self._last_cycle_duration

    async def start(self) -> None:
        """Start the scheduler loop as a background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name=f"scheduler.{self._name}")
        logger.info("Scheduler '%s' started (interval=%.2fs).", self._name, self._interval)

    async def stop(self) -> None:
        """Stop the scheduler and wait for any in-progress cycle to finish."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info(
            "Scheduler '%s' stopped (cycles: started=%d, completed=%d, failed=%d).",
            self._name,
            self._cycles_started,
            self._cycles_completed,
            self._cycles_failed,
        )

    async def _loop(self) -> None:
        """Main scheduling loop. Runs until self._running is False."""
        while self._running:
            wait = self._backoff_interval()
            try:
                await asyncio.sleep(wait)
            except asyncio.CancelledError:
                break

            if not self._running:
                break

            self._cycles_started += 1
            t0 = time.monotonic()
            try:
                await self._callback()
                self._consecutive_failures = 0
                self._cycles_completed += 1
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._consecutive_failures += 1
                self._cycles_failed += 1
                logger.exception(
                    "Scheduler '%s' cycle %d failed",
                    self._name,
                    self._cycles_started,
                )
                if self._error_hook is not None:
                    try:
                        await self._error_hook(exc)
                    except Exception as hook_exc:  # noqa: BLE001
                        logger.warning("Error hook failed: %s", hook_exc)
            finally:
                self._last_cycle_duration = time.monotonic() - t0

    def _backoff_interval(self) -> float:
        """Return the sleep duration considering backoff and jitter."""
        if self._consecutive_failures == 0:
            base = self._interval
        else:
            base = min(
                self._interval * (2 ** self._consecutive_failures),
                self._max_backoff,
            )
        jitter = base * _JITTER_FACTOR * random.random()
        return base + jitter
