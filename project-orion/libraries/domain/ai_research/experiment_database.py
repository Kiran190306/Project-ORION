"""Lightweight experiment persistence abstraction for the AI research platform.

Supports create, update, query, compare, archive, metadata, and tags.
Does NOT connect to external databases — uses in-memory storage.
"""

from __future__ import annotations

from datetime import datetime, timezone

from libraries.domain.ai_research.exceptions import ExperimentDatabaseError
from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentQuery,
    ExperimentRecord,
    ExperimentStatus,
)


class ExperimentDatabase:
    """In-memory experiment database for persistence abstraction.

    Provides a clean interface for experiment lifecycle management.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, ExperimentRecord] = {}
        self._archived: dict[str, ExperimentRecord] = {}

    async def create(self, experiment: Experiment) -> ExperimentRecord:
        """Create a new experiment record.

        Args:
            experiment: The experiment to persist.

        Returns:
            The created ExperimentRecord.

        Raises:
            ExperimentDatabaseError: If experiment ID already exists.
        """
        if experiment.experiment_id in self._experiments:
            raise ExperimentDatabaseError(f"experiment '{experiment.experiment_id}' already exists")
        now = datetime.now(timezone.utc)
        record = ExperimentRecord(
            experiment_id=experiment.experiment_id,
            name=experiment.name,
            status=ExperimentStatus.CREATED,
            version=experiment.version,
            metadata=dict(experiment.metadata),
            created_at=now,
            updated_at=now,
        )
        self._experiments[experiment.experiment_id] = record
        return record

    async def update(
        self,
        experiment_id: str,
        status: ExperimentStatus | None = None,
        metrics: dict[str, float] | None = None,
        tags: frozenset[str] | None = None,
    ) -> ExperimentRecord:
        """Update an existing experiment record.

        Args:
            experiment_id: ID of the experiment to update.
            status: New status (optional).
            metrics: New metrics to merge (optional).
            tags: New tags (optional).

        Returns:
            The updated ExperimentRecord.

        Raises:
            ExperimentDatabaseError: If experiment not found.
        """
        existing = self._experiments.get(experiment_id)
        if existing is None:
            raise ExperimentDatabaseError(f"experiment '{experiment_id}' not found")

        new_metrics = dict(existing.metrics)
        if metrics:
            new_metrics.update(metrics)

        new_tags = existing.tags
        if tags is not None:
            new_tags = tags

        updated = ExperimentRecord(
            experiment_id=existing.experiment_id,
            name=existing.name,
            status=status or existing.status,
            version=existing.version,
            tags=new_tags,
            metrics=new_metrics,
            metadata=dict(existing.metadata),
            created_at=existing.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._experiments[experiment_id] = updated
        return updated

    async def get(self, experiment_id: str) -> ExperimentRecord | None:
        """Get an experiment record by ID.

        Args:
            experiment_id: ID of the experiment.

        Returns:
            The ExperimentRecord, or None if not found.
        """
        return self._experiments.get(experiment_id)

    async def query(self, query: ExperimentQuery | None = None) -> tuple[ExperimentRecord, ...]:
        """Query experiments with optional filters.

        Args:
            query: Query filters (optional).

        Returns:
            Tuple of matching ExperimentRecords.
        """
        records = list(self._experiments.values())

        if query is not None:
            if query.status is not None:
                records = [r for r in records if r.status == query.status]
            if query.tags is not None:
                records = [r for r in records if query.tags.issubset(r.tags)]
            if query.name_pattern is not None:
                records = [r for r in records if query.name_pattern.lower() in r.name.lower()]

        records.sort(key=lambda r: r.created_at, reverse=True)
        if query is not None:
            offset = query.offset if query.offset is not None else 0
            limit = query.limit if query.limit is not None else len(records)
            records = records[offset : offset + limit]
        return tuple(records)

    async def compare(self, experiment_ids: tuple[str, ...]) -> tuple[ExperimentRecord, ...]:
        """Compare multiple experiments by retrieving their records.

        Args:
            experiment_ids: IDs of experiments to compare.

        Returns:
            Tuple of ExperimentRecords in the same order as input IDs.

        Raises:
            ExperimentDatabaseError: If any experiment ID is not found.
        """
        records: list[ExperimentRecord] = []
        for exp_id in experiment_ids:
            record = self._experiments.get(exp_id)
            if record is None:
                raise ExperimentDatabaseError(f"experiment '{exp_id}' not found")
            records.append(record)
        return tuple(records)

    async def archive(self, experiment_id: str) -> bool:
        """Archive an experiment, moving it out of active storage.

        Args:
            experiment_id: ID of the experiment to archive.

        Returns:
            True if archived, False if not found.
        """
        record = self._experiments.pop(experiment_id, None)
        if record is None:
            return False
        self._archived[experiment_id] = record
        return True

    async def list_archived(self) -> tuple[ExperimentRecord, ...]:
        """List all archived experiments.

        Returns:
            Tuple of archived ExperimentRecords.
        """
        return tuple(self._archived.values())

    async def get_stats(self) -> dict[str, int]:
        """Get database statistics.

        Returns:
            Dictionary with active and archived counts.
        """
        return {
            "active": len(self._experiments),
            "archived": len(self._archived),
        }
