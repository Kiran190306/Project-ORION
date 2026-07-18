"""
Project ORION - Secrets Management

Abstract secrets abstraction layer for secure credential storage.
Supports multiple backends (environment variables, Vault, files).

Provides:
- Secrets interface
- Environment variable backend
- File-based secrets
- In-memory cache
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from libraries.infrastructure.logging import get_logger

logger = get_logger("infrastructure.secrets")


class SecretsError(Exception):
    """Raised when secrets operations fail."""

    pass


class SecretsBackend(ABC):
    """Abstract secrets storage backend."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a secret by key."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Store a secret."""
        ...

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        ...


class EnvironmentSecretsBackend(SecretsBackend):
    """Secrets backend using environment variables."""

    def __init__(self, prefix: str = "ORION_SECRET_") -> None:
        self._prefix = prefix

    def get(self, key: str) -> Optional[str]:
        env_key = f"{self._prefix}{key.upper()}"
        return os.environ.get(env_key)

    def set(self, key: str, value: str) -> None:
        env_key = f"{self._prefix}{key.upper()}"
        os.environ[env_key] = value

    def has(self, key: str) -> bool:
        env_key = f"{self._prefix}{key.upper()}"
        return env_key in os.environ


class FileSecretsBackend(SecretsBackend):
    """Secrets backend using files on disk."""

    def __init__(self, secrets_dir: str | Path = "/run/secrets") -> None:
        self._secrets_dir = Path(secrets_dir)

    def get(self, key: str) -> Optional[str]:
        secret_file = self._secrets_dir / key
        if secret_file.exists():
            return secret_file.read_text(encoding="utf-8").strip()
        return None

    def set(self, key: str, value: str) -> None:
        self._secrets_dir.mkdir(parents=True, exist_ok=True)
        secret_file = self._secrets_dir / key
        secret_file.write_text(value, encoding="utf-8")

    def has(self, key: str) -> bool:
        secret_file = self._secrets_dir / key
        return secret_file.exists()


class SecretsManager:
    """
    Centralized secrets manager with caching and multiple backends.

    Usage:
        manager = SecretsManager()
        manager.add_backend(EnvironmentSecretsBackend())
        manager.add_backend(FileSecretsBackend())

        db_password = manager.get("database_password")
    """

    def __init__(self) -> None:
        self._backends: list[SecretsBackend] = []
        self._cache: dict[str, str] = {}
        self._use_cache: bool = True

    def add_backend(self, backend: SecretsBackend) -> None:
        """Add a secrets backend (first added = highest priority)."""
        self._backends.append(backend)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret by key.

        Args:
            key: Secret key name.
            default: Default value if secret is not found.

        Returns:
            Secret value or default.
        """
        # Check cache first
        if self._use_cache and key in self._cache:
            return self._cache[key]

        # Check backends in order
        for backend in self._backends:
            value = backend.get(key)
            if value is not None:
                if self._use_cache:
                    self._cache[key] = value
                return value

        return default

    def set(self, key: str, value: str) -> None:
        """Store a secret in all backends."""
        for backend in self._backends:
            backend.set(key, value)
        if self._use_cache:
            self._cache[key] = value

    def has(self, key: str) -> bool:
        """Check if a secret exists."""
        if self._use_cache and key in self._cache:
            return True
        return any(backend.has(key) for backend in self._backends)

    def clear_cache(self) -> None:
        """Clear the in-memory secret cache."""
        self._cache.clear()

    def disable_cache(self) -> None:
        """Disable secret caching."""
        self._use_cache = False

    def enable_cache(self) -> None:
        """Enable secret caching."""
        self._use_cache = True


# ─── Singleton ────────────────────────────────────────────────

_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global secrets manager."""
    global _manager
    if _manager is None:
        _manager = SecretsManager()
        _manager.add_backend(EnvironmentSecretsBackend())
    return _manager


def reset_secrets_manager() -> None:
    """Reset the secrets manager (for testing)."""
    global _manager
    _manager = None
