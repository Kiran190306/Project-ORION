"""
Data Serialization Module

Module Description:
This module provides serialization functionality for data platform objects.
It supports multiple serialization formats (JSON, MessagePack, Avro, Parquet).

Implementation Checklist:
- [ ] JSON serializer
- [ ] MessagePack serializer
- [ ] Avro serializer
- [ ] Parquet serializer
- [ ] Serialization registry
- [ ] Format detection

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/
- Used by: storage/, datasets/, pipelines/
"""

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from importlib import import_module
from types import ModuleType
from typing import Any, Protocol, cast

from shared.errors import OrionError


class _MessagePackModule(Protocol):
    """Typed surface used from the optional :mod:`msgpack` package."""

    def packb(self, data: object, *, use_bin_type: bool) -> bytes:
        ...

    def unpackb(self, data: bytes, *, raw: bool) -> Any:
        ...


def _load_msgpack() -> _MessagePackModule:
    """Load MessagePack only when the optional serializer is used."""
    try:
        module: ModuleType = import_module("msgpack")
    except ImportError as error:
        raise SerializationError("MessagePack not installed") from error
    return cast(_MessagePackModule, module)


class SerializationError(OrionError):
    """Serialization error."""

    pass


class Serializer(ABC):
    """Abstract serializer interface."""

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to data."""
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Get format name."""
        pass


class JSONSerializer(Serializer):
    """JSON serializer implementation."""

    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        try:
            if hasattr(data, "__dataclass_fields__"):
                data = asdict(data)
            return json.dumps(data, default=str).encode("utf-8")
        except Exception as e:
            raise SerializationError(f"JSON serialization failed: {str(e)}")

    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to data."""
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            raise SerializationError(f"JSON deserialization failed: {str(e)}")

    @property
    def format_name(self) -> str:
        """Get format name."""
        return "json"


class MessagePackSerializer(Serializer):
    """MessagePack serializer implementation."""

    def serialize(self, data: Any) -> bytes:
        """Serialize data to MessagePack bytes."""
        msgpack = _load_msgpack()
        try:
            if hasattr(data, "__dataclass_fields__"):
                data = asdict(data)
            return msgpack.packb(data, use_bin_type=True)
        except Exception as e:
            raise SerializationError(f"MessagePack serialization failed: {str(e)}")

    def deserialize(self, data: bytes) -> Any:
        """Deserialize MessagePack bytes to data."""
        msgpack = _load_msgpack()
        try:
            return msgpack.unpackb(data, raw=False)
        except Exception as e:
            raise SerializationError(f"MessagePack deserialization failed: {str(e)}")

    @property
    def format_name(self) -> str:
        """Get format name."""
        return "msgpack"


class SerializationRegistry:
    """Registry for serializers."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._serializers: dict[str, Serializer] = {}
        self._register_default_serializers()

    def _register_default_serializers(self) -> None:
        """Register default serializers."""
        self.register("json", JSONSerializer())
        try:
            self.register("msgpack", MessagePackSerializer())
        except SerializationError:
            pass  # MessagePack not available

    def register(self, format_name: str, serializer: Serializer) -> None:
        """Register a serializer."""
        self._serializers[format_name] = serializer

    def get_serializer(self, format_name: str) -> Serializer:
        """Get serializer by format name."""
        if format_name not in self._serializers:
            raise SerializationError(f"No serializer registered for format: {format_name}")
        return self._serializers[format_name]

    def list_formats(self) -> list[str]:
        """List available formats."""
        return list(self._serializers.keys())


# Global registry instance
_registry = SerializationRegistry()


def serialize(data: Any, format: str = "json") -> bytes:
    """Serialize data using specified format."""
    serializer = _registry.get_serializer(format)
    return serializer.serialize(data)


def deserialize(data: bytes, format: str = "json") -> Any:
    """Deserialize data using specified format."""
    serializer = _registry.get_serializer(format)
    return serializer.deserialize(data)


def register_serializer(format_name: str, serializer: Serializer) -> None:
    """Register a custom serializer."""
    _registry.register(format_name, serializer)


def list_serialization_formats() -> list[str]:
    """List available serialization formats."""
    return _registry.list_formats()
