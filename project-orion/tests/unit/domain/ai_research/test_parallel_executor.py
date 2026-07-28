"""Tests for parallel_executor module."""

from __future__ import annotations

import pytest

from libraries.domain.ai_research.exceptions import ParallelExecutionError
from libraries.domain.ai_research.models import ProgressReport
from libraries.domain.ai_research.parallel_executor import ParallelExecutor


class TestParallelExecutor:
    def test_empty_tasks(self):
        executor = ParallelExecutor()
        results = []
        coro = executor.execute(tuple())
        import asyncio

        results = asyncio.run(coro)
        assert results == ()

    def test_single_task(self):
        executor = ParallelExecutor()

        async def task():
            return 42

        import asyncio

        results = asyncio.run(executor.execute((task,)))
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == 42

    def test_multi_task(self):
        executor = ParallelExecutor(max_workers=2)

        async def task_a():
            return "a"

        async def task_b():
            return "b"

        import asyncio

        results = asyncio.run(executor.execute((task_a, task_b)))
        assert len(results) == 2

    def test_task_exception_isolation(self):
        executor = ParallelExecutor()

        async def good_task():
            return 42

        async def bad_task():
            raise ValueError("boom")

        import asyncio

        results = asyncio.run(executor.execute((good_task, bad_task)))
        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False
        assert "ValueError: boom" in results[1].error

    def test_cancellation(self):
        executor = ParallelExecutor()

        async def slow_task():
            import asyncio

            await asyncio.sleep(10)
            return 42

        executor.cancel()

        import asyncio

        results = asyncio.run(executor.execute((slow_task,)))
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error == "cancelled"

    def test_progress_callback(self):
        calls = []

        def callback(report: ProgressReport):
            calls.append(report)

        executor = ParallelExecutor(max_workers=2, progress_callback=callback)

        async def task():
            return 1

        import asyncio

        results = asyncio.run(executor.execute((task, task, task)))
        assert len(results) == 3
        assert len(calls) > 0

    def test_invalid_max_workers_raises_error(self):
        with pytest.raises(ParallelExecutionError, match="max_workers must be at least 1"):
            ParallelExecutor(max_workers=0)

    def test_task_id_present(self):
        executor = ParallelExecutor()

        async def task():
            return "done"

        import asyncio

        results = asyncio.run(executor.execute((task,)))
        assert results[0].task_id.startswith("task_")

    def test_concurrent_execution(self):
        import asyncio

        executor = ParallelExecutor(max_workers=4)
        started = set()

        async def task(n):
            started.add(n)
            await asyncio.sleep(0.01)
            return n

        results = asyncio.run(executor.execute(tuple(task(i) for i in range(4))))
        assert len(results) == 4
        assert all(r.success for r in results)

    def test_progress_report_model(self):
        report = ProgressReport(completed=5, total=10)
        assert report.completed == 5
        assert report.total == 10
        assert report.errors == 0
        assert report.progress_pct == 50.0

    def test_progress_report_complete(self):
        report = ProgressReport(completed=10, total=10, message="done")
        assert report.progress_pct == 100.0

    def test_progress_report_zero_total(self):
        report = ProgressReport(completed=0, total=0)
        assert report.progress_pct == 100.0

    def test_progress_report_validation(self):
        with pytest.raises(ValueError, match="completed must be non-negative"):
            ProgressReport(completed=-1, total=10)

    def test_task_result_model(self):
        from libraries.domain.ai_research.models import TaskResult

        r = TaskResult(task_id="t1", success=True, result=42)
        assert r.task_id == "t1"
        assert r.success is True
        assert r.result == 42
