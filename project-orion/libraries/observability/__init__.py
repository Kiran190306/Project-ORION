"""Enterprise Observability Foundation for Project ORION.

Provides production-grade logging, metrics, tracing, health checks,
diagnostics, and middleware for all ORION services.

Usage:
    from libraries.observability import (
        configure_logging,
        get_logger,
        MetricsRegistry,
        ObservabilityMiddleware,
        HealthRegistry,
        DiagnosticsService,
        ObservabilityConfig,
    )
"""

from __future__ import annotations

from libraries.observability.config import (
    Environment,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    ObservabilityConfigError,
    TracingConfig,
)
from libraries.observability.diagnostics import DiagnosticsService, SystemInfo
from libraries.observability.health import HealthCheckResult, HealthRegistry, HealthStatus
from libraries.observability.integration import (
    ServiceObserver,
    configure_observability,
    observe_service,
)
from libraries.observability.logging import (
    StructuredFormatter,
    StructuredLogger,
    configure_logging,
    get_correlation_id,
    get_logger,
    set_correlation_id,
)
from libraries.observability.metrics import MetricsError, MetricsRegistry, MetricType
from libraries.observability.middleware import (
    CorrelationIdMiddleware,
    ObservabilityMiddleware,
    RequestMetricsMiddleware,
)
from libraries.observability.tracing import (
    TraceExporterType,
    TracingError,
    TracingManager,
    _NoopSpan,
)

__all__ = [
    # Config
    "ObservabilityConfig",
    "ObservabilityConfigError",
    "Environment",
    "LoggingConfig",
    "MetricsConfig",
    "TracingConfig",
    "HealthConfig",
    # Logging
    "StructuredLogger",
    "StructuredFormatter",
    "configure_logging",
    "get_logger",
    "set_correlation_id",
    "get_correlation_id",
    # Metrics
    "MetricsRegistry",
    "MetricType",
    "MetricsError",
    # Tracing
    "TracingManager",
    "TracingError",
    "TraceExporterType",
    "_NoopSpan",
    # Health
    "HealthRegistry",
    "HealthStatus",
    "HealthCheckResult",
    # Diagnostics
    "DiagnosticsService",
    "SystemInfo",
    # Middleware
    "ObservabilityMiddleware",
    "CorrelationIdMiddleware",
    "RequestMetricsMiddleware",
]

__version__ = "0.12.0-alpha.1"
