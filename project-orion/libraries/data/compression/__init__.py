"""
Compression Module

Module Description:
This module provides compression abstraction for data platform.
It supports multiple compression algorithms (gzip, lz4, zstd).

Implementation Checklist:
- [ ] Gzip compressor
- [ ] LZ4 compressor
- [ ] Zstd compressor
- [ ] Compression registry
- [ ] Compression level configuration

Dependency Notes:
- Depends on: shared/ (errors)
- Used by: storage/, datasets/
"""

import gzip
from abc import ABC, abstractmethod
from importlib import import_module
from types import ModuleType
from typing import Optional, Protocol, cast

from shared.errors import OrionError


class _LZ4FrameModule(Protocol):
    """Typed surface used from the optional :mod:`lz4.frame` package."""

    def compress(self, data: bytes, *, compression_level: int | None) -> bytes:
        """Compress data with the requested LZ4 compression level."""

    def decompress(self, data: bytes) -> bytes:
        """Decompress LZ4 data."""


class _ZstdCompressorContext(Protocol):
    """Typed compression context supplied by the optional zstandard package."""

    def compress(self, data: bytes) -> bytes:
        """Compress data."""


class _ZstdDecompressorContext(Protocol):
    """Typed decompression context supplied by the optional zstandard package."""

    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""


class _ZstandardModule(Protocol):
    """Typed surface used from the optional :mod:`zstandard` package."""

    def ZstdCompressor(self, *, level: int) -> _ZstdCompressorContext:
        """Create a compression context."""

    def ZstdDecompressor(self) -> _ZstdDecompressorContext:
        """Create a decompression context."""


def _load_optional_module(module_name: str, dependency_name: str) -> ModuleType:
    """Load an optional dependency while preserving a clear domain error."""
    try:
        return import_module(module_name)
    except ImportError as error:
        raise CompressionError(f"{dependency_name} not installed") from error


class CompressionError(OrionError):
    """Compression error."""

    pass


class Compressor(ABC):
    """Abstract compressor interface."""

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress data."""
        pass

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        pass

    @property
    @abstractmethod
    def algorithm_name(self) -> str:
        """Get algorithm name."""
        pass


class GzipCompressor(Compressor):
    """Gzip compressor implementation."""

    def __init__(self, level: int = 6):
        """Initialize compressor.

        Args:
            level: Compression level (0-9, default 6)
        """
        if level < 0 or level > 9:
            raise CompressionError(f"Invalid compression level: {level}")
        self.level = level

    def compress(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        try:
            return gzip.compress(data, compresslevel=self.level)
        except Exception as e:
            raise CompressionError(f"Gzip compression failed: {str(e)}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        try:
            return gzip.decompress(data)
        except Exception as e:
            raise CompressionError(f"Gzip decompression failed: {str(e)}")

    @property
    def algorithm_name(self) -> str:
        """Get algorithm name."""
        return "gzip"


class LZ4Compressor(Compressor):
    """LZ4 compressor implementation."""

    def __init__(self, level: Optional[int] = None):
        """Initialize compressor.

        Args:
            level: Compression level (optional)
        """
        self.level = level

    def compress(self, data: bytes) -> bytes:
        """Compress data using LZ4."""
        lz4_frame = cast(_LZ4FrameModule, _load_optional_module("lz4.frame", "LZ4"))
        try:
            return lz4_frame.compress(data, compression_level=self.level)
        except Exception as e:
            raise CompressionError(f"LZ4 compression failed: {str(e)}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress LZ4 data."""
        lz4_frame = cast(_LZ4FrameModule, _load_optional_module("lz4.frame", "LZ4"))
        try:
            return lz4_frame.decompress(data)
        except Exception as e:
            raise CompressionError(f"LZ4 decompression failed: {str(e)}")

    @property
    def algorithm_name(self) -> str:
        """Get algorithm name."""
        return "lz4"


class ZstdCompressor(Compressor):
    """Zstd compressor implementation."""

    def __init__(self, level: int = 3):
        """Initialize compressor.

        Args:
            level: Compression level (1-22, default 3)
        """
        if level < 1 or level > 22:
            raise CompressionError(f"Invalid compression level: {level}")
        self.level = level

    def compress(self, data: bytes) -> bytes:
        """Compress data using Zstd."""
        zstd = cast(_ZstandardModule, _load_optional_module("zstandard", "Zstandard"))
        try:
            cctx = zstd.ZstdCompressor(level=self.level)
            return cctx.compress(data)
        except Exception as e:
            raise CompressionError(f"Zstd compression failed: {str(e)}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress Zstd data."""
        zstd = cast(_ZstandardModule, _load_optional_module("zstandard", "Zstandard"))
        try:
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(data)
        except Exception as e:
            raise CompressionError(f"Zstd decompression failed: {str(e)}")

    @property
    def algorithm_name(self) -> str:
        """Get algorithm name."""
        return "zstd"


class CompressionRegistry:
    """Registry for compressors."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._compressors: dict[str, Compressor] = {}
        self._register_default_compressors()

    def _register_default_compressors(self) -> None:
        """Register default compressors."""
        self.register("gzip", GzipCompressor())
        try:
            self.register("lz4", LZ4Compressor())
        except CompressionError:
            pass  # LZ4 not available
        try:
            self.register("zstd", ZstdCompressor())
        except CompressionError:
            pass  # Zstd not available

    def register(self, algorithm_name: str, compressor: Compressor) -> None:
        """Register a compressor."""
        self._compressors[algorithm_name] = compressor

    def get_compressor(self, algorithm_name: str) -> Compressor:
        """Get compressor by algorithm name."""
        if algorithm_name not in self._compressors:
            raise CompressionError(f"No compressor registered for algorithm: {algorithm_name}")
        return self._compressors[algorithm_name]

    def list_algorithms(self) -> list[str]:
        """List available algorithms."""
        return list(self._compressors.keys())


# Global registry instance
_registry = CompressionRegistry()


def compress(data: bytes, algorithm: str = "gzip") -> bytes:
    """Compress data using specified algorithm."""
    compressor = _registry.get_compressor(algorithm)
    return compressor.compress(data)


def decompress(data: bytes, algorithm: str = "gzip") -> bytes:
    """Decompress data using specified algorithm."""
    compressor = _registry.get_compressor(algorithm)
    return compressor.decompress(data)


def register_compressor(algorithm_name: str, compressor: Compressor) -> None:
    """Register a custom compressor."""
    _registry.register(algorithm_name, compressor)


def list_compression_algorithms() -> list[str]:
    """List available compression algorithms."""
    return _registry.list_algorithms()
