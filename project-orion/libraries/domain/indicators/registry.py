"""Indicator Registry.

Provides centralized registration, discovery, and version compatibility
checking for all indicator implementations. Thread-safe via asyncio.Lock.

No global state - instances are created via dependency injection.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.indicators.base import BaseIndicator
from libraries.domain.indicators.exceptions import IndicatorRegistrationError
from libraries.domain.indicators.interfaces import Indicator
from libraries.domain.indicators.models import IndicatorMetadata


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """An entry in the indicator registry."""

    name: str
    indicator_class: type[BaseIndicator]
    metadata: IndicatorMetadata
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"


class IndicatorRegistry:
    """Registry for indicator implementations.

    Supports:
    - register() / unregister() with duplicate detection
    - discover() by type, name, or pattern
    - metadata querying
    - version compatibility checking
    """

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        indicator_class: type[BaseIndicator],
        name: str | None = None,
        version: str = "1.0.0",
        force: bool = False,
    ) -> RegistryEntry:
        """Register an indicator class.

        Args:
            indicator_class: The indicator class to register.
            name: Optional override name (defaults to class metadata name).
            version: Version string for compatibility checking.
            force: If True, overwrite existing registration.

        Returns:
            The created RegistryEntry.

        Raises:
            IndicatorRegistrationError: If already registered and force=False.
        """
        async with self._lock:
            instance = indicator_class()
            indicator_name = name or instance.metadata.name
            metadata = instance.metadata

            if indicator_name in self._entries and not force:
                raise IndicatorRegistrationError(
                    f"Indicator '{indicator_name}' is already registered. "
                    f"Use force=True to overwrite."
                )

            entry = RegistryEntry(
                name=indicator_name,
                indicator_class=indicator_class,
                metadata=metadata,
                version=version,
            )
            self._entries[indicator_name] = entry
            return entry

    async def unregister(self, name: str) -> None:
        """Unregister an indicator by name.

        Args:
            name: Name of the indicator to unregister.

        Raises:
            KeyError: If the indicator is not registered.
        """
        async with self._lock:
            if name not in self._entries:
                raise KeyError(f"Indicator '{name}' is not registered.")
            del self._entries[name]

    async def discover(
        self,
        indicator_type: str | None = None,
        name_pattern: str | None = None,
    ) -> list[RegistryEntry]:
        """Discover registered indicators matching criteria.

        Args:
            indicator_type: Filter by IndicatorType value (e.g., "trend", "momentum").
            name_pattern: Filter by name substring (case-insensitive).

        Returns:
            List of matching RegistryEntry objects.
        """
        async with self._lock:
            results: list[RegistryEntry] = []
            for entry in self._entries.values():
                if indicator_type and entry.metadata.indicator_type.value != indicator_type:
                    continue
                if name_pattern and name_pattern.lower() not in entry.name.lower():
                    continue
                results.append(entry)
            return results

    async def get_metadata(self, name: str) -> IndicatorMetadata | None:
        """Get metadata for a registered indicator.

        Args:
            name: Name of the indicator.

        Returns:
            IndicatorMetadata if found, None otherwise.
        """
        async with self._lock:
            entry = self._entries.get(name)
            return entry.metadata if entry else None

    async def get_class(self, name: str) -> type[BaseIndicator] | None:
        """Get the indicator class for a registered name.

        Args:
            name: Name of the indicator.

        Returns:
            Indicator class if found, None otherwise.
        """
        async with self._lock:
            entry = self._entries.get(name)
            return entry.indicator_class if entry else None

    async def is_registered(self, name: str) -> bool:
        """Check if an indicator is registered.

        Args:
            name: Name of the indicator.

        Returns:
            True if registered, False otherwise.
        """
        async with self._lock:
            return name in self._entries

    async def check_version_compatibility(
        self,
        name: str,
        required_version: str,
    ) -> bool:
        """Check if a registered indicator meets a version requirement.

        Simple semantic version check - major version must match.

        Args:
            name: Name of the indicator.
            required_version: Required version string.

        Returns:
            True if compatible, False otherwise.
        """
        async with self._lock:
            entry = self._entries.get(name)
            if not entry:
                return False

            required_parts = required_version.split(".")
            actual_parts = entry.version.split(".")

            if not required_parts or not actual_parts:
                return False

            # Major version must match
            return required_parts[0] == actual_parts[0]

    async def list_all(self) -> list[RegistryEntry]:
        """List all registered indicators.

        Returns:
            List of all RegistryEntry objects.
        """
        async with self._lock:
            return list(self._entries.values())

    async def count(self) -> int:
        """Return the number of registered indicators."""
        async with self._lock:
            return len(self._entries)

    async def clear(self) -> None:
        """Clear all registered indicators."""
        async with self._lock:
            self._entries.clear()
