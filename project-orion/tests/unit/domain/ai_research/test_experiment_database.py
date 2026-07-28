"""Tests for experiment_database module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import ExperimentDatabaseError
from libraries.domain.ai_research.experiment_database import ExperimentDatabase
from libraries.domain.ai_research.models import (
    Experiment,
    ExperimentQuery,
    ExperimentStatus,
)


class TestExperimentDatabase:
    def test_create_experiment(self):
        db = ExperimentDatabase()
        import asyncio

        exp = Experiment(experiment_id="exp-1", name="Test", version="1.0")
        record = asyncio.run(db.create(exp))
        assert record.experiment_id == "exp-1"
        assert record.status == ExperimentStatus.CREATED

    def test_create_duplicate_raises_error(self):
        db = ExperimentDatabase()
        import asyncio

        exp = Experiment(experiment_id="exp-1", name="Test", version="1.0")
        asyncio.run(db.create(exp))
        with pytest.raises(ExperimentDatabaseError, match="already exists"):
            asyncio.run(db.create(exp))

    def test_get_experiment(self):
        db = ExperimentDatabase()
        import asyncio

        exp = Experiment(experiment_id="exp-1", name="Test", version="1.0")
        asyncio.run(db.create(exp))
        record = asyncio.run(db.get("exp-1"))
        assert record is not None
        assert record.name == "Test"

    def test_get_nonexistent(self):
        db = ExperimentDatabase()
        import asyncio

        record = asyncio.run(db.get("nonexistent"))
        assert record is None

    def test_update_status(self):
        db = ExperimentDatabase()
        import asyncio

        exp = Experiment(experiment_id="exp-1", name="Test", version="1.0")
        asyncio.run(db.create(exp))
        updated = asyncio.run(db.update("exp-1", status=ExperimentStatus.RUNNING))
        assert updated.status == ExperimentStatus.RUNNING

    def test_update_metrics(self):
        db = ExperimentDatabase()
        import asyncio

        exp = Experiment(experiment_id="exp-1", name="Test", version="1.0")
        asyncio.run(db.create(exp))
        updated = asyncio.run(db.update("exp-1", metrics={"sharpe": 1.5}))
        assert updated.metrics["sharpe"] == 1.5

    def test_update_nonexistent_raises_error(self):
        db = ExperimentDatabase()
        import asyncio

        with pytest.raises(ExperimentDatabaseError, match="not found"):
            asyncio.run(db.update("nonexistent"))

    def test_query_all(self):
        db = ExperimentDatabase()
        import asyncio

        for i in range(3):
            asyncio.run(
                db.create(Experiment(experiment_id=f"exp-{i}", name=f"Test {i}", version="1.0"))
            )
        results = asyncio.run(db.query())
        assert len(results) == 3

    def test_query_with_status_filter(self):
        db = ExperimentDatabase()
        import asyncio

        exp1 = Experiment(experiment_id="exp-1", name="A", version="1.0")
        exp2 = Experiment(experiment_id="exp-2", name="B", version="1.0")
        asyncio.run(db.create(exp1))
        asyncio.run(db.create(exp2))
        asyncio.run(db.update("exp-2", status=ExperimentStatus.RUNNING))

        results = asyncio.run(db.query(ExperimentQuery(status=ExperimentStatus.CREATED)))
        assert len(results) == 1
        assert results[0].experiment_id == "exp-1"

    def test_query_with_name_pattern(self):
        db = ExperimentDatabase()
        import asyncio

        asyncio.run(db.create(Experiment(experiment_id="exp-1", name="Alpha", version="1.0")))
        asyncio.run(db.create(Experiment(experiment_id="exp-2", name="Beta", version="1.0")))
        results = asyncio.run(db.query(ExperimentQuery(name_pattern="Alpha")))
        assert len(results) == 1

    def test_compare(self):
        db = ExperimentDatabase()
        import asyncio

        asyncio.run(db.create(Experiment(experiment_id="exp-1", name="A", version="1.0")))
        asyncio.run(db.create(Experiment(experiment_id="exp-2", name="B", version="1.0")))
        results = asyncio.run(db.compare(("exp-1", "exp-2")))
        assert len(results) == 2

    def test_compare_missing_raises_error(self):
        db = ExperimentDatabase()
        import asyncio

        asyncio.run(db.create(Experiment(experiment_id="exp-1", name="A", version="1.0")))
        with pytest.raises(ExperimentDatabaseError, match="not found"):
            asyncio.run(db.compare(("exp-1", "exp-missing")))

    def test_archive(self):
        db = ExperimentDatabase()
        import asyncio

        asyncio.run(db.create(Experiment(experiment_id="exp-1", name="A", version="1.0")))
        result = asyncio.run(db.archive("exp-1"))
        assert result is True
        assert asyncio.run(db.get("exp-1")) is None

    def test_archive_nonexistent(self):
        db = ExperimentDatabase()
        import asyncio

        result = asyncio.run(db.archive("nonexistent"))
        assert result is False

    def test_list_archived(self):
        db = ExperimentDatabase()
        import asyncio

        asyncio.run(db.create(Experiment(experiment_id="exp-1", name="A", version="1.0")))
        asyncio.run(db.archive("exp-1"))
        archived = asyncio.run(db.list_archived())
        assert len(archived) == 1

    def test_get_stats(self):
        db = ExperimentDatabase()
        import asyncio

        for i in range(3):
            asyncio.run(
                db.create(Experiment(experiment_id=f"exp-{i}", name=f"T{i}", version="1.0"))
            )
        asyncio.run(db.archive("exp-0"))
        stats = asyncio.run(db.get_stats())
        assert stats["active"] == 2
        assert stats["archived"] == 1
