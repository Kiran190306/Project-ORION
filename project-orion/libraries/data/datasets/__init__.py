"""
Datasets Module

Module Description:
This module provides dataset management for data platform.
It handles dataset lifecycle, versioning, immutability, and registry.

Implementation Checklist:
- [ ] Dataset manager
- [ ] Dataset creation
- [ ] Dataset versioning
- [ ] Dataset lifecycle management
- [ ] Dataset registry
- [ ] Dataset lineage tracking
- [ ] Dataset immutability enforcement

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/, libraries/data/storage/, libraries/data/quality/
- Used by: pipelines/, replay/
"""

from datetime import datetime
from typing import List, Optional

from libraries.data.schemas import (
    ChangeType,
    DataLineage,
    DatasetRegistry,
    DatasetType,
    DatasetVersion,
    DateRange,
    LifecycleStage,
    Transformation,
)
from libraries.data.storage import StorageManager
from libraries.data.validators import QualityChecker
from shared.errors import OrionError


class DatasetError(OrionError):
    """Dataset error."""

    pass


class DatasetManager:
    """Manager for dataset lifecycle and versioning."""

    def __init__(self, storage: StorageManager):
        """Initialize dataset manager.

        Args:
            storage: Storage manager
        """
        self.storage = storage
        self.quality_checker = QualityChecker()

    def create_dataset(
        self,
        dataset_id: str,
        dataset_type: DatasetType,
        symbol: str,
        timeframe: Optional[str] = None,
        date_range: Optional[DateRange] = None,
    ) -> DatasetRegistry:
        """Create a new dataset registry entry."""
        try:
            registry = DatasetRegistry(
                registry_id=f"{dataset_id}_v1.0.0",
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                dataset_version="1.0.0",
                symbol=symbol,
                timeframe=timeframe,
                date_range=date_range,
                lifecycle_stage=LifecycleStage.IMPORT,
                created_by="system",
            )

            # Save registry
            self._save_registry(registry)

            return registry
        except Exception as e:
            raise DatasetError(f"Failed to create dataset: {str(e)}")

    def create_version(
        self,
        dataset_id: str,
        previous_version: str,
        change_type: ChangeType,
        change_description: str,
        quality_score: float,
    ) -> DatasetVersion:
        """Create a new dataset version."""
        try:
            # Generate new version number
            new_version = self._increment_version(previous_version, change_type)

            version = DatasetVersion(
                version_id=f"{dataset_id}_v{new_version}",
                dataset_id=dataset_id,
                version=new_version,
                previous_version=previous_version,
                change_type=change_type,
                change_description=change_description,
                quality_score=quality_score,
                backward_compatible=change_type != ChangeType.MAJOR,
                forward_compatible=True,
                created_by="system",
            )

            # Save version
            self._save_version(version)

            return version
        except Exception as e:
            raise DatasetError(f"Failed to create version: {str(e)}")

    def _increment_version(self, version: str, change_type: ChangeType) -> str:
        """Increment version based on change type."""
        parts = version.split(".")
        if len(parts) != 3:
            return version

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if change_type == ChangeType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif change_type == ChangeType.MINOR:
            minor += 1
            patch = 0
        else:  # PATCH
            patch += 1

        return f"{major}.{minor}.{patch}"

    def update_lifecycle_stage(
        self, dataset_id: str, version: str, new_stage: LifecycleStage
    ) -> bool:
        """Update dataset lifecycle stage."""
        try:
            registry = self.get_registry(dataset_id, version)
            if not registry:
                raise DatasetError(f"Dataset not found: {dataset_id} v{version}")

            registry.lifecycle_stage = new_stage
            registry.stage_entry_date = datetime.utcnow()

            if new_stage in [LifecycleStage.ARCHIVE, LifecycleStage.RETIRE]:
                registry.stage_exit_date = datetime.utcnow()

            self._save_registry(registry)
            return True
        except Exception as e:
            raise DatasetError(f"Failed to update lifecycle stage: {str(e)}")

    def create_lineage(
        self,
        dataset_id: str,
        dataset_type: DatasetType,
        version: str,
        source_id: str,
        source_type: str,
        source_timestamp: datetime,
        transformations: List[Transformation],
        dependencies: List[str],
        quality_score: float,
    ) -> DataLineage:
        """Create data lineage record."""
        try:
            lineage = DataLineage(
                lineage_id=f"{dataset_id}_{version}_lineage",
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                version=version,
                source_id=source_id,
                source_type=source_type,
                source_timestamp=source_timestamp,
                transformations=transformations,
                dependencies=dependencies,
                quality_score=quality_score,
                created_by="system",
            )

            # Save lineage
            self._save_lineage(lineage)

            return lineage
        except Exception as e:
            raise DatasetError(f"Failed to create lineage: {str(e)}")

    def get_registry(self, dataset_id: str, version: str) -> Optional[DatasetRegistry]:
        """Get dataset registry entry."""
        try:
            path = f"registry/{dataset_id}/{version}/registry.json"
            return self.storage.read(path)
        except Exception:
            return None

    def get_version(self, dataset_id: str, version: str) -> Optional[DatasetVersion]:
        """Get dataset version."""
        try:
            path = f"versions/{dataset_id}/{version}/version.json"
            return self.storage.read(path)
        except Exception:
            return None

    def get_lineage(self, dataset_id: str, version: str) -> Optional[DataLineage]:
        """Get data lineage."""
        try:
            path = f"lineage/{dataset_id}/{version}/lineage.json"
            return self.storage.read(path)
        except Exception:
            return None

    def list_datasets(self) -> List[str]:
        """List all dataset IDs."""
        try:
            files = self.storage.list("registry/")
            dataset_ids = set()
            for file in files:
                parts = file.split("/")
                if len(parts) >= 2:
                    dataset_ids.add(parts[1])
            return list(dataset_ids)
        except Exception as e:
            raise DatasetError(f"Failed to list datasets: {str(e)}")

    def list_versions(self, dataset_id: str) -> List[str]:
        """List all versions for a dataset."""
        try:
            files = self.storage.list(f"registry/{dataset_id}/")
            versions = []
            for file in files:
                parts = file.split("/")
                if len(parts) >= 3:
                    versions.append(parts[2])
            return versions
        except Exception as e:
            raise DatasetError(f"Failed to list versions: {str(e)}")

    def _save_registry(self, registry: DatasetRegistry) -> bool:
        """Save dataset registry."""
        path = f"registry/{registry.dataset_id}/{registry.dataset_version}/registry.json"
        self.storage.write(path, registry)
        return True

    def _save_version(self, version: DatasetVersion) -> bool:
        """Save dataset version."""
        path = f"versions/{version.dataset_id}/{version.version}/version.json"
        self.storage.write(path, version)
        return True

    def _save_lineage(self, lineage: DataLineage) -> bool:
        """Save data lineage."""
        path = f"lineage/{lineage.dataset_id}/{lineage.version}/lineage.json"
        self.storage.write(path, lineage)
        return True
