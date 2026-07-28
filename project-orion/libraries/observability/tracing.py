"""OpenTelemetry tracing support for ORION services.

Provides trace propagation, nested spans, context propagation,
sampling configuration, and exporter abstraction.
"""

from __future__ import annotations

import contextlib
import uuid
from enum import StrEnum
from threading import local
from typing import Any, Callable

from libraries.observability.config import TracingConfig


class TracingError(Exception):
    """Tracing operation error."""


class TraceExporterType(StrEnum):
    """Supported trace exporter types."""

    CONSOLE = "console"
    GRPC = "grpc"
    HTTP = "http"


class _Span:
    """Internal span representation."""

    def __init__(self, name: str, trace_id: str, parent_span_id: str | None = None) -> None:
        self.name = name
        self.trace_id = trace_id
        self.span_id = uuid.uuid4().hex[:16]
        self.parent_span_id = parent_span_id
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.attributes: dict[str, Any] = {}
        self.status: str = "UNSET"
        self.status_description: str = ""

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000.0
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": self.duration_ms,
            "attributes": dict(self.attributes),
            "status": self.status,
        }


_thread_local = local()


def get_current_trace_id() -> str | None:
    """Get the current trace ID from context."""
    return getattr(_thread_local, "trace_id", None)


def get_current_span_id() -> str | None:
    """Get the current span ID from context."""
    return getattr(_thread_local, "span_id", None)


class TracingManager:
    """Manages trace and span lifecycle.

    Usage:
        tracer = TracingManager(config)
        with tracer.start_span("process_request") as span:
            span.set_attribute("http.method", "GET")
            # ... do work ...
    """

    def __init__(self, config: TracingConfig | None = None) -> None:
        self._config = config or TracingConfig()
        self._spans: list[_Span] = []
        self._exporters: list[Callable[[_Span], None]] = []

        if self._config.enabled:
            self._setup_exporters()

    def _setup_exporters(self) -> None:
        if self._config.exporter_type == TraceExporterType.CONSOLE:
            self._exporters.append(lambda span: print(f"[TRACE] {span.to_dict()}"))

    def add_exporter(self, exporter: Callable[[_Span], None]) -> None:
        """Register a custom span exporter."""
        self._exporters.append(exporter)

    def is_enabled(self) -> bool:
        return self._config.enabled

    @contextlib.contextmanager
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ):
        """Start a new span. If no active trace, creates a new trace."""
        if not self._config.enabled:
            yield _NoopSpan()
            return

        trace_id = get_current_trace_id() or uuid.uuid4().hex
        parent_span_id = get_current_span_id()

        span = _Span(name, trace_id, parent_span_id)
        span.start_time = __import__("time").time()
        if attributes:
            span.attributes.update(attributes)

        # Set context
        _thread_local.trace_id = trace_id
        _thread_local.span_id = span.span_id

        try:
            yield span
            span.status = "OK"
        except Exception as exc:
            span.status = "ERROR"
            span.status_description = str(exc)
            raise
        finally:
            span.end_time = __import__("time").time()
            self._spans.append(span)
            # Export
            for exporter in self._exporters:
                try:
                    exporter(span)
                except Exception:
                    pass
            # Restore parent context
            if parent_span_id:
                _thread_local.span_id = parent_span_id
            else:
                del _thread_local.trace_id
                del _thread_local.span_id

    def get_spans(self) -> list[dict[str, Any]]:
        """Get all recorded spans."""
        return [s.to_dict() for s in self._spans]

    def clear(self) -> None:
        """Clear all recorded spans."""
        self._spans.clear()


class _NoopSpan:
    """No-op span returned when tracing is disabled."""

    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: str, description: str = "") -> None:
        pass
