"""
Project ORION - Interfaces & Contracts

Abstract interfaces and protocol definitions for the platform.
All services implement these interfaces to ensure pluggability.

Provides:
- Repository interfaces (database abstraction)
- Service interfaces (business logic boundaries)
- Handler interfaces (event/message handlers)
- Factory interfaces (object creation)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Protocol, TypeVar

from shared.common.result import Result
from shared.types import K, T, V

# ─── Repository Interfaces ────────────────────────────────────


class Repository(ABC, Generic[T, K]):
    """Base repository interface for data access."""

    @abstractmethod
    async def save(self, entity: T) -> Result[T, Exception]:
        """Save an entity."""
        ...

    @abstractmethod
    async def find_by_id(self, entity_id: K) -> Result[Optional[T], Exception]:
        """Find an entity by its identifier."""
        ...

    @abstractmethod
    async def delete(self, entity_id: K) -> Result[bool, Exception]:
        """Delete an entity by its identifier."""
        ...

    @abstractmethod
    async def exists(self, entity_id: K) -> Result[bool, Exception]:
        """Check if an entity exists."""
        ...


class ReadOnlyRepository(ABC, Generic[T, K]):
    """Read-only repository interface."""

    @abstractmethod
    async def find_by_id(self, entity_id: K) -> Result[Optional[T], Exception]:
        """Find an entity by its identifier."""
        ...

    @abstractmethod
    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> Result[list[T], Exception]:
        """Find all entities matching filters."""
        ...

    @abstractmethod
    async def count(self, **filters: Any) -> Result[int, Exception]:
        """Count entities matching filters."""
        ...


# ─── Service Interfaces ───────────────────────────────────────


class Service(ABC):
    """Base service interface."""

    @abstractmethod
    async def initialize(self) -> Result[bool, Exception]:
        """Initialize the service."""
        ...

    @abstractmethod
    async def health_check(self) -> Result[dict[str, Any], Exception]:
        """Check service health."""
        ...

    @abstractmethod
    async def shutdown(self) -> Result[bool, Exception]:
        """Gracefully shutdown the service."""
        ...


class Validator(ABC, Generic[T]):
    """Interface for validation logic."""

    @abstractmethod
    def validate(self, value: T) -> Result[T, Exception]:
        """Validate a value and return it or an error."""
        ...


class Transformer(ABC, Generic[T, V]):
    """Interface for object transformation."""

    @abstractmethod
    def transform(self, input_data: T) -> Result[V, Exception]:
        """Transform input to output."""
        ...


class CacheService(ABC, Generic[K, V]):
    """Interface for caching operations."""

    @abstractmethod
    async def get(self, key: K) -> Result[Optional[V], Exception]:
        """Get a value from cache."""
        ...

    @abstractmethod
    async def set(
        self,
        key: K,
        value: V,
        ttl_seconds: Optional[int] = None,
    ) -> Result[bool, Exception]:
        """Set a value in cache."""
        ...

    @abstractmethod
    async def delete(self, key: K) -> Result[bool, Exception]:
        """Delete a value from cache."""
        ...

    @abstractmethod
    async def clear(self) -> Result[bool, Exception]:
        """Clear all cache entries."""
        ...


# ─── Handler Interfaces ───────────────────────────────────────


class EventHandler(ABC, Generic[T]):
    """Interface for handling domain events."""

    @abstractmethod
    async def handle(self, event: T) -> Result[bool, Exception]:
        """Handle a domain event."""
        ...


class MessageHandler(ABC, Generic[T]):
    """Interface for handling queue messages."""

    @abstractmethod
    async def handle_message(self, message: T) -> Result[bool, Exception]:
        """Process a queue message."""
        ...


# ─── Factory Interfaces ───────────────────────────────────────


class Factory(ABC, Generic[T]):
    """Interface for object creation."""

    @abstractmethod
    def create(self, **kwargs: Any) -> T:
        """Create a new instance."""
        ...


class AsyncFactory(ABC, Generic[T]):
    """Async interface for object creation."""

    @abstractmethod
    async def create_async(self, **kwargs: Any) -> T:
        """Create a new instance asynchronously."""
        ...


# ─── Connection / Pool Interfaces ─────────────────────────────


class ConnectionPool(ABC):
    """Interface for connection pool management."""

    @abstractmethod
    async def acquire(self) -> Any:
        """Acquire a connection from pool."""
        ...

    @abstractmethod
    async def release(self, connection: Any) -> None:
        """Release a connection back to pool."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close all connections in pool."""
        ...


# ─── Protocol-Based Interfaces ────────────────────────────────


class Serializer(Protocol):
    """Protocol for serialization/deserialization."""

    def serialize(self, obj: Any) -> bytes:
        """Serialize object to bytes."""
        ...

    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to object."""
        ...


class Logger(Protocol):
    """Protocol for logging operations."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        ...

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        ...


class MetricCollector(Protocol):
    """Protocol for metric collection."""

    def increment(self, metric: str, tags: Optional[dict[str, str]] = None) -> None:
        ...

    def gauge(self, metric: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        ...

    def timing(
        self, metric: str, duration_ms: float, tags: Optional[dict[str, str]] = None
    ) -> None:
        ...
