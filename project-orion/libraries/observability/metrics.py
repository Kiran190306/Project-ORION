"""Prometheus metrics registry for ORION services.

Provides counters, gauges, histograms, and summaries for
monitoring application performance and business metrics.
"""

from __future__ import annotations

import time
from enum import StrEnum
from threading import Lock
from typing import Any, Callable


class MetricsError(Exception):
    """Metrics operation error."""


class MetricType(StrEnum):
    """Supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class _Metric:
    """Internal metric storage."""

    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        description: str,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.type = metric_type
        self.description = description
        self.labels = labels or {}
        self._value: float = 0.0
        self._lock = Lock()
        self._observations: list[float] = []

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def observe(self, value: float) -> None:
        with self._lock:
            self._observations.append(value)
            self._value += 1  # count

    @property
    def value(self) -> float:
        return self._value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            result: dict[str, Any] = {
                "name": self.name,
                "type": self.type.value,
                "description": self.description,
                "labels": dict(self.labels),
                "value": self._value,
            }
            if self._observations:
                obs = list(self._observations)
                result.update(
                    {
                        "count": len(obs),
                        "sum": sum(obs),
                        "min": min(obs),
                        "max": max(obs),
                        "avg": sum(obs) / len(obs) if obs else 0.0,
                    }
                )
            return result


class MetricsRegistry:
    """Thread-safe registry for all application metrics.

    Usage:
        registry = MetricsRegistry()
        registry.counter("requests_total", "Total HTTP requests")
        registry.gauge("memory_bytes", "Current memory usage")
        registry.histogram("request_duration_seconds", "Request duration")
        registry.inc("requests_total")
        registry.set("memory_bytes", 1048576)
        registry.observe("request_duration_seconds", 0.042)
    """

    def __init__(self, prefix: str = "orion") -> None:
        self._prefix = prefix
        self._metrics: dict[str, _Metric] = {}
        self._lock = Lock()

    def _full_name(self, name: str) -> str:
        return f"{self._prefix}_{name}" if self._prefix else name

    def counter(
        self, name: str, description: str = "", labels: dict[str, str] | None = None
    ) -> None:
        """Register a counter metric."""
        full = self._full_name(name)
        with self._lock:
            if full not in self._metrics:
                self._metrics[full] = _Metric(full, MetricType.COUNTER, description, labels)

    def gauge(self, name: str, description: str = "", labels: dict[str, str] | None = None) -> None:
        """Register a gauge metric."""
        full = self._full_name(name)
        with self._lock:
            if full not in self._metrics:
                self._metrics[full] = _Metric(full, MetricType.GAUGE, description, labels)

    def histogram(
        self, name: str, description: str = "", labels: dict[str, str] | None = None
    ) -> None:
        """Register a histogram metric."""
        full = self._full_name(name)
        with self._lock:
            if full not in self._metrics:
                self._metrics[full] = _Metric(full, MetricType.HISTOGRAM, description, labels)

    def inc(self, name: str, amount: float = 1.0) -> None:
        """Increment a counter metric."""
        full = self._full_name(name)
        metric = self._get(full)
        if metric is None:
            raise MetricsError(f"Counter '{full}' not registered")
        metric.inc(amount)

    def set(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        full = self._full_name(name)
        metric = self._get(full)
        if metric is None:
            raise MetricsError(f"Gauge '{full}' not registered")
        metric.set(value)

    def observe(self, name: str, value: float) -> None:
        """Record an observation for a histogram metric."""
        full = self._full_name(name)
        metric = self._get(full)
        if metric is None:
            raise MetricsError(f"Histogram '{full}' not registered")
        metric.observe(value)

    def _get(self, name: str) -> _Metric | None:
        with self._lock:
            return self._metrics.get(name)

    def snapshot(self) -> dict[str, Any]:
        """Snapshot all metrics and their current values."""
        with self._lock:
            return {name: metric.snapshot() for name, metric in sorted(self._metrics.items())}

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            for name, metric in sorted(self._metrics.items()):
                help_line = f"# HELP {name} {metric.description}" if metric.description else ""
                type_line = f"# TYPE {name} {metric.type.value}"
                lines.append(help_line)
                lines.append(type_line)
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(metric.labels.items()))
                metric_line = (
                    f"{name}{{{label_str}}} {metric.value}"
                    if label_str
                    else f"{name} {metric.value}"
                )
                lines.append(metric_line)
        return "\n".join(lines) + "\n"
