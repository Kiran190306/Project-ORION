"""Application lifespan management for FastAPI.

Handles startup, dependency wiring, optional Alembic migrations,
health check registration, and graceful shutdown in reverse order.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from libraries.domain.market_data.models import ProviderStatus
from libraries.domain.market_data.quality_engine import MarketDataQualityEngine
from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.caching.config import RedisConfig
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.health import (
    HealthCheck,
    HealthCheckRegistry,
    HealthCheckResult,
    HealthStatus,
)
from libraries.infrastructure.market_data.cache import MarketDataCache
from libraries.infrastructure.market_data.factory import create_market_data_provider
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.infrastructure.security.ip_resolver import ClientIpResolver
from libraries.infrastructure.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
)
from libraries.observability.config import LoggingConfig
from libraries.observability.logging import configure_logging
from libraries.observability.metrics import MetricsRegistry

from .config import AppSettings
from .services.market_data_service import MarketDataService
from .services.rate_limit_service import RateLimitService
from .workers.coordinator import AutonomousWorkerCoordinator

logger = logging.getLogger("trading_engine.lifespan")


# ─── Health Checks ──────────────────────────────────────────────────────────


class DatabaseHealthCheck(HealthCheck):
    """Health check for PostgreSQL database connectivity."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        super().__init__(name="database", timeout_seconds=5.0)
        self._db_manager = db_manager

    async def check(self) -> HealthCheckResult:
        """Run SELECT 1 health check via DatabaseManager."""
        try:
            is_healthy = await self._db_manager.health_check()
            if is_healthy:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Database connection verified",
                )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Database health query failed",
            )
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection error: {exc}",
            )


class RedisHealthCheck(HealthCheck):
    """Health check for Redis connectivity."""

    def __init__(self, redis_client: RedisClient) -> None:
        super().__init__(name="redis", timeout_seconds=5.0)
        self._redis_client = redis_client

    async def check(self) -> HealthCheckResult:
        """Ping Redis via RedisClient."""
        try:
            if not self._redis_client.is_connected:
                await self._redis_client.connect()
            is_healthy = await self._redis_client.health_check()
            if is_healthy:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message="Redis connection verified",
                )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message="Redis ping check returned false",
            )
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis connection error: {exc}",
            )


class MarketDataHealthCheck(HealthCheck):
    """Health check for Market Data provider connectivity."""

    def __init__(self, market_service: MarketDataService) -> None:
        super().__init__(name="market_data", timeout_seconds=5.0)
        self._market_service = market_service

    async def check(self) -> HealthCheckResult:
        """Probe market data provider health."""
        try:
            health = await self._market_service.get_health()
            if health.status == ProviderStatus.HEALTHY:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.HEALTHY,
                    message=f"Market data provider '{health.provider}' healthy (latency={health.latency_ms:.1f}ms)",
                )
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.DEGRADED,
                message=f"Market data provider status '{health.status.value}'",
            )
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Market data health check failed: {exc}",
            )



# ─── Alembic Migration Hook ────────────────────────────────────────────────


