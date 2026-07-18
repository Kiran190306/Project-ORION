"""
Cache Module

Module Description:
This module provides cache abstraction for data platform.
It supports multiple cache backends (Redis, in-memory, file-based).

Implementation Checklist:
- [ ] Cache interface
- [ ] Redis cache backend
- [ ] In-memory cache backend
- [ ] Cache key generation
- [ ] Cache expiration
- [ ] Cache invalidation

Dependency Notes:
- Depends on: shared/ (errors), libraries/infrastructure/caching/ (reuse)
- Used by: storage/, datasets/, providers/
"""

import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

from shared.errors import OrionError


class CacheError(OrionError):
    """Cache error."""

    pass


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache backend implementation."""

    def __init__(self) -> None:
        """Initialize in-memory cache."""
        self._cache: Dict[str, Any] = {}
        self._expires_at: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            expires_at = self._expires_at.get(key)
            if expires_at is not None and time.monotonic() >= expires_at:
                self.delete(key)
                return None
            return self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache."""
        try:
            self._cache[key] = value
            if ttl is not None:
                self._expires_at[key] = time.monotonic() + max(0.0, ttl.total_seconds())
            else:
                self._expires_at.pop(key, None)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
            self._expires_at.pop(key, None)
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache

    def clear(self) -> bool:
        """Clear all cache entries."""
        try:
            self._cache.clear()
            self._expires_at.clear()
            return True
        except Exception:
            return False


class CacheKeyGenerator:
    """Cache key generator."""

    @staticmethod
    def generate_key(prefix: str, **kwargs: Any) -> str:
        """Generate cache key from parameters."""
        parts = [prefix]
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}={value}")
        return ":".join(parts)

    @staticmethod
    def generate_dataset_key(
        dataset_id: str,
        version: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> str:
        """Generate cache key for dataset."""
        parts = ["dataset", dataset_id, version]
        if symbol:
            parts.append(symbol)
        if timeframe:
            parts.append(timeframe)
        return ":".join(parts)

    @staticmethod
    def generate_metadata_key(symbol: str, metadata_type: str) -> str:
        """Generate cache key for metadata."""
        return f"metadata:{metadata_type}:{symbol}"


class CacheManager:
    """Cache manager with key generation and backend management."""

    def __init__(self, backend: Optional[CacheBackend] = None) -> None:
        """Initialize cache manager.

        Args:
            backend: Cache backend (defaults to InMemoryCache)
        """
        self.backend = backend or InMemoryCache()
        self.key_generator = CacheKeyGenerator()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache."""
        return self.backend.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return self.backend.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.backend.exists(key)

    def clear(self) -> bool:
        """Clear all cache entries."""
        return self.backend.clear()

    def get_or_set(
        self, key: str, factory: Callable[..., Any], ttl: Optional[timedelta] = None
    ) -> Any:
        """Get value from cache or set using factory function."""
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, ttl)
        return value


# Global cache manager instance
_cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    return _cache_manager


def set_cache_backend(backend: CacheBackend) -> None:
    """Set cache backend for global manager."""
    _cache_manager.backend = backend
