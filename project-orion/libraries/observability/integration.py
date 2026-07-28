"""Passive observability integration for ORION services.

Provides decorators and context managers that wrap existing service
methods with logging, metrics, and tracing WITHOUT modifying business logic.

Usage:
    from libraries.observability.integration import observe_service, ServiceObserver

    class MyEngine:
        @observe_service("research_engine")
        async def run(self, context):
            ... existing code ...
"""

from __future__ import annotations

import functools
import time
import uuid
from typing import Any, Awaitable, Callable, TypeVar

from libraries.observability.logging import get_logger, set_correlation_id
from libraries.observability.metrics import MetricsRegistry
from libraries.observability.tracing import TracingManager

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

# Global defaults (set during application bootstrap)
_metrics_registry: MetricsRegistry | None = None
_tracing_manager: TracingManager | None = None
_service_name: str = "orion"
_service_version: str = "0.0.0"
_environment: str = "development"


def configure_observability(
    service_name: str = "orion",
    service_version: str = "0.0.0",
    environment: str = "development",
    metrics_registry: MetricsRegistry | None = None,
    tracing_manager: TracingManager | None = None,
) -> None:
    """Configure global observability defaults for integration decorators."""
    global _service_name, _service_version, _environment, _metrics_registry, _tracing_manager
    _service_name = service_name
    _service_version = service_version
    _environment = environment
    _metrics_registry = metrics_registry
    _tracing_manager = tracing_manager


def observe_service(
    component: str = "",
    metrics: bool = True,
    tracing: bool = True,
    logging_enabled: bool = True,
) -> Callable[[F], F]:
    """Decorator that wraps an async method with observability.

    Adds:
    - Correlation ID generation (if none present)
    - Execution duration logging
    - Success/failure metrics
    - Tracing span creation
    - Exception capture

    Usage:
        @observe_service("research_engine.run")
        async def run(self, context):
            ...

    Args:
        component: Name for the component being observed (for metrics/tracing).
        metrics: Whether to record metrics.
        tracing: Whether to create tracing spans.
        logging_enabled: Whether to log entry/exit.

    Returns:
        Decorated async function.
    """

    def decorator(func: F) -> F:
        operation_name = component or func.__qualname__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate correlation ID if not set
            correlation_id = getattr(args[0], "_correlation_id", None) if args else None
            if not correlation_id:
                correlation_id = uuid.uuid4().hex
                set_correlation_id(correlation_id)

            logger = get_logger(_service_name)
            start_time = time.time()

            span = None
            if tracing and _tracing_manager and _tracing_manager.is_enabled():
                span_ctx = _tracing_manager.start_span(operation_name)
                span = span_ctx.__enter__()

            try:
                if logging_enabled:
                    logger.info(
                        f"Executing {operation_name}",
                        component=operation_name,
                        operation="start",
                        correlation_id=correlation_id,
                    )

                result = await func(*args, **kwargs)

                elapsed = time.time() - start_time

                if metrics and _metrics_registry:
                    try:
                        _metrics_registry.inc(f"{operation_name}_total")
                        _metrics_registry.observe(f"{operation_name}_duration_seconds", elapsed)
                    except Exception:
                        pass

                if logging_enabled:
                    logger.info(
                        f"Completed {operation_name}",
                        component=operation_name,
                        operation="end",
                        duration_ms=round(elapsed * 1000, 2),
                        correlation_id=correlation_id,
                    )

                return result

            except Exception as exc:
                elapsed = time.time() - start_time

                if metrics and _metrics_registry:
                    try:
                        _metrics_registry.inc(f"{operation_name}_errors_total")
                        _metrics_registry.observe(f"{operation_name}_duration_seconds", elapsed)
                    except Exception:
                        pass

                logger.error(
                    f"Failed {operation_name}: {exc!s}",
                    component=operation_name,
                    operation="error",
                    error=str(exc),
                    duration_ms=round(elapsed * 1000, 2),
                    correlation_id=correlation_id,
                )

                if span:
                    span.set_attribute("error", str(exc))
                    span.set_attribute("error.type", type(exc).__name__)

                raise
            finally:
                if span and span_ctx:
                    try:
                        span_ctx.__exit__(None, None, None)
                    except Exception:
                        pass

        return wrapper  # type: ignore[return-value]

    return decorator


class ServiceObserver:
    """Manages observability for an entire service engine.

    Wraps all public async methods with logging, metrics, and tracing.
    Does NOT modify the underlying service's behavior.

    Usage:
        engine = AIResearchEngine(...)
        observed = ServiceObserver(engine, "research_engine")
        await observed.run(context)  # transparently observed
    """

    def __init__(
        self,
        service: Any,
        service_name: str = "service",
        metrics_enabled: bool = True,
        tracing_enabled: bool = True,
        logging_enabled: bool = True,
    ) -> None:
        self._service = service
        self._service_name = service_name
        self._metrics_enabled = metrics_enabled
        self._tracing_enabled = tracing_enabled
        self._logging_enabled = logging_enabled

    @property
    def wrapped(self) -> Any:
        return self._service

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to wrapped service, decorating async methods."""
        attr = getattr(self._service, name)
        if not callable(attr):
            return attr

        # Decorate async methods
        if hasattr(attr, "__code__") or hasattr(attr, "__await__"):
            return observe_service(
                component=f"{self._service_name}.{name}",
                metrics=self._metrics_enabled,
                tracing=self._tracing_enabled,
                logging_enabled=self._logging_enabled,
            )(attr)

        return attr

    async def health(self) -> dict[str, Any]:
        """Return health status of the observed service."""
        base = {
            "service": self._service_name,
            "observed": True,
        }
        # Try to call the service's own health_check if it exists
        health_fn = getattr(self._service, "health_check", None)
        if callable(health_fn):
            try:
                result = await health_fn()
                if isinstance(result, dict):
                    base.update(result)
            except Exception:
                base["health_error"] = "health_check failed"
        return base

    async def health_check(self) -> dict[str, Any]:
        """Alias for health()."""
        return await self.health()
