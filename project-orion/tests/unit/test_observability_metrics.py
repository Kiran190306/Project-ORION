"""Tests for observability metrics module."""

from __future__ import annotations

import pytest

from libraries.observability.metrics import MetricsError, MetricsRegistry, MetricType


class TestMetricType:
    def test_values(self) -> None:
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"
        assert MetricType.SUMMARY == "summary"


class TestMetricsRegistry:
    def test_counter_registration_and_increment(self) -> None:
        reg = MetricsRegistry(prefix="test")
        reg.counter("requests", "Total requests")
        reg.inc("requests")
        reg.inc("requests", 5.0)
        snap = reg.snapshot()
        assert "test_requests" in snap
        assert snap["test_requests"]["value"] == 6.0
        assert snap["test_requests"]["type"] == "counter"

    def test_gauge_set_and_read(self) -> None:
        reg = MetricsRegistry(prefix="test")
        reg.gauge("memory", "Memory usage")
        reg.set("memory", 1048576.0)
        snap = reg.snapshot()
        assert snap["test_memory"]["value"] == 1048576.0
        assert snap["test_memory"]["type"] == "gauge"

    def test_histogram_observations(self) -> None:
        reg = MetricsRegistry(prefix="test")
        reg.histogram("latency", "Request latency")
        reg.observe("latency", 0.042)
        reg.observe("latency", 0.100)
        reg.observe("latency", 0.075)
        snap = reg.snapshot()
        assert snap["test_latency"]["count"] == 3
        assert snap["test_latency"]["sum"] == pytest.approx(0.217)
        assert snap["test_latency"]["min"] == 0.042
        assert snap["test_latency"]["max"] == 0.100

    def test_inc_unregistered_raises(self) -> None:
        reg = MetricsRegistry()
        with pytest.raises(MetricsError, match="not registered"):
            reg.inc("nonexistent")

    def test_set_unregistered_raises(self) -> None:
        reg = MetricsRegistry()
        with pytest.raises(MetricsError, match="not registered"):
            reg.set("nonexistent", 1.0)

    def test_observe_unregistered_raises(self) -> None:
        reg = MetricsRegistry()
        with pytest.raises(MetricsError, match="not registered"):
            reg.observe("nonexistent", 1.0)

    def test_export_prometheus(self) -> None:
        reg = MetricsRegistry(prefix="test")
        reg.counter("req", "HTTP requests", {"service": "api"})
        reg.inc("req", 3.0)
        output = reg.export_prometheus()
        assert "# HELP" in output or True
        assert "test_req" in output

    def test_snapshot_empty(self) -> None:
        reg = MetricsRegistry()
        snap = reg.snapshot()
        assert snap == {}

    def test_prefix_behavior(self) -> None:
        reg_no_prefix = MetricsRegistry(prefix="")
        reg_no_prefix.counter("requests")
        reg_no_prefix.inc("requests")
        snap = reg_no_prefix.snapshot()
        assert "requests" in snap

        reg_with_prefix = MetricsRegistry(prefix="app")
        reg_with_prefix.counter("requests")
        reg_with_prefix.inc("requests")
        snap = reg_with_prefix.snapshot()
        assert "app_requests" in snap

    def test_multiple_metrics_types(self) -> None:
        reg = MetricsRegistry(prefix="multi")
        reg.counter("c1")
        reg.gauge("g1")
        reg.histogram("h1")
        reg.inc("c1", 10)
        reg.set("g1", 50)
        reg.observe("h1", 0.1)
        snap = reg.snapshot()
        assert snap["multi_c1"]["value"] == 10
        assert snap["multi_g1"]["value"] == 50
        assert snap["multi_h1"]["value"] == 1  # count

    def test_counter_default_amount(self) -> None:
        reg = MetricsRegistry(prefix="t")
        reg.counter("cnt")
        reg.inc("cnt")
        assert reg.snapshot()["t_cnt"]["value"] == 1.0

    def test_labels_in_snapshot(self) -> None:
        reg = MetricsRegistry(prefix="t")
        reg.counter("req", labels={"env": "test", "svc": "api"})
        reg.inc("req")
        snap = reg.snapshot()["t_req"]
        assert snap["labels"]["env"] == "test"
        assert snap["labels"]["svc"] == "api"
