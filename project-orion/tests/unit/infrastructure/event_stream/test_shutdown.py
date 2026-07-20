"""Tests for GracefulShutdown."""

from __future__ import annotations

import asyncio

import pytest

from libraries.infrastructure.event_stream.shutdown import (
    GracefulShutdown,
    ShutdownPhase,
)


class TestGracefulShutdown:
    def test_executes_all_registered_tasks(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown(timeout_seconds=10.0)
            executed: list[str] = []

            async def task_a() -> None:
                executed.append("a")

            async def task_b() -> None:
                executed.append("b")

            shutdown.register(
                name="task_a",
                phase=ShutdownPhase.STOP_PUBLISHERS,
                coro=task_a,
            )
            shutdown.register(
                name="task_b",
                phase=ShutdownPhase.FLUSH_QUEUES,
                coro=task_b,
            )

            results = await shutdown.execute()
            assert len(results) == 2
            assert executed == ["a", "b"]

        asyncio.run(exercise())

    def test_tasks_execute_in_phase_order(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()
            order: list[str] = []

            async def task1() -> None:
                order.append("stop_publishers")

            async def task2() -> None:
                order.append("flush_queues")

            async def task3() -> None:
                order.append("persist")

            async def task4() -> None:
                order.append("close")

            async def task5() -> None:
                order.append("cancel")

            shutdown.register("t1", ShutdownPhase.STOP_PUBLISHERS, task1)
            shutdown.register("t2", ShutdownPhase.FLUSH_QUEUES, task2)
            shutdown.register("t3", ShutdownPhase.PERSIST_SNAPSHOTS, task3)
            shutdown.register("t4", ShutdownPhase.CLOSE_TRANSPORTS, task4)
            shutdown.register("t5", ShutdownPhase.CANCEL_TASKS, task5)

            await shutdown.execute()
            assert order == [
                "stop_publishers",
                "flush_queues",
                "persist",
                "close",
                "cancel",
            ]

        asyncio.run(exercise())

    def test_task_timeout_does_not_crash(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown(timeout_seconds=10.0)

            async def slow_task() -> None:
                await asyncio.sleep(10.0)

            shutdown.register(
                name="slow",
                phase=ShutdownPhase.STOP_PUBLISHERS,
                coro=slow_task,
                timeout_seconds=0.01,
            )

            results = await shutdown.execute()
            assert len(results) == 1
            assert results[0].success is False
            assert "Timeout" in (results[0].error or "")

        asyncio.run(exercise())

    def test_task_failure_does_not_halt_shutdown(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()

            async def failing_task() -> None:
                raise ValueError("task failed")

            async def good_task() -> None:
                pass

            shutdown.register("fail", ShutdownPhase.STOP_PUBLISHERS, failing_task)
            shutdown.register("good", ShutdownPhase.FLUSH_QUEUES, good_task)

            results = await shutdown.execute()
            assert len(results) == 2
            assert results[0].success is False
            assert results[1].success is True

        asyncio.run(exercise())

    def test_was_successful_returns_true_when_all_ok(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()

            async def ok() -> None:
                pass

            shutdown.register("ok1", ShutdownPhase.STOP_PUBLISHERS, ok)
            shutdown.register("ok2", ShutdownPhase.FLUSH_QUEUES, ok)

            await shutdown.execute()
            assert await shutdown.was_successful()

        asyncio.run(exercise())

    def test_was_successful_returns_false_when_any_fails(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()

            async def fail() -> None:
                raise ValueError("fail")

            async def ok() -> None:
                pass

            shutdown.register("fail", ShutdownPhase.STOP_PUBLISHERS, fail)
            shutdown.register("ok", ShutdownPhase.FLUSH_QUEUES, ok)

            await shutdown.execute()
            assert not await shutdown.was_successful()

        asyncio.run(exercise())

    def test_shutting_down_flag(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()
            assert not shutdown.shutting_down

            async def ok() -> None:
                pass

            shutdown.register("ok", ShutdownPhase.STOP_PUBLISHERS, ok)

            await shutdown.execute()
            # After execution, the shut down flag should be set
            assert shutdown.shutting_down

        asyncio.run(exercise())

    def test_get_results_returns_results(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()

            async def ok() -> None:
                pass

            shutdown.register("ok", ShutdownPhase.STOP_PUBLISHERS, ok)
            await shutdown.execute()

            results = await shutdown.get_results()
            assert len(results) == 1

        asyncio.run(exercise())

    def test_reset_clears_state(self) -> None:
        async def exercise() -> None:
            shutdown = GracefulShutdown()

            async def ok() -> None:
                pass

            shutdown.register("ok", ShutdownPhase.STOP_PUBLISHERS, ok)
            await shutdown.execute()

            assert await shutdown.was_successful()

            shutdown.reset()
            assert not shutdown.shutting_down
            assert len(await shutdown.get_results()) == 0

        asyncio.run(exercise())

    def test_validates_timeout(self) -> None:
        with pytest.raises(ValueError):
            GracefulShutdown(timeout_seconds=0)
