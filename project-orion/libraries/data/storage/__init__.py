"""
Storage Module

Module Description:
This module provides storage abstraction for data platform.
It supports multiple storage backends (file system, S3, database).

Implementation Checklist:
- [ ] Storage interface
- [ ] File system storage backend
- [ ] S3 storage backend
- [ ] Database storage backend
- [ ] Storage path generation
- [ ] Storage checksum calculation
- [ ] Storage metadata management

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/compression/, libraries/data/serialization/
- Used by: datasets/, pipelines/
"""

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, Protocol, cast

from libraries.data.compression import compress, decompress
from libraries.data.serialization import serialize
from shared.errors import OrionError


class _S3Body(Protocol):
    """Typed surface of the streaming S3 response body."""

    def read(self) -> bytes:
        """Read the complete response body."""


class _S3Client(Protocol):
    """Typed surface used from the optional boto3 S3 client."""

    def put_object(self, **kwargs: object) -> object:
        ...

    def get_object(self, **kwargs: object) -> Mapping[str, object]:
        ...

    def head_object(self, **kwargs: object) -> object:
        ...

    def delete_object(self, **kwargs: object) -> object:
        ...

    def list_objects_v2(self, **kwargs: object) -> Mapping[str, object]:
        ...


class _Boto3Module(Protocol):
    """Typed surface used from the optional :mod:`boto3` package."""

    def client(self, service_name: str) -> _S3Client:
        ...


def _load_boto3() -> _Boto3Module:
    """Load boto3 only when the S3 backend is used."""
    try:
        module: ModuleType = import_module("boto3")
    except ImportError as error:
        raise StorageError("boto3 not installed") from error
    return cast(_Boto3Module, module)


def _is_missing_s3_key(error: Exception) -> bool:
    """Return whether an S3 client error represents a missing object key."""
    response = getattr(error, "response", None)
    if not isinstance(response, Mapping):
        return False
    error_details = response.get("Error")
    return isinstance(error_details, Mapping) and error_details.get("Code") in {
        "404",
        "NoSuchKey",
        "NotFound",
    }


