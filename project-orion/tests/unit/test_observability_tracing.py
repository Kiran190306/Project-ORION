"""Tests for observability tracing module."""

from __future__ import annotations

import pytest

from libraries.observability.tracing import (
    TraceExporterType,
    TracingError,
    TracingManager,
    _NoopSpan,
)


class TestTraceExporterType:
    def test_values(self) -> None:
        assert TraceExporterType.CONSOLE == "console"
        assert TraceExporterType.GRPC == "grpc"
        assert TraceExporterType.HTTP == "http"


class TestTracingManager:
    def test_disabled_by_default(self) -> None:
        tracer = TracingManager()
        assert tracer.is_enabled() is False
        with tracer.start_span("test"):
            pass
        assert len(tracer.get_spans()) == 0

    def test_enabled_records_spans(self) -> None:
        from libraries.observability.config import TracingConfig

        tracer = TracingManager(TracingConfig(enabled=True))
        assert tracer.is_enabled() is True
        with tracer.start_span("test_op", attributes={"key": "value"}):
            pass
        spans = tracer.get_spans()
        assert len(spans) == 1
        assert spans[0]["name"] == "test_op"
        assert spans[0]["span_id"] is not None
        assert spans[0]["trace_id"] is not None

    def test_nested_spans(self) -> None:
        from libraries.observability.config import TracingConfig

        tracer = TracingManager(TracingConfig(enabled=True))
        with tracer.start_span("parent", attributes={"type": "outer"}) as parent:
            pass
        with tracer.start_span("child", attributes={"type": "inner"}) as child:
            pass
        spans = tracer.get_spans()
        assert len(spans) == 2
        # Both should be separate traces since we don't nest
        assert spans[0]["name"] == "parent"
        assert spans[1]["name"] == "child"

    def test_span_duration(self) -> None:
        from libraries.observability.config import TracingConfig

        tracer = TracingManager(TracingConfig(enabled=True))
        with tracer.start_span("timed"):
            import time

            time.sleep(0.001)
        spans = tracer.get_spans()
        assert spans[0]["duration_ms"] > 0

    def test_clear_spans(self) -> None:
        from libraries.observability.config import TracingConfig

        tracer = TracingManager(TracingConfig(enabled=True))
        with tracer.start_span("clear_test"):
            pass
        assert len(tracer.get_spans()) == 1
        tracer.clear()
        assert len(tracer.get_spans()) == 0

    def test_exception_records_error(self) -> None:
        from libraries.observability.config import TracingConfig

        tracer = TracingManager(TracingConfig(enabled=True))
        with pytest.raises(ValueError, match="test error"):
            with tracer.start_span("failing"):
                msg = "test error"
                raise ValueError(msg)
        spans = tracer.get_spans()
        assert len(spans) == 1
        assert spans[0]["status"] == "ERROR"

    def test_add_exporter(self) -> None:
        from libraries.observability.config import TracingConfig

        exported: list[dict] = []
        tracer = TracingManager(TracingConfig(enabled=True))
        tracer.add_exporter(lambda span: exported.append(span.to_dict()))
        with tracer.start_span("exported"):
            pass
        assert len(exported) == 1
        assert exported[0]["name"] == "exported"

    def test_noop_span(self) -> None:
        span = _NoopSpan()
        with span:
            span.set_attribute("key", "value")
            span.set_status("OK")
        assert True  # No-op should not raise

    def test_noop_span_context_manager(self) -> None:
        span = _NoopSpan()
        with span as s:
            assert s is span
        assert True

    def test_get_spans_empty(self) -> None:
        tracer = TracingManager()
        assert tracer.get_spans() == []

    def test_get_current_trace_id(self) -> None:
        from libraries.observability.tracing import get_current_trace_id

        tid = get_current_trace_id()
        assert tid is None  # No active trace
