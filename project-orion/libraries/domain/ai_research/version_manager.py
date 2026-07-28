"""Version manager for the AI research platform.

Tracks versions of experiments, datasets, strategies, and configurations.
Does NOT connect to external databases — uses in-memory storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from libraries.domain.ai_research.exceptions import VersionError
from libraries.domain.ai_research.models import VersionRecord


class VersionManager:
    """In-memory version manager for tracking entity versions.

    Supports:
    - Experiment versions
    - Dataset versions
    - Strategy versions
    - Configuration versions
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[VersionRecord]] = {}

    async def create_version(
        self,
        entity_type: str,
        entity_id: str,
        version: str,
        previous_version: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VersionRecord:
        """Create a new version record.

        Args:
            entity_type: Type of entity (e.g., 'experiment', 'dataset', 'strategy', 'config').
            entity_id: Unique identifier of the entity.
            version: Version string (e.g., '1.0.0').
            previous_version: Previous version string (optional).
            metadata: Additional metadata (optional).

        Returns:
            The created VersionRecord.

        Raises:
            VersionError: If version already exists for this entity.
        """
        if entity_type not in {"experiment", "dataset", "strategy", "config"}:
            raise VersionError(f"unsupported entity type: {entity_type}")

        key = f"{entity_type}:{entity_id}"
        existing = self._versions.get(key, [])
        for v in existing:
            if v.version == version:
                raise VersionError(
                    f"version '{version}' already exists for {entity_type} '{entity_id}'"
                )

        record = VersionRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            version=version,
            previous_version=previous_version,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        self._versions.setdefault(key, []).append(record)
        return record

    async def get_version(
        self, entity_type: str, entity_id: str, version: str
    ) -> VersionRecord | None:
        """Get a specific version record.

        Args:
            entity_type: Type of entity.
            entity_id: Unique identifier of the entity.
            version: Version string.

        Returns:
            The VersionRecord, or None if not found.
        """
        key = f"{entity_type}:{entity_id}"
        for v in self._versions.get(key, []):
            if v.version == version:
                return v
        return None

    async def list_versions(self, entity_type: str, entity_id: str) -> tuple[VersionRecord, ...]:
        """List all versions for an entity.

        Args:
            entity_type: Type of entity.
            entity_id: Unique identifier of the entity.

        Returns:
            Tuple of VersionRecords sorted by creation time (newest first).
        """
        key = f"{entity_type}:{entity_id}"
        records = sorted(
            self._versions.get(key, []),
            key=lambda r: r.created_at,
            reverse=True,
        )
        return tuple(records)

    async def get_latest_version(self, entity_type: str, entity_id: str) -> VersionRecord | None:
        """Get the latest version for an entity.

        Args:
            entity_type: Type of entity.
            entity_id: Unique identifier of the entity.

        Returns:
            The latest VersionRecord, or None if no versions exist.
        """
        versions = await self.list_versions(entity_type, entity_id)
        return versions[0] if versions else None

    async def get_stats(self) -> dict[str, int]:
        """Get version manager statistics.

        Returns:
            Dictionary with total versions and entity count.
        """
        total_versions = sum(len(v) for v in self._versions.values())
        return {
            "total_versions": total_versions,
            "total_entities": len(self._versions),
        }
