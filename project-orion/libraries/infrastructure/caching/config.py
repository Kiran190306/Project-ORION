"""Redis configuration and environment parsing."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RedisConfig:
    """Configuration settings for Redis connection and connection pool."""

    url: str = "redis://localhost:6379/0"
    max_connections: int = 20
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    decode_responses: bool = True

    @classmethod
    def from_env(cls) -> RedisConfig:
        """Load Redis configuration from environment variables."""
        url = os.getenv(
            "ORION_REDIS_URL",
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        )
        max_connections = int(os.getenv("ORION_REDIS_MAX_CONNECTIONS", "20"))
        socket_timeout = float(os.getenv("ORION_REDIS_SOCKET_TIMEOUT", "5.0"))
        socket_connect_timeout = float(os.getenv("ORION_REDIS_CONNECT_TIMEOUT", "5.0"))
        retry_on_timeout = (
            os.getenv("ORION_REDIS_RETRY_TIMEOUT", "true").lower()
            in ("true", "1", "yes")
        )
        health_check_interval = int(
            os.getenv("ORION_REDIS_HEALTH_CHECK_INTERVAL", "30")
        )

        return cls(
            url=url,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=health_check_interval,
            decode_responses=True,
        )
