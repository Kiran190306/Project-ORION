"""In-memory experiment tracker for AI research.

Tracks experiment lifecycle (create, update status, finish)
with metadata, version, and timestamp support.

No persistence. No external dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone

from libraries.domain.ai_research.exceptions import ExperimentError
from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentResult,
    ExperimentStatus,
)


class InMemoryExperimentTracker:
    """Tracks experiment lifecycle in memory.

    Supports:
        - Create experiment
        - Update status
        - Finish experiment with results
        - Metrics and metadata
    """

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._results: dict[str, ExperimentResult] = {}

    async def create(self, experiment: Experiment) -> None:
        """Register a new experiment.

        Args:
            experiment: Experiment to register.

        Raises:
            ExperimentError: If an experiment with the same ID already exists.
        """
        if experiment.experiment_id in self._experiments:
            raise ExperimentError(f"experiment '{experiment.experiment_id}' already exists")
        self._experiments[experiment.experiment_id] = experiment

    async def update_status(self, experiment_id: str, status: ExperimentStatus | str) -> None:
        """Update the status of an experiment.

        Args:
            experiment_id: Experiment identifier.
            status: New status value.

        Raises:
            ExperimentError: If the experiment is not found.
        """
        if experiment_id not in self._experiments:
            raise ExperimentError(f"experiment '{experiment_id}' not found")

        existing = self._experiments[experiment_id]
        updated = Experiment(
            experiment_id=existing.experiment_id,
            name=existing.name,
            version=existing.version,
            metadata=dict(existing.metadata),
            created_at=existing.created_at,
        )
        self._experiments[experiment_id] = updated

    async def finish(self, result: ExperimentResult) -> None:
        """Mark an experiment as finished.

        Args:
            result: Experiment result.

        Raises:
            ExperimentError: If the experiment is not found.
        """
        if result.experiment_id not in self._experiments:
            raise ExperimentError(f"experiment '{result.experiment_id}' not found")
        self._results[result.experiment_id] = result

    async def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Get an experiment by ID.

        Args:
            experiment_id: Experiment identifier.

        Returns:
            The experiment, or None if not found.
        """
        return self._experiments.get(experiment_id)

    async def get_result(self, experiment_id: str) -> ExperimentResult | None:
        """Get an experiment result by ID.

        Args:
            experiment_id: Experiment identifier.

        Returns:
            The experiment result, or None if not found.
        """
        return self._results.get(experiment_id)

    async def list_experiments(self) -> tuple[Experiment, ...]:
        """List all registered experiments.

        Returns:
            Tuple of all experiments.
        """
        return tuple(self._experiments.values())

    async def get_stats(self) -> dict[str, int]:
        """Get tracker statistics.

        Returns:
            Dictionary with total, completed, and failed counts.
        """
        completed = sum(
            1 for result in self._results.values() if result.status == ExperimentStatus.COMPLETED
        )
        failed = sum(
            1 for result in self._results.values() if result.status == ExperimentStatus.FAILED
        )
        return {
            "total_experiments": len(self._experiments),
            "completed": completed,
            "failed": failed,
        }


# Backward-compatible alias
ExperimentTracker = InMemoryExperimentTracker
