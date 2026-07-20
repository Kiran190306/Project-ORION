"""Tests for metrics collectors."""

from __future__ import annotations

from libraries.infrastructure.broker_connectors.metrics import (
    MetricSample,
    MetricsCollector,
    NullMetricsCollector,
    RecordingMetricsCollector,
)


def test_recording_metrics_collector_increment() -> None:
    collector = RecordingMetricsCollector()
    collector.increment("test.counter", tags={"env": "test"})
    assert len(collector.samples) == 1
    sample = collector.samples[0]
    assert sample.kind == "increment"
    assert sample.name == "test.counter"
    assert sample.value == 1
    assert sample.tags == {"env": "test"}


def test_recording_metrics_collector_gauge() -> None:
    collector = RecordingMetricsCollector()
    collector.gauge("test.gauge", 42.5, tags={"env": "test"})
    assert len(collector.samples) == 1
    sample = collector.samples[0]
    assert sample.kind == "gauge"
    assert sample.name == "test.gauge"
    assert sample.value == 42.5
    assert sample.tags == {"env": "test"}


def test_recording_metrics_collector_timing() -> None:
    collector = RecordingMetricsCollector()
    collector.timing("test.latency", 123.45, tags={"env": "test"})
    assert len(collector.samples) == 1
    sample = collector.samples[0]
    assert sample.kind == "timing"
    assert sample.name == "test.latency"
    assert sample.value == 123.45
    assert sample.tags == {"env": "test"}


def test_recording_metrics_multiple_samples() -> None:
    collector = RecordingMetricsCollector()
    collector.increment("a")
    collector.increment("b")
    collector.gauge("c", 1.0)
    assert len(collector.samples) == 3


def test_recording_metrics_no_tags() -> None:
    collector = RecordingMetricsCollector()
    collector.increment("plain")
    assert collector.samples[0].tags is None


def test_null_metrics_collector_noop() -> None:
    collector = NullMetricsCollector()
    # Should not raise
    collector.increment("test", tags={"env": "test"})
    collector.gauge("test", 1.0, tags={"env": "test"})
    collector.timing("test", 100.0, tags={"env": "test"})


def test_null_metrics_collector_returns_none() -> None:
    collector = NullMetricsCollector()
    assert collector.increment("test") is None
    assert collector.gauge("test", 1.0) is None
    assert collector.timing("test", 100.0) is None


def test_metric_sample_dataclass() -> None:
    sample = MetricSample(kind="increment", name="test", value=1, tags={"env": "test"})
    assert sample.kind == "increment"
    assert sample.name == "test"
    assert sample.value == 1
    assert sample.tags == {"env": "test"}


def test_metrics_collector_base_raises_not_implemented() -> None:
    """Base MetricsCollector should raise NotImplementedError."""
    base = MetricsCollector()
    try:
        base.increment("test")
        assert False, "Should have raised"
    except NotImplementedError:
        pass
    try:
        base.gauge("test", 1.0)
        assert False, "Should have raised"
    except NotImplementedError:
        pass
    try:
        base.timing("test", 1.0)
        assert False, "Should have raised"
    except NotImplementedError:
        pass
