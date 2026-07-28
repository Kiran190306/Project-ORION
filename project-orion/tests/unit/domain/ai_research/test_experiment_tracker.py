"""Tests for EPIC-011 InMemoryExperimentTracker."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import ExperimentError
from libraries.domain.ai_research.experiment_tracker import InMemoryExperimentTracker
from libraries.domain.ai_research.models import Experiment, ExperimentResult, ExperimentStatus


class TestInMemoryExperimentTracker:
    """Test InMemoryExperimentTracker."""

    @pytest.fixture
    def tracker(self):
        return InMemoryExperimentTracker()

    @pytest.mark.asyncio
    async def test_create_experiment(self, tracker):
        experiment = Experiment(
            experiment_id="exp-1",
            name="test-experiment",
            version="1.0.0",
        )
        await tracker.create(experiment)
        result = await tracker.get_experiment("exp-1")
        assert result is not None
        assert result.experiment_id == "exp-1"
        assert result.name == "test-experiment"

    @pytest.mark.asyncio
    async def test_create_duplicate_raises_error(self, tracker):
        experiment = Experiment(
            experiment_id="exp-1",
            name="test",
            version="1.0.0",
        )
        await tracker.create(experiment)
        with pytest.raises(ExperimentError, match="already exists"):
            await tracker.create(experiment)

    @pytest.mark.asyncio
    async def test_update_status(self, tracker):
        experiment = Experiment(
            experiment_id="exp-1",
            name="test",
            version="1.0.0",
        )
        await tracker.create(experiment)
        await tracker.update_status("exp-1", ExperimentStatus.RUNNING)
        result = await tracker.get_experiment("exp-1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_status_nonexistent_raises_error(self, tracker):
        with pytest.raises(ExperimentError, match="not found"):
            await tracker.update_status("nonexistent", ExperimentStatus.RUNNING)

    @pytest.mark.asyncio
    async def test_finish_experiment(self, tracker):
        experiment = Experiment(
            experiment_id="exp-1",
            name="test",
            version="1.0.0",
        )
        await tracker.create(experiment)
        result = ExperimentResult(
            experiment_id="exp-1",
            status=ExperimentStatus.COMPLETED,
            metrics={"accuracy": 0.95},
        )
        await tracker.finish(result)
        stored_result = await tracker.get_result("exp-1")
        assert stored_result is not None
        assert stored_result.status == ExperimentStatus.COMPLETED
        assert stored_result.metrics["accuracy"] == 0.95

    @pytest.mark.asyncio
    async def test_finish_nonexistent_raises_error(self, tracker):
        result = ExperimentResult(
            experiment_id="nonexistent",
            status=ExperimentStatus.COMPLETED,
        )
        with pytest.raises(ExperimentError, match="not found"):
            await tracker.finish(result)

    @pytest.mark.asyncio
    async def test_get_result_nonexistent(self, tracker):
        result = await tracker.get_result("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_experiments_empty(self, tracker):
        experiments = await tracker.list_experiments()
        assert experiments == ()

    @pytest.mark.asyncio
    async def test_list_experiments(self, tracker):
        exp1 = Experiment(experiment_id="exp-1", name="test-1", version="1.0.0")
        exp2 = Experiment(experiment_id="exp-2", name="test-2", version="1.0.0")
        await tracker.create(exp1)
        await tracker.create(exp2)
        experiments = await tracker.list_experiments()
        assert len(experiments) == 2

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, tracker):
        stats = await tracker.get_stats()
        assert stats["total_experiments"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_experiments(self, tracker):
        exp1 = Experiment(experiment_id="exp-1", name="test-1", version="1.0.0")
        exp2 = Experiment(experiment_id="exp-2", name="test-2", version="1.0.0")
        await tracker.create(exp1)
        await tracker.create(exp2)

        await tracker.finish(
            ExperimentResult(
                experiment_id="exp-1",
                status=ExperimentStatus.COMPLETED,
            )
        )
        await tracker.finish(
            ExperimentResult(
                experiment_id="exp-2",
                status=ExperimentStatus.FAILED,
            )
        )

        stats = await tracker.get_stats()
        assert stats["total_experiments"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1