class StorageError(OrionError):
    """Storage error."""

    pass


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    def write(self, path: str, data: bytes) -> bool:
        """Write data to storage."""
        pass

    @abstractmethod
    def read(self, path: str) -> Optional[bytes]:
        """Read data from storage."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists in storage."""
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete data from storage."""
        pass

    @abstractmethod
    def list(self, prefix: str) -> list[str]:
        """List files with prefix."""
        pass


class FileSystemStorage(StorageBackend):
    """File system storage backend implementation."""

    def __init__(self, base_path: str):
        """Initialize file system storage.

        Args:
            base_path: Base directory for storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get full path from relative path."""
        return self.base_path / path

    def write(self, path: str, data: bytes) -> bool:
        """Write data to file system."""
        try:
            full_path = self._get_full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(data)
            return True
        except Exception as e:
            raise StorageError(f"File system write failed: {str(e)}")

    def read(self, path: str) -> Optional[bytes]:
        """Read data from file system."""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            return full_path.read_bytes()
        except Exception as e:
            raise StorageError(f"File system read failed: {str(e)}")

    def exists(self, path: str) -> bool:
        """Check if path exists in file system."""
        full_path = self._get_full_path(path)
        return full_path.exists()

    def delete(self, path: str) -> bool:
        """Delete data from file system."""
        try:
            full_path = self._get_full_path(path)
            if full_path.exists():
                full_path.unlink()
            return True
        except Exception as e:
            raise StorageError(f"File system delete failed: {str(e)}")

    def list(self, prefix: str) -> list[str]:
        """List files with prefix."""
        try:
            full_prefix = self._get_full_path(prefix)
            if not full_prefix.exists():
                return []
            return [
                str(p.relative_to(self.base_path))
                for p in full_prefix.parent.glob(full_prefix.name)
            ]
        except Exception as e:
            raise StorageError(f"File system list failed: {str(e)}")


class S3Storage(StorageBackend):
    """S3 storage backend implementation."""

    def __init__(self, bucket: str, prefix: str = ""):
        """Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            prefix: S3 key prefix
        """
        self.bucket = bucket
        self.prefix = prefix
        self._client: _S3Client | None = None

    def _get_client(self) -> _S3Client:
        """Create the optional S3 client when it is first required."""
        if self._client is None:
            self._client = _load_boto3().client("s3")
        return self._client

    def _get_s3_key(self, path: str) -> str:
        """Get S3 key from relative path."""
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path

    def write(self, path: str, data: bytes) -> bool:
        """Write data to S3."""
        try:
            key = self._get_s3_key(path)
            self._get_client().put_object(Bucket=self.bucket, Key=key, Body=data)
            return True
        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"S3 write failed: {str(e)}")

    def read(self, path: str) -> Optional[bytes]:
        """Read data from S3."""
        try:
            key = self._get_s3_key(path)
            response = self._get_client().get_object(Bucket=self.bucket, Key=key)
            body = response.get("Body")
            if body is None:
                raise StorageError("S3 response did not contain an object body")
            return cast(_S3Body, body).read()
        except Exception as e:
            if _is_missing_s3_key(e):
                return None
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"S3 read failed: {str(e)}")

    def exists(self, path: str) -> bool:
        """Check if path exists in S3."""
        try:
            key = self._get_s3_key(path)
            self._get_client().head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            if _is_missing_s3_key(e):
                return False
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"S3 exists check failed: {str(e)}")

    def delete(self, path: str) -> bool:
        """Delete data from S3."""
        try:
            key = self._get_s3_key(path)
            self._get_client().delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"S3 delete failed: {str(e)}")

    def list(self, prefix: str) -> list[str]:
        """List files with prefix in S3."""
        try:
            key_prefix = self._get_s3_key(prefix)
            response = self._get_client().list_objects_v2(
                Bucket=self.bucket, Prefix=key_prefix
            )
            contents = response.get("Contents")
            if not isinstance(contents, list):
                return []
            return [
                key
                for item in contents
                if isinstance(item, Mapping)
                and isinstance((key := item.get("Key")), str)
            ]
        except Exception as e:
            if isinstance(e, StorageError):
                raise
            raise StorageError(f"S3 list failed: {str(e)}")


class StorageManager:
    """Storage manager with compression and serialization."""

    def __init__(
        self,
        backend: StorageBackend,
        compress: bool = True,
        compression_algorithm: str = "gzip",
        serialization_format: str = "json",
    ):
        """Initialize storage manager.

        Args:
            backend: Storage backend
            compress: Whether to compress data
            compression_algorithm: Compression algorithm to use
            serialization_format: Serialization format to use
        """
        self.backend = backend
        self.compress = compress
        self.compression_algorithm = compression_algorithm
        self.serialization_format = serialization_format

    def write(self, path: str, data: Any) -> bool:
        """Write data to storage with optional compression."""
        try:
            # Serialize
            serialized = serialize(data, self.serialization_format)

            # Compress if enabled
            if self.compress:
                serialized = compress(serialized, self.compression_algorithm)

            # Write to backend
            return self.backend.write(path, serialized)
        except Exception as e:
            raise StorageError(f"Storage write failed: {str(e)}")

    def read(self, path: str) -> Optional[Any]:
        """Read data from storage with optional decompression."""
        try:
            # Read from backend
            data = self.backend.read(path)
            if data is None:
                return None

            # Decompress if enabled
            if self.compress:
                from libraries.data.compression import decompress

                data = decompress(data, self.compression_algorithm)

            # Deserialize
            from libraries.data.serialization import deserialize

            return deserialize(data, self.serialization_format)
        except Exception as e:
            raise StorageError(f"Storage read failed: {str(e)}")

    def exists(self, path: str) -> bool:
        """Check if path exists in storage."""
        return self.backend.exists(path)

    def delete(self, path: str) -> bool:
        """Delete data from storage."""
        return self.backend.delete(path)

    def list(self, prefix: str) -> list[str]:
        """List files with prefix."""
        return self.backend.list(prefix)

    def calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def generate_storage_path(
        self,
        dataset_id: str,
        version: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        date: Optional[str] = None,
    ) -> str:
        """Generate storage path for dataset."""
        parts = [dataset_id, version]
        if symbol:
            parts.append(symbol)
        if timeframe:
            parts.append(timeframe)
        if date:
            parts.append(date)
        return "/".join(parts) + ".dat"
