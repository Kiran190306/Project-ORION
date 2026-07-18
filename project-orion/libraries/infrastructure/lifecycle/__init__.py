"""
Project ORION - Application Lifecycle Management

Graceful startup and shutdown management for all services.
Manages service initialization order and cleanup.

Provides:
- Application lifecycle states
- Startup hooks
- Shutdown hooks
- Graceful termination handling
- Signal handling
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional

from libraries.infrastructure.logging import get_logger

logger = get_logger("infrastructure.lifecycle")


class LifecycleState(str, Enum):
    """Application lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class LifecycleHook:
    """A startup or shutdown hook."""

    name: str
    handler: Callable[[], Any]
    priority: int = 0
    timeout_seconds: float = 30.0
    critical: bool = False


class ApplicationLifecycle:
    """
    Manages application startup and shutdown lifecycle.

    Usage:
        lifecycle = ApplicationLifecycle()

        @lifecycle.on_startup(priority=10)
        async def init_database():
            await database.connect()

        @lifecycle.on_shutdown(priority=10)
        async def close_database():
            await database.close()

        await lifecycle.start()
        # ... application runs ...
        await lifecycle.stop()
    """

    def __init__(self) -> None:
        self._state = LifecycleState.CREATED
        self._startup_hooks: list[LifecycleHook] = []
        self._shutdown_hooks: list[LifecycleHook] = []
        self._start_time: Optional[float] = None

    @property
    def state(self) -> LifecycleState:
        """Get current lifecycle state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if the application is running."""
        return self._state == LifecycleState.RUNNING

    @property
    def uptime_seconds(self) -> float:
        """Get application uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def on_startup(
        self,
        priority: int = 0,
        timeout_seconds: float = 30.0,
        critical: bool = False,
    ) -> Callable[..., Any]:
        """
        Decorator to register a startup hook.

        Args:
            priority: Execution order (lower = earlier).
            timeout_seconds: Maximum execution time.
            critical: If True, failure prevents application start.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            hook = LifecycleHook(
                name=func.__name__,
                handler=func,
                priority=priority,
                timeout_seconds=timeout_seconds,
                critical=critical,
            )
            self._startup_hooks.append(hook)
            self._startup_hooks.sort(key=lambda h: h.priority)
            return func

        return decorator

    def on_shutdown(
        self,
        priority: int = 0,
        timeout_seconds: float = 30.0,
        critical: bool = False,
    ) -> Callable[..., Any]:
        """
        Decorator to register a shutdown hook.

        Args:
            priority: Execution order (lower = earlier).
            timeout_seconds: Maximum execution time.
            critical: If True, failure does not prevent shutdown.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            hook = LifecycleHook(
                name=func.__name__,
                handler=func,
                priority=priority,
                timeout_seconds=timeout_seconds,
                critical=critical,
            )
            self._shutdown_hooks.append(hook)
            self._shutdown_hooks.sort(key=lambda h: h.priority)
            return func

        return decorator

    def register_startup_hook(
        self,
        name: str,
        handler: Callable[[], Any],
        priority: int = 0,
        timeout_seconds: float = 30.0,
        critical: bool = False,
    ) -> None:
        """Register a startup hook."""
        hook = LifecycleHook(
            name=name,
            handler=handler,
            priority=priority,
            timeout_seconds=timeout_seconds,
            critical=critical,
        )
        self._startup_hooks.append(hook)
        self._startup_hooks.sort(key=lambda h: h.priority)

    def register_shutdown_hook(
        self,
        name: str,
        handler: Callable[[], Any],
        priority: int = 0,
        timeout_seconds: float = 30.0,
        critical: bool = False,
    ) -> None:
        """Register a shutdown hook."""
        hook = LifecycleHook(
            name=name,
            handler=handler,
            priority=priority,
            timeout_seconds=timeout_seconds,
            critical=critical,
        )
        self._shutdown_hooks.append(hook)
        self._shutdown_hooks.sort(key=lambda h: h.priority)

    async def start(self) -> None:
        """Execute all startup hooks in order."""
        self._state = LifecycleState.STARTING
        self._start_time = time.monotonic()

        logger.info(
            "Starting application with %d startup hooks", len(self._startup_hooks)
        )

        for hook in self._startup_hooks:
            logger.info("Executing startup hook: %s", hook.name)
            try:
                result = hook.handler()
                if isinstance(result, Coroutine):
                    await asyncio.wait_for(result, timeout=hook.timeout_seconds)
                self._state = LifecycleState.RUNNING
            except Exception as exc:
                logger.error(
                    "Startup hook '%s' failed: %s",
                    hook.name,
                    exc,
                )
                if hook.critical:
                    self._state = LifecycleState.FAILED
                    raise RuntimeError(
                        f"Critical startup hook '{hook.name}' failed: {exc}"
                    ) from exc

        self._state = LifecycleState.RUNNING
        logger.info(
            "Application started in %.2fs",
            time.monotonic() - self._start_time,
        )

    async def stop(self) -> None:
        """Execute all shutdown hooks in reverse order."""
        if self._state == LifecycleState.STOPPED:
            return

        self._state = LifecycleState.STOPPING
        logger.info(
            "Stopping application with %d shutdown hooks",
            len(self._shutdown_hooks),
        )

        for hook in reversed(self._shutdown_hooks):
            logger.info("Executing shutdown hook: %s", hook.name)
            try:
                result = hook.handler()
                if isinstance(result, Coroutine):
                    await asyncio.wait_for(result, timeout=hook.timeout_seconds)
            except Exception as exc:
                logger.error(
                    "Shutdown hook '%s' failed: %s",
                    hook.name,
                    exc,
                )

        self._state = LifecycleState.STOPPED
        logger.info("Application stopped")

    def handle_signals(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """
        Register signal handlers for graceful shutdown.

        Args:
            loop: Event loop to use (uses current loop if None).
        """
        loop = loop or asyncio.get_event_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:

                def _make_handler(s: signal.Signals) -> Callable[[], None]:
                    def _handler() -> None:
                        asyncio.create_task(self._signal_handler(s))

                    return _handler

                loop.add_signal_handler(
                    sig,
                    _make_handler(sig),
                )
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        logger.info("Signal handlers registered")

    async def _signal_handler(self, sig: signal.Signals) -> None:
        """Handle OS signals."""
        logger.warning("Received signal: %s", sig.name)
        await self.stop()
        sys.exit(0)


# ─── Singleton ────────────────────────────────────────────────

_lifecycle: Optional[ApplicationLifecycle] = None


def get_lifecycle() -> ApplicationLifecycle:
    """Get the global lifecycle instance."""
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = ApplicationLifecycle()
    return _lifecycle


def reset_lifecycle() -> None:
    """Reset the global lifecycle instance (for testing)."""
    global _lifecycle
    _lifecycle = None
