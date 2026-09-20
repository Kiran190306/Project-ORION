"""Unit tests for RedisConfig, RedisClient, and caching exceptions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as AioRedisConnectionError
from redis.exceptions import TimeoutError as AioRedisTimeoutError

from libraries.infrastructure.caching import (
    RedisClient,
    RedisConfig,
    RedisConnectionError,
    RedisTimeoutError,
)


def test_redis_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify RedisConfig loads properly from environment variables."""
    monkeypatch.setenv("ORION_REDIS_URL", "redis://redis.internal:6380/2")
    monkeypatch.setenv("ORION_REDIS_MAX_CONNECTIONS", "50")
    monkeypatch.setenv("ORION_REDIS_SOCKET_TIMEOUT", "10.5")

    config = RedisConfig.from_env()
    assert config.url == "redis://redis.internal:6380/2"
    assert config.max_connections == 50
    assert config.socket_timeout == 10.5
    assert config.decode_responses is True


def test_redis_client_unconnected_operations_raise_error() -> None:
    """Verify calling Redis operations without connecting raises RedisConnectionError."""
    client = RedisClient()
    assert client.is_connected is False

    with pytest.raises(RedisConnectionError, match="not connected"):
        client._ensure_connected()


@pytest.mark.asyncio
async def test_redis_client_connect_and_disconnect() -> None:
    """Test connecting and disconnecting with mocked aioredis."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.aclose.return_value = None

    mock_pool = AsyncMock()
    mock_pool.disconnect.return_value = None

    with patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool), patch(
        "redis.asyncio.Redis", return_value=mock_redis
    ):
        client = RedisClient()
        await client.connect()

        assert client.is_connected is True
        assert await client.ping() is True
        assert await client.health_check() is True

        await client.disconnect()
        assert client.is_connected is False


@pytest.mark.asyncio
async def test_redis_client_crud_operations() -> None:
    """Test get, set, delete, exists, expire operations."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = "cached_value"
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = 1
    mock_redis.expire.return_value = True
    mock_redis.hget.return_value = "hash_val"
    mock_redis.hset.return_value = 1
    mock_redis.hgetall.return_value = {"field1": "val1"}

    mock_pool = AsyncMock()

    with patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool), patch(
        "redis.asyncio.Redis", return_value=mock_redis
    ):
        async with RedisClient() as client:
            assert client.is_connected is True

            # Get / Set / Delete
            val = await client.get("test_key")
            assert val == "cached_value"

            set_res = await client.set("test_key", "val", ttl_seconds=60)
            assert set_res is True

            del_res = await client.delete("test_key")
            assert del_res == 1

            exists_res = await client.exists("test_key")
            assert exists_res is True

            exp_res = await client.expire("test_key", 120)
            assert exp_res is True

            # Hash operations
            hget_res = await client.hget("my_hash", "field1")
            assert hget_res == "hash_val"

            hset_res = await client.hset("my_hash", "field1", "val1")
            assert hset_res == 1

            hgetall_res = await client.hgetall("my_hash")
            assert hgetall_res == {"field1": "val1"}


@pytest.mark.asyncio
async def test_redis_client_timeout_error_handling() -> None:
    """Test that Redis timeout errors are wrapped into RedisTimeoutError."""
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.side_effect = AioRedisTimeoutError("Read timed out")

    mock_pool = AsyncMock()

    with patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool), patch(
        "redis.asyncio.Redis", return_value=mock_redis
    ):
        async with RedisClient() as client:
            with pytest.raises(RedisTimeoutError, match="timed out"):
                await client.get("slow_key")


@pytest.mark.asyncio
async def test_redis_client_connection_error_handling() -> None:
    """Test that Redis connection failures are wrapped into RedisConnectionError."""
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = AioRedisConnectionError("Connection refused")

    mock_pool = AsyncMock()

    with patch("redis.asyncio.ConnectionPool.from_url", return_value=mock_pool), patch(
        "redis.asyncio.Redis", return_value=mock_redis
    ):
        client = RedisClient()
        with pytest.raises(RedisConnectionError, match="Failed to connect"):
            await client.connect()

        # health_check returns False without raising unhandled exception
        assert await client.health_check() is False
