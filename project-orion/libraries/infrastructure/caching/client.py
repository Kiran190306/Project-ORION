"""Asynchronous Redis client wrapper for Project ORION."""

from __future__ import annotations

import asyncio
from typing import Any, Self

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as AioRedisConnectionError
from redis.exceptions import RedisError as AioRedisGenericError
from redis.exceptions import TimeoutError as AioRedisTimeoutError

from libraries.infrastructure.caching.config import RedisConfig
from libraries.infrastructure.caching.exceptions import (
    RedisConnectionError,
    RedisError,
    RedisTimeoutError,
)


class RedisClient:
    """Asynchronous Redis infrastructure client supporting pooling, health checks, and CRUD."""

    def __init__(self, config: RedisConfig | None = None) -> None:
        self._config = config or RedisConfig.from_env()
        self._pool: aioredis.ConnectionPool | None = None
        self._client: aioredis.Redis | None = None
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def config(self) -> RedisConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Establish Redis connection pool and verify connectivity."""
        if self._connected and self._client is not None:
            return

        async with self._lock:
            if self._connected and self._client is not None:
                return
            try:
                self._pool = aioredis.ConnectionPool.from_url(
                    self._config.url,
                    max_connections=self._config.max_connections,
                    socket_timeout=self._config.socket_timeout,
                    socket_connect_timeout=self._config.socket_connect_timeout,
                    retry_on_timeout=self._config.retry_on_timeout,
                    health_check_interval=self._config.health_check_interval,
                    decode_responses=self._config.decode_responses,
                )
                self._client = aioredis.Redis(connection_pool=self._pool)
                await self._client.ping()
                self._connected = True
            except AioRedisTimeoutError as exc:
                self._connected = False
                raise RedisTimeoutError(
                    f"Connection to Redis timed out: {exc}",
                    url=self._config.url,
                ) from exc
            except (AioRedisConnectionError, OSError) as exc:
                self._connected = False
                raise RedisConnectionError(
                    f"Failed to connect to Redis at {self._config.url}: {exc}",
                    url=self._config.url,
                ) from exc
            except Exception as exc:
                self._connected = False
                raise RedisError(f"Unexpected Redis error: {exc}") from exc

    async def disconnect(self) -> None:
        """Close Redis connection pool gracefully."""
        async with self._lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None
            if self._pool is not None:
                res = self._pool.disconnect()
                if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                    await res
                self._pool = None
            self._connected = False

    async def ping(self) -> bool:
        """Send PING command to Redis server and return True if PONG received."""
        if self._client is None:
            return False
        try:
            res = await self._client.ping()
            return bool(res)
        except Exception:  # noqa: BLE001
            return False

    async def health_check(self) -> bool:
        """Perform health check verification."""
        try:
            if not self._connected or self._client is None:
                await self.connect()
            return await self.ping()
        except Exception:  # noqa: BLE001
            return False

    def _ensure_connected(self) -> aioredis.Redis:
        """Ensure client is initialized before executing operations."""
        if self._client is None or not self._connected:
            raise RedisConnectionError(
                "RedisClient is not connected. Call await client.connect() first."
            )
        return self._client

    async def get(self, key: str) -> str | None:
        """Retrieve a string value by key."""
        client = self._ensure_connected()
        try:
            res: Any = await client.get(key)
            return str(res) if res is not None else None
        except AioRedisTimeoutError as exc:
            raise RedisTimeoutError(f"Redis get timed out for key {key}") from exc
        except AioRedisConnectionError as exc:
            raise RedisConnectionError(f"Redis get connection error for key {key}") from exc
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis get failed for key {key}: {exc}") from exc

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> bool:
        """Store a string value with optional TTL expiration."""
        client = self._ensure_connected()
        try:
            res: Any = await client.set(key, value, ex=ttl_seconds)
            return bool(res)
        except AioRedisTimeoutError as exc:
            raise RedisTimeoutError(f"Redis set timed out for key {key}") from exc
        except AioRedisConnectionError as exc:
            raise RedisConnectionError(f"Redis set connection error for key {key}") from exc
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis set failed for key {key}: {exc}") from exc

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns number of keys deleted."""
        if not keys:
            return 0
        client = self._ensure_connected()
        try:
            res: Any = await client.delete(*keys)
            return int(res)
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis delete failed for keys {keys}: {exc}") from exc

    async def exists(self, *keys: str) -> bool:
        """Check if one or more keys exist."""
        if not keys:
            return False
        client = self._ensure_connected()
        try:
            res: Any = await client.exists(*keys)
            return int(res) > 0
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis exists failed for keys {keys}: {exc}") from exc

    async def expire(self, key: str, seconds: int) -> bool:
        """Set a timeout on key in seconds."""
        client = self._ensure_connected()
        try:
            res: Any = await client.expire(key, seconds)
            return bool(res)
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis expire failed for key {key}: {exc}") from exc

    async def hget(self, name: str, key: str) -> str | None:
        """Get the value of a hash field."""
        client = self._ensure_connected()
        try:
            res: Any = await client.hget(name, key)
            return str(res) if res is not None else None
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis hget failed for {name}.{key}: {exc}") from exc

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set the string value of a hash field."""
        client = self._ensure_connected()
        try:
            res: Any = await client.hset(name, key, value)
            return int(res)
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis hset failed for {name}.{key}: {exc}") from exc

    async def hgetall(self, name: str) -> dict[str, str]:
        """Get all fields and values of a hash."""
        client = self._ensure_connected()
        try:
            res: Any = await client.hgetall(name)
            return dict(res) if res else {}
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis hgetall failed for {name}: {exc}") from exc

    @property
    def raw_client(self) -> aioredis.Redis | None:
        """Access underlying redis.asyncio.Redis client if connected."""
        return self._client

    async def eval_script(
        self,
        script: str,
        keys: list[str],
        args: list[Any],
    ) -> Any:
        """Execute a Lua script atomically against Redis."""
        client = self._ensure_connected()
        try:
            return await client.eval(script, len(keys), *keys, *args)
        except AioRedisTimeoutError as exc:
            raise RedisTimeoutError(f"Redis eval_script timed out: {exc}") from exc
        except AioRedisConnectionError as exc:
            raise RedisConnectionError(f"Redis eval_script connection error: {exc}") from exc
        except AioRedisGenericError as exc:
            raise RedisError(f"Redis eval_script failed: {exc}") from exc

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        await self.disconnect()
