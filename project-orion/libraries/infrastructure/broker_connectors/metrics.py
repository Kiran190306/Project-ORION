"""Metrics abstractions for connector layer.

Production readiness requires a metrics sink interface; tests can use a
recording collector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


class MetricsCollector:
    """Simple metrics collector interface (sync by design)."""

    def increment(
        self, metric: str, tags: dict[str, str] | None = None
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    def gauge(
        self, metric: str, value: float, tags: dict[str, str] | None = None
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    def timing(
        self, metric: str, duration_ms: float, tags: dict[str, str] | None = None
    ) -> None:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class MetricSample:
    kind: str
    name: str
    value: float | int | None
    tags: Optional[dict[str, str]]


class RecordingMetricsCollector(MetricsCollector):
    """In-memory metrics sink for unit tests."""

    def __init__(self) -> None:
        self.samples: list[MetricSample] = []

    def increment(self, metric: str, tags: dict[str, str] | None = None) -> None:
        self.samples.append(MetricSample(kind="increment", name=metric, value=1, tags=tags))

    def gauge(
        self,
        metric: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:  # type: ignore[override]
        self.samples.append(MetricSample(kind="gauge", name=metric, value=value, tags=tags))

    def timing(self, metric: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        self.samples.append(MetricSample(kind="timing", name=metric, value=duration_ms, tags=tags))


class NullMetricsCollector(MetricsCollector):
    """No-op metrics sink."""

    def increment(self, metric: str, tags: dict[str, str] | None = None) -> None:
        return None

    def gauge(self, metric: str, value: float, tags: dict[str, str] | None = None) -> None:
        return None

    def timing(self, metric: str, duration_ms: float, tags: dict[str, str] | None = None) -> None:
        return None
