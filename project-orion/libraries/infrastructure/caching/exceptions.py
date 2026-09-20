"""Exceptions for Redis caching and key-value infrastructure."""

from __future__ import annotations


class RedisError(Exception):
    """Base exception for Redis infrastructure errors."""

    def __init__(self, message: str, **kwargs: object) -> None:
        self.details = kwargs
        super().__init__(message)


class RedisConnectionError(RedisError, ConnectionError):
    """Raised when connecting or communicating with Redis server fails."""


class RedisTimeoutError(RedisError, TimeoutError):
    """Raised when a Redis command exceeds configured timeout."""
