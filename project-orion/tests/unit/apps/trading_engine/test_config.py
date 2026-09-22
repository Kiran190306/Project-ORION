"""Unit tests for Trading Engine application settings and configuration."""

from __future__ import annotations

import os
from decimal import Decimal
from unittest import mock

import pytest
from apps.trading_engine.src.config import AppSettings, ConfigurationError


def test_config_from_env_defaults() -> None:
    """Test loading settings with only required DATABASE_URL set."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/trading_db",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        settings = AppSettings.from_env()

        assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/trading_db"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.run_migrations is False
        assert settings.server_host == "0.0.0.0"
        assert settings.server_port == 8000
        assert settings.paper_balance == Decimal(100000)
        assert settings.is_development is True
        assert settings.is_production is False


def test_config_from_env_custom_values() -> None:
    """Test loading custom configuration values from environment."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://prod_user:secret@prod-db:5432/orion_prod",
        "ORION_ENVIRONMENT": "production",
        "ORION_JWT_SECRET_KEY": "production-jwt-secret-key-must-be-at-least-32-chars-long",
        "ORION_LOG_LEVEL": "WARNING",
        "ORION_REDIS_URL": "redis://redis-cluster:6379/2",
        "ORION_RUN_MIGRATIONS": "true",
        "ORION_SERVER_HOST": "127.0.0.1",
        "ORION_SERVER_PORT": "9000",
        "ORION_PAPER_BALANCE": "250000.50",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        settings = AppSettings.from_env()

        assert settings.database_url == "postgresql+asyncpg://prod_user:secret@prod-db:5432/orion_prod"
        assert settings.environment == "production"
        assert settings.log_level == "WARNING"
        assert settings.redis_url == "redis://redis-cluster:6379/2"
        assert settings.run_migrations is True
        assert settings.server_host == "127.0.0.1"
        assert settings.server_port == 9000
        assert settings.paper_balance == Decimal("250000.50")
        assert settings.is_development is False
        assert settings.is_production is True


def test_config_missing_database_url_raises() -> None:
    """Test that missing ORION_DATABASE_URL raises ConfigurationError."""
    with (
        mock.patch.dict(os.environ, {}, clear=True),
        pytest.raises(ConfigurationError, match="ORION_DATABASE_URL.*required"),
    ):
        AppSettings.from_env()


def test_config_postgres_url_scheme_normalization() -> None:
    """Test normalization of legacy postgres:// scheme to postgresql+asyncpg://."""
    env = {
        "ORION_DATABASE_URL": "postgres://render_user:pass@render-db:5432/orion",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        settings = AppSettings.from_env()
        assert settings.database_url == "postgresql+asyncpg://render_user:pass@render-db:5432/orion"


def test_config_invalid_log_level_raises() -> None:
    """Test that an invalid log level raises ConfigurationError."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_LOG_LEVEL": "INVALID_LEVEL",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="Invalid ORION_LOG_LEVEL"),
    ):
        AppSettings.from_env()


def test_config_invalid_server_port_raises() -> None:
    """Test that a non-integer server port raises ConfigurationError."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_SERVER_PORT": "not-a-number",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="ORION_SERVER_PORT must be an integer"),
    ):
        AppSettings.from_env()


def test_config_invalid_paper_balance_raises() -> None:
    """Test that a non-numeric balance raises ConfigurationError."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_PAPER_BALANCE": "invalid-decimal",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="ORION_PAPER_BALANCE must be a number"),
    ):
        AppSettings.from_env()


def test_config_cloud_environment_fallbacks() -> None:
    """Test fallback lookups for DATABASE_URL, PORT, and REDIS_URL from cloud platforms."""
    env = {
        "DATABASE_URL": "postgres://render_pg:pass@render-db:5432/prod",
        "PORT": "8080",
        "REDIS_URL": "redis://render-redis:6379/1",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        settings = AppSettings.from_env()
        assert settings.database_url == "postgresql+asyncpg://render_pg:pass@render-db:5432/prod"
        assert settings.server_port == 8080
        assert settings.redis_url == "redis://render-redis:6379/1"


def test_config_production_missing_jwt_secret_fails_closed() -> None:
    """Test that missing ORION_JWT_SECRET_KEY in production fails closed."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "production",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="ORION_JWT_SECRET_KEY is required in production"),
    ):
        AppSettings.from_env()


def test_config_production_default_insecure_jwt_secret_fails_closed() -> None:
    """Test that using default insecure JWT secret in production fails closed."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "production",
        "ORION_JWT_SECRET_KEY": "insecure-dev-secret-key-change-in-production-institutional-orion-2026",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="cannot use the default development secret in production"),
    ):
        AppSettings.from_env()


def test_config_production_short_jwt_secret_fails_closed() -> None:
    """Test that short JWT secret (<32 chars) in production fails closed."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "production",
        "ORION_JWT_SECRET_KEY": "too-short",
    }
    with (
        mock.patch.dict(os.environ, env, clear=True),
        pytest.raises(ConfigurationError, match="must be at least 32 characters in production"),
    ):
        AppSettings.from_env()


def test_config_production_valid_jwt_secret_succeeds() -> None:
    """Test that valid 32+ char secret in production succeeds."""
    env = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "production",
        "ORION_JWT_SECRET_KEY": "a-strong-production-secret-with-32-plus-characters-institutional!",
    }
    with mock.patch.dict(os.environ, env, clear=True):
        settings = AppSettings.from_env()
        assert settings.is_production is True
        assert settings.jwt_secret_key == "a-strong-production-secret-with-32-plus-characters-institutional!"


def test_config_development_uses_default_or_custom_jwt_secret() -> None:
    """Test that development environment can use default secret or custom test secret."""
    # 1. Default secret in dev
    env_default = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "development",
    }
    with mock.patch.dict(os.environ, env_default, clear=True):
        settings = AppSettings.from_env()
        assert settings.is_development is True
        assert "institutional-orion-2026" in settings.jwt_secret_key

    # 2. Custom secret in test/dev
    env_custom = {
        "ORION_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "ORION_ENVIRONMENT": "test",
        "ORION_JWT_SECRET_KEY": "explicit-test-secret",
    }
    with mock.patch.dict(os.environ, env_custom, clear=True):
        settings_custom = AppSettings.from_env()
        assert settings_custom.jwt_secret_key == "explicit-test-secret"
