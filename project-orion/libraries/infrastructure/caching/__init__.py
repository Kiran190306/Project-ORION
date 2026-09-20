"""Caching and Key-Value Infrastructure Library for Project ORION."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.caching.config import RedisConfig
from libraries.infrastructure.caching.exceptions import (
    RedisConnectionError,
    RedisError,
    RedisTimeoutError,
)

F = TypeVar("F", bound=Callable[..., object])


def cache_decorator(func: F) -> F:
    """Cache decorator placeholder for method level caching."""
    return func


__all__ = [
    "RedisClient",
    "RedisConfig",
    "RedisConnectionError",
    "RedisError",
    "RedisTimeoutError",
    "cache_decorator",
]
