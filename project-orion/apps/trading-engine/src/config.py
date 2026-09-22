"""Typed application settings for the Trading Engine.

All configuration is sourced from environment variables only.
No secrets are embedded in code.
Validation raises ConfigurationError on missing required values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal


class ConfigurationError(Exception):
    """Raised when required configuration is absent or invalid."""


@dataclass(frozen=True)
class AppSettings:
    """Strongly-typed application settings.

    Environment variables (all prefixed ``ORION_``):
        ORION_ENVIRONMENT       - runtime environment (default: development)
        ORION_LOG_LEVEL         - logging level (default: INFO)
        ORION_DATABASE_URL      - PostgreSQL URL (required)
        ORION_REDIS_URL         - Redis URL (default: redis://localhost:6379/0)
        ORION_RUN_MIGRATIONS    - run alembic upgrade on startup (default: false)
        ORION_SERVER_HOST       - bind host (default: 0.0.0.0)
        ORION_SERVER_PORT       - bind port (default: 8000)
        ORION_PAPER_BALANCE     - starting paper account balance (default: 100000)
    """

    environment: str
    log_level: str
    database_url: str
    redis_url: str
    run_migrations: bool
    server_host: str
    server_port: int
    paper_balance: Decimal
    # ─── Autonomous Worker ────────────────────────────────
    worker_enabled: bool
    worker_symbols: tuple[str, ...]
    market_data_poll_interval: float
    trading_cycle_interval: float
    worker_timeout: float
    worker_stale_threshold: float
    # ─── Market Data (EPIC-021) ───────────────────────────
    market_data_provider: str = "mock"
    market_data_api_key: str = ""
    market_data_base_url: str = "https://api.twelvedata.com"
    # ─── Authentication ───────────────────────────────────
    jwt_secret_key: str = "insecure-dev-secret-key-change-in-production-institutional-orion-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    )
    # ─── Rate Limiting & Abuse Defense (EPIC-027) ─────────
    rate_limiting_enabled: bool = True
    trusted_proxies: tuple[str, ...] = ("127.0.0.1", "::1")

    @classmethod
    def from_env(cls) -> AppSettings:
        """Load settings from environment variables.

        Raises:
            ConfigurationError: If a required variable is missing or invalid.
        """
        database_url = (
            os.environ.get("ORION_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
            or ""
        ).strip()
        if not database_url:
            raise ConfigurationError(
                "ORION_DATABASE_URL (or DATABASE_URL) is required but not set. "
                "Set it to a PostgreSQL URL such as "
                "postgresql+asyncpg://user:pass@host:5432/dbname"
            )

        # Normalize PostgreSQL URL schemes for asyncpg driver (Render / cloud providers)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://") and "+asyncpg" not in database_url and "+aiosqlite" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        log_level = os.environ.get("ORION_LOG_LEVEL", "INFO").upper()
        if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ConfigurationError(
                f"Invalid ORION_LOG_LEVEL '{log_level}'. "
                "Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )

        server_port_raw = (
            os.environ.get("ORION_SERVER_PORT")
            or os.environ.get("PORT")
            or "8000"
        )
        try:
            server_port = int(server_port_raw)
        except ValueError:
            raise ConfigurationError(
                f"ORION_SERVER_PORT must be an integer, got '{server_port_raw}'"
            )

        balance_raw = os.environ.get("ORION_PAPER_BALANCE", "100000")
        try:
            paper_balance = Decimal(balance_raw)
        except (ArithmeticError, ValueError):
            raise ConfigurationError(
                f"ORION_PAPER_BALANCE must be a number, got '{balance_raw}'"
            )

        run_migrations_raw = os.environ.get("ORION_RUN_MIGRATIONS", "false").lower()
        run_migrations = run_migrations_raw in ("true", "1", "yes")

        redis_url = (
            os.environ.get("ORION_REDIS_URL")
            or os.environ.get("REDIS_URL")
            or "redis://localhost:6379/0"
        )

        env_name = os.environ.get("ORION_ENVIRONMENT", "development").strip().lower()
        raw_jwt_secret = os.environ.get("ORION_JWT_SECRET_KEY", "").strip()
        default_insecure_secret = "insecure-dev-secret-key-change-in-production-institutional-orion-2026"

        if env_name == "production":
            if not raw_jwt_secret:
                raise ConfigurationError(
                    "ORION_JWT_SECRET_KEY is required in production environment but is not set."
                )
            if raw_jwt_secret == default_insecure_secret:
                raise ConfigurationError(
                    "ORION_JWT_SECRET_KEY cannot use the default development secret in production."
                )
            if len(raw_jwt_secret) < 32:
                raise ConfigurationError(
                    "ORION_JWT_SECRET_KEY must be at least 32 characters in production."
                )
            jwt_secret_key = raw_jwt_secret
        else:
            jwt_secret_key = raw_jwt_secret if raw_jwt_secret else default_insecure_secret

        return cls(
            environment=os.environ.get("ORION_ENVIRONMENT", "development"),
            log_level=log_level,
            database_url=database_url,
            redis_url=redis_url,
            run_migrations=run_migrations,
            server_host=os.environ.get("ORION_SERVER_HOST", "0.0.0.0"),
            server_port=server_port,
            paper_balance=paper_balance,
            # ─── Autonomous Worker ─────────────────────────────
            worker_enabled=os.environ.get("ORION_WORKER_ENABLED", "false").lower()
            in ("true", "1", "yes"),
            worker_symbols=_parse_symbols(
                os.environ.get("ORION_WORKER_SYMBOLS", "EUR/USD,GBP/USD,USD/JPY")
            ),
            market_data_poll_interval=_parse_positive_float(
                os.environ.get("ORION_MARKET_DATA_POLL_INTERVAL", "5.0"),
                "ORION_MARKET_DATA_POLL_INTERVAL",
            ),
            trading_cycle_interval=_parse_positive_float(
                os.environ.get("ORION_TRADING_CYCLE_INTERVAL", "10.0"),
                "ORION_TRADING_CYCLE_INTERVAL",
            ),
            worker_timeout=_parse_positive_float(
                os.environ.get("ORION_WORKER_TIMEOUT", "30.0"),
                "ORION_WORKER_TIMEOUT",
            ),
            worker_stale_threshold=_parse_positive_float(
                os.environ.get("ORION_WORKER_STALE_THRESHOLD", "30.0"),
                "ORION_WORKER_STALE_THRESHOLD",
            ),
            # ─── Market Data (EPIC-021) ───────────────────────
            market_data_provider=os.environ.get("ORION_MARKET_DATA_PROVIDER", "mock").strip().lower(),
            market_data_api_key=os.environ.get("ORION_MARKET_DATA_API_KEY", "").strip(),
            market_data_base_url=os.environ.get("ORION_MARKET_DATA_BASE_URL", "https://api.twelvedata.com").strip(),
            jwt_secret_key=jwt_secret_key,
            jwt_algorithm=os.environ.get("ORION_JWT_ALGORITHM", "HS256"),
            jwt_expire_minutes=int(os.environ.get("ORION_JWT_EXPIRE_MINUTES", "30")),
            cors_origins=_parse_cors_origins(
                os.environ.get(
                    "ORION_CORS_ORIGINS",
                    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
                )
            ),
            rate_limiting_enabled=os.environ.get(
                "ORION_RATE_LIMITING_ENABLED", "true"
            ).lower()
            in ("true", "1", "yes"),
            trusted_proxies=tuple(
                p.strip()
                for p in os.environ.get("ORION_TRUSTED_PROXIES", "127.0.0.1,::1").split(",")
                if p.strip()
            ),
        )

    @property
    def is_development(self) -> bool:
        """Return True if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.environment.lower() == "production"


# ─── Private helpers ──────────────────────────────────────────────────────────


def _parse_positive_float(raw: str, var_name: str) -> float:
    """Parse ``raw`` as a positive float; raise ConfigurationError on failure."""
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError(
            f"{var_name} must be a positive number, got '{raw}'"
        )
    if value <= 0:
        raise ConfigurationError(
            f"{var_name} must be > 0, got {value!r}"
        )
    return value


def _parse_symbols(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated list of symbols into a deduplicated tuple."""
    items = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not items:
        raise ConfigurationError(
            "ORION_WORKER_SYMBOLS must contain at least one symbol, e.g. 'EUR/USD,GBP/USD'"
        )
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for sym in items:
        if sym not in seen:
            seen.add(sym)
            unique.append(sym)
    return tuple(unique)


def parse_cors_origins(raw: str) -> tuple[str, ...]:
    """Parse comma-separated list of CORS origins."""
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return (
        tuple(origins)
        if origins
        else (
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        )
    )


_parse_cors_origins = parse_cors_origins

