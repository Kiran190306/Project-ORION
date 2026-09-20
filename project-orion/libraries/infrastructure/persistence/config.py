"""Database configuration, connection pooling, and engine management."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Configuration settings for PostgreSQL database connection."""

    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: float = 30.0
    pool_recycle: int = 1800
    pool_pre_ping: bool = True
    echo: bool = False

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        """Load database configuration from environment variables."""
        url = os.getenv(
            "ORION_DATABASE_URL",
            os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://orion:orion@localhost:5432/orion_dev",
            ),
        )
        # Normalize postgres:// to postgresql+asyncpg:// if needed for asyncpg driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        pool_size = int(os.getenv("ORION_DB_POOL_SIZE", "10"))
        max_overflow = int(os.getenv("ORION_DB_MAX_OVERFLOW", "20"))
        pool_timeout = float(os.getenv("ORION_DB_POOL_TIMEOUT", "30.0"))
        pool_recycle = int(os.getenv("ORION_DB_POOL_RECYCLE", "1800"))
        echo = os.getenv("ORION_DB_ECHO", "false").lower() in ("true", "1", "yes")

        return cls(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo=echo,
        )


class DatabaseManager:
    """Manages AsyncEngine lifecycle, session factories, and health checks."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self._config = config or DatabaseConfig.from_env()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def config(self) -> DatabaseConfig:
        return self._config

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self._initialize()
        assert self._engine is not None
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._initialize()
        assert self._session_factory is not None
        return self._session_factory

    def _initialize(self) -> None:
        """Initialize async engine and sessionmaker."""
        engine_kwargs: dict[str, object] = {
            "echo": self._config.echo,
        }
        # SQLite in-memory or file for testing doesn't use pool_size
        if not self._config.url.startswith("sqlite"):
            engine_kwargs.update(
                {
                    "pool_size": self._config.pool_size,
                    "max_overflow": self._config.max_overflow,
                    "pool_timeout": self._config.pool_timeout,
                    "pool_recycle": self._config.pool_recycle,
                    "pool_pre_ping": self._config.pool_pre_ping,
                }
            )

        self._engine = create_async_engine(self._config.url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def health_check(self) -> bool:
        """Perform database health check by running a lightweight query."""
        try:
            async with self.session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception:  # noqa: BLE001
            return False

    def session(self) -> AsyncSession:
        """Create a new AsyncSession."""
        return self.session_factory()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Async generator yielding a managed session context."""
        async with self.session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Dispose of the database connection pool."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
