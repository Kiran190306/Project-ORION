"""Strongly typed configuration for observability components."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum


class ObservabilityConfigError(Exception):
    """Configuration validation error."""


class Environment(StrEnum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Configuration for structured logging."""

    level: str = "INFO"
    json_format: bool = True
    service_name: str = "orion"
    environment: str = "development"
    version: str = "0.0.0"
    enable_console: bool = True
    enable_file: bool = False
    file_path: str = "logs/orion.log"
    max_file_size_mb: int = 100
    backup_count: int = 5
    sensitive_fields: tuple[str, ...] = (
        "password",
        "secret",
        "token",
        "api_key",
        "private_key",
        "credit_card",
    )


@dataclass(frozen=True, slots=True)
class MetricsConfig:
    """Configuration for Prometheus metrics."""

    enabled: bool = True
    prefix: str = "orion"
    default_labels: dict[str, str] = field(default_factory=lambda: {"service": "orion"})
    buckets: tuple[float, ...] = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    )


@dataclass(frozen=True, slots=True)
class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    enabled: bool = False
    service_name: str = "orion"
    exporter_endpoint: str = "http://localhost:4317"
    exporter_type: str = "grpc"
    sampling_ratio: float = 0.1
    max_export_batch_size: int = 512
    scheduled_delay_millis: int = 5000
    export_timeout_millis: int = 30000


@dataclass(frozen=True, slots=True)
class HealthConfig:
    """Configuration for health checks."""

    enabled: bool = True
    liveness_path: str = "/health/live"
    readiness_path: str = "/health/ready"
    startup_path: str = "/health/startup"
    check_timeout_seconds: float = 5.0


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    """Top-level observability configuration."""

    environment: str = "development"
    service_name: str = "orion"
    version: str = "0.0.0"
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    health: HealthConfig = field(default_factory=HealthConfig)

    def __post_init__(self) -> None:
        valid_envs = {e.value for e in Environment}
        if self.environment not in valid_envs:
            raise ObservabilityConfigError(
                f"Invalid environment '{self.environment}'. Must be one of: {sorted(valid_envs)}"
            )
        if not self.service_name.strip():
            raise ObservabilityConfigError("service_name must not be empty")

    @classmethod
    def from_env(cls) -> ObservabilityConfig:
        """Load configuration from environment variables."""
        env = os.getenv("ORION_ENV", "development")
        service = os.getenv("ORION_SERVICE", "orion")
        version = os.getenv("ORION_VERSION", "0.0.0")
        log_level = os.getenv("ORION_LOG_LEVEL", "INFO")

        logging_cfg = LoggingConfig(
            level=log_level,
            service_name=service,
            environment=env,
            version=version,
        )

        return cls(
            environment=env,
            service_name=service,
            version=version,
            logging=logging_cfg,
        )
