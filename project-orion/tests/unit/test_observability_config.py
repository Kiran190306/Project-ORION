"""Tests for observability configuration module."""

from __future__ import annotations

import pytest

from libraries.observability.config import (
    Environment,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    ObservabilityConfig,
    ObservabilityConfigError,
    TracingConfig,
)


class TestEnvironment:
    def test_values(self) -> None:
        assert Environment.DEVELOPMENT == "development"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"


class TestLoggingConfig:
    def test_defaults(self) -> None:
        cfg = LoggingConfig()
        assert cfg.level == "INFO"
        assert cfg.json_format is True
        assert cfg.service_name == "orion"
        assert cfg.enable_console is True
        assert cfg.enable_file is False

    def test_sensitive_fields(self) -> None:
        cfg = LoggingConfig()
        assert "password" in cfg.sensitive_fields
        assert "api_key" in cfg.sensitive_fields
        assert "credit_card" in cfg.sensitive_fields

    def test_is_frozen(self) -> None:
        cfg = LoggingConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.level = "DEBUG"  # type: ignore[misc]


class TestMetricsConfig:
    def test_defaults(self) -> None:
        cfg = MetricsConfig()
        assert cfg.enabled is True
        assert cfg.prefix == "orion"

    def test_buckets(self) -> None:
        cfg = MetricsConfig()
        assert len(cfg.buckets) > 0
        assert cfg.buckets[0] == 0.005
        assert cfg.buckets[-1] == 10.0

    def test_default_labels(self) -> None:
        cfg = MetricsConfig()
        assert cfg.default_labels["service"] == "orion"


class TestTracingConfig:
    def test_defaults(self) -> None:
        cfg = TracingConfig()
        assert cfg.enabled is False
        assert cfg.service_name == "orion"
        assert cfg.sampling_ratio == 0.1

    def test_exporter_defaults(self) -> None:
        cfg = TracingConfig()
        assert cfg.exporter_type == "grpc"
        assert cfg.max_export_batch_size == 512
        assert cfg.scheduled_delay_millis == 5000


class TestHealthConfig:
    def test_defaults(self) -> None:
        cfg = HealthConfig()
        assert cfg.enabled is True
        assert cfg.liveness_path == "/health/live"
        assert cfg.readiness_path == "/health/ready"
        assert cfg.check_timeout_seconds == 5.0


class TestObservabilityConfig:
    def test_defaults(self) -> None:
        cfg = ObservabilityConfig()
        assert cfg.environment == "development"
        assert cfg.service_name == "orion"
        assert cfg.version == "0.0.0"
        assert isinstance(cfg.logging, LoggingConfig)
        assert isinstance(cfg.metrics, MetricsConfig)
        assert isinstance(cfg.tracing, TracingConfig)
        assert isinstance(cfg.health, HealthConfig)

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(ObservabilityConfigError, match="Invalid environment"):
            ObservabilityConfig(environment="invalid")

    def test_empty_service_name_raises(self) -> None:
        with pytest.raises(ObservabilityConfigError, match="service_name must not be empty"):
            ObservabilityConfig(service_name="")

    def test_valid_environments(self) -> None:
        for env in ("development", "testing", "staging", "production"):
            cfg = ObservabilityConfig(environment=env)
            assert cfg.environment == env

    def test_from_env(self) -> None:
        cfg = ObservabilityConfig.from_env()
        assert cfg.service_name == "orion"
        assert isinstance(cfg.logging, LoggingConfig)

    def test_is_frozen(self) -> None:
        cfg = ObservabilityConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.environment = "production"  # type: ignore[misc]
