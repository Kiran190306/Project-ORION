"""Observability middleware for ASGI/WSGI applications.

Provides correlation ID generation, tracing attachment,
latency recording, metrics emission, structured logging,
and exception capture.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from libraries.observability.logging import get_logger, set_correlation_id, set_trace_ids
from libraries.observability.metrics import MetricsRegistry
from libraries.observability.tracing import TracingManager


class ObservabilityMiddleware:
    """Combined observability middleware for ASGI applications.

    Wraps an ASGI application (Starlette/FastAPI) to provide
    correlation IDs, tracing, metrics, and structured logging.

    Usage:
        app = ...
        app = ObservabilityMiddleware(
            app,
            service_name="trading-engine",
            metrics_registry=registry,
            tracer=tracer,
        )
    """

    def __init__(
        self,
        app: Any,
        service_name: str = "orion",
        metrics_registry: MetricsRegistry | None = None,
        tracer: TracingManager | None = None,
        exclude_paths: set[str] | None = None,
    ) -> None:
        self._app = app
        self._service_name = service_name
        self._metrics = metrics_registry
        self._tracer = tracer
        self._exclude_paths = exclude_paths or {"/health", "/metrics", "/favicon.ico"}
        self._logger = get_logger(f"{service_name}.middleware")

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._exclude_paths:
            await self._app(scope, receive, send)
            return

        # Generate correlation ID
        correlation_id = scope.get("headers", {}).get("x-correlation-id", uuid.uuid4().hex)
        set_correlation_id(correlation_id)

        # Trace
        span = None
        if self._tracer and self._tracer.is_enabled():
            span_ctx = self._tracer.start_span(f"{scope['method']} {path}")
            span = span_ctx.__enter__()  # type: ignore[union-attr]

        # Record start time
        start_time = time.time()

        # Metrics
        if self._metrics:
            try:
                self._metrics.inc(f"http_requests_total", 1.0)
            except Exception:
                pass

        # Wrap send to capture status
        status_code = 200

        async def wrapped_send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self._app(scope, receive, wrapped_send)
            duration = time.time() - start_time

            # Record metrics
            if self._metrics:
                try:
                    self._metrics.inc(f"http_requests_total")
                    self._metrics.observe(f"http_request_duration_seconds", duration)
                except Exception:
                    pass

            # Log
            self._logger.info(
                f"{scope['method']} {path} -> {status_code}",
                method=scope["method"],
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
                correlation_id=correlation_id,
            )

        except Exception as exc:
            duration = time.time() - start_time
            self._logger.error(
                f"Request failed: {scope['method']} {path}",
                method=scope["method"],
                path=path,
                status_code=500,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                correlation_id=correlation_id,
            )
            if self._metrics:
                try:
                    self._metrics.inc(f"http_errors_total")
                except Exception:
                    pass
            raise
        finally:
            if span:
                span.set_attribute("http.method", scope.get("method", ""))
                span.set_attribute("http.path", path)
                span.set_attribute("http.status_code", status_code)
                span_ctx.__exit__(None, None, None)  # type: ignore[union-attr]

            set_correlation_id("")


class CorrelationIdMiddleware:
    """Middleware that only adds correlation IDs without other observability."""

    def __init__(self, app: Any, header_name: str = "x-correlation-id") -> None:
        self._app = app
        self._header_name = header_name

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers", {}))
        correlation_id = str(headers.get(self._header_name, uuid.uuid4().hex))
        set_correlation_id(correlation_id)

        try:
            await self._app(scope, receive, send)
        finally:
            set_correlation_id("")


class RequestMetricsMiddleware:
    """Middleware that only records request metrics."""

    def __init__(
        self,
        app: Any,
        metrics_registry: MetricsRegistry,
        exclude_paths: set[str] | None = None,
    ) -> None:
        self._app = app
        self._metrics = metrics_registry
        self._exclude_paths = exclude_paths or {"/health", "/metrics"}

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._exclude_paths:
            await self._app(scope, receive, send)
            return

        start = time.time()

        async def wrapped_send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status = message.get("status", 200)
                duration = time.time() - start
                try:
                    self._metrics.inc(f"http_requests_total")
                    self._metrics.observe(f"http_request_duration_seconds", duration)
                    if status >= 500:
                        self._metrics.inc(f"http_errors_total")
                except Exception:
                    pass
            await send(message)

        await self._app(scope, receive, wrapped_send)