def run_database_migrations(database_url: str) -> None:
    """Execute Alembic upgrade head synchronously if configured."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    logger.info("Running database migrations (Alembic upgrade head)...")
    # Resolve alembic.ini from project root
    current_file = Path(__file__).resolve()
    # Path is apps/trading-engine/src/lifespan.py -> parents[3] is project root
    project_root = current_file.parents[3]
    ini_path = project_root / "alembic.ini"
    if not ini_path.exists():
        # Fallback to local working directory
        ini_path = Path("alembic.ini").resolve()

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed successfully.")


# ─── Lifespan Context Manager ───────────────────────────────────────────────


def create_lifespan(
    settings_override: AppSettings | None = None,
    db_manager_override: DatabaseManager | None = None,
    redis_client_override: RedisClient | None = None,
    paper_adapter_override: PaperExecutionAdapter | None = None,
    worker_override: AutonomousWorkerCoordinator | None = None,
    market_data_service_override: MarketDataService | None = None,
    rate_limit_service_override: RateLimitService | None = None,
) -> Any:
    """Create a FastAPI lifespan context manager with optional overrides for testing."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # 1. Load configuration
        settings = settings_override or AppSettings.from_env()
        app.state.settings = settings

        # 2. Configure structured logging
        log_config = LoggingConfig(
            level=settings.log_level,
            service_name="trading-engine",
            environment=settings.environment,
        )
        configure_logging(log_config)
        logger.info(
            "Starting Trading Engine runtime (environment=%s, log_level=%s)",
            settings.environment,
            settings.log_level,
        )

        # 3. Initialize Database
        db_config = DatabaseConfig(url=settings.database_url)
        db_manager = db_manager_override or DatabaseManager(config=db_config)
        app.state.db_manager = db_manager

        # 4. Optional Alembic migrations
        if settings.run_migrations:
            try:
                import anyio

                await anyio.to_thread.run_sync(
                    run_database_migrations, settings.database_url
                )
            except Exception as exc:
                logger.error("Failed to execute database migrations: %s", exc)
                raise

        # 5. Initialize Redis
        redis_config = RedisConfig(url=settings.redis_url)
        redis_client = redis_client_override or RedisClient(config=redis_config)
        app.state.redis_client = redis_client
        try:
            await redis_client.connect()
            logger.info("Redis client connected.")
        except Exception as exc:  # noqa: BLE001
            # Do not crash startup if Redis is optional in development/test,
            # but log warning. Readiness check will report accurately.
            logger.warning("Redis initial connection failed: %s", exc)

        # 6. Initialize Paper Execution Adapter
        paper_config = PaperExecutionConfig(
            broker_name="paper",
            is_paper=True,
            balance=settings.paper_balance,
        )
        paper_adapter = paper_adapter_override or PaperExecutionAdapter(config=paper_config)
        app.state.paper_adapter = paper_adapter
        try:
            await paper_adapter.connect()
            logger.info("PaperExecutionAdapter connected.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("PaperExecutionAdapter initial connection failed: %s", exc)

        # 7. Register Health Checks
        health_registry = HealthCheckRegistry()
        health_registry.register(DatabaseHealthCheck(db_manager))
        health_registry.register(RedisHealthCheck(redis_client))
        app.state.health_registry = health_registry

        # 8. Initialize Metrics Registry
        metrics_registry = MetricsRegistry(prefix="orion")
        metrics_registry.counter("http_requests_total", "Total HTTP requests processed")
        metrics_registry.counter("paper_trades_total", "Total paper trade orders submitted")
        metrics_registry.gauge("paper_account_balance", "Current paper account balance")
        metrics_registry.set("paper_account_balance", float(settings.paper_balance))

        # 8.1 Initialize Rate Limiting & Abuse Defense Telemetry (EPIC-027)
        metrics_registry.counter("rate_limit_allowed_total", "Total requests allowed by rate limiting")
        metrics_registry.counter("rate_limit_rejected_total", "Total requests rejected with HTTP 429")
        metrics_registry.counter("rate_limit_redis_errors_total", "Total Redis failures during rate check")
        metrics_registry.counter("rate_limit_fallback_total", "Total rate checks served by in-memory fallback")
        app.state.metrics_registry = metrics_registry

        # 8.2 Initialize Rate Limiting & Abuse Defense Service
        if rate_limit_service_override is not None:
            rate_limit_service = rate_limit_service_override
        else:
            ip_resolver = ClientIpResolver(trusted_proxies=settings.trusted_proxies)
            redis_limiter = RedisRateLimiter(redis_client=redis_client)
            fallback_limiter = InMemoryRateLimiter(max_keys=10000)
            rate_limit_service = RateLimitService(
                redis_limiter=redis_limiter,
                fallback_limiter=fallback_limiter,
                ip_resolver=ip_resolver,
                metrics_registry=metrics_registry,
                enabled=settings.rate_limiting_enabled,
            )
        app.state.rate_limit_service = rate_limit_service

        # 8.5. Initialize Market Data Service (EPIC-021)
        if market_data_service_override is not None:
            market_service = market_data_service_override
        else:
            market_provider = create_market_data_provider(
                provider_type=settings.market_data_provider,
                api_key=settings.market_data_api_key,
                base_url=settings.market_data_base_url,
            )
            market_cache = MarketDataCache(redis_client=redis_client)
            market_service = MarketDataService(
                provider=market_provider,
                quality_engine=MarketDataQualityEngine(),
                cache=market_cache,
                paper_adapter=paper_adapter,
                metrics=metrics_registry,
            )
        app.state.market_data_service = market_service
        health_registry.register(MarketDataHealthCheck(market_service))

        logger.info("Trading Engine application runtime successfully initialized.")

        # 9. Initialize and start Autonomous Worker
        worker = AutonomousWorkerCoordinator(
            symbols=settings.worker_symbols,
            market_poll_interval=settings.market_data_poll_interval,
            trading_cycle_interval=settings.trading_cycle_interval,
            stale_threshold_seconds=settings.worker_stale_threshold,
            account_balance=settings.paper_balance,
            paper_adapter=paper_adapter,
            metrics_registry=metrics_registry,
            enabled=settings.worker_enabled,
        )
        app.state.worker = worker
        health_registry.register(worker.build_health_check())
        await worker.start()

        try:
            yield
        finally:
            # ─── Graceful Shutdown ──────────────────────────────────────────
            logger.info("Shutting down Trading Engine runtime...")

            # Stop Autonomous Worker first (must drain before closing broker/redis/db)
            try:
                await worker.stop()
            except Exception as exc:  # noqa: BLE001
                logger.error("Error stopping autonomous worker: %s", exc)

            # Disconnect Market Data Provider
            try:
                if hasattr(market_service, "provider") and hasattr(market_service.provider, "disconnect"):
                    await market_service.provider.disconnect()
                    logger.info("Market data provider disconnected.")
            except Exception as exc:  # noqa: BLE001
                logger.error("Error disconnecting market data provider: %s", exc)

            # Disconnect Paper Adapter
            try:
                if paper_adapter.is_connected:
                    await paper_adapter.disconnect()
                    logger.info("PaperExecutionAdapter disconnected.")
            except Exception as exc:  # noqa: BLE001
                logger.error("Error disconnecting PaperExecutionAdapter: %s", exc)

            # Disconnect Redis
            try:
                if redis_client.is_connected:
                    await redis_client.disconnect()
                    logger.info("Redis client disconnected.")
            except Exception as exc:  # noqa: BLE001
                logger.error("Error disconnecting Redis client: %s", exc)

            # Dispose Database Engine
            try:
                await db_manager.close()
                logger.info("DatabaseManager connection pool disposed.")
            except Exception as exc:  # noqa: BLE001
                logger.error("Error closing DatabaseManager: %s", exc)

            logger.info("Trading Engine shutdown complete.")

    return lifespan
