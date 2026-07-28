"""Tests for observability integration module."""

from __future__ import annotations

import pytest

from libraries.observability.integration import (
    ServiceObserver,
    configure_observability,
    observe_service,
)
from libraries.observability.metrics import MetricsRegistry


class TestObserveService:
    def test_decorated_function_runs(self) -> None:
        call_count = 0

        class TestService:
            @observe_service("test_svc.run", metrics=False, tracing=False)
            async def run(self) -> str:
                nonlocal call_count
                call_count += 1
                return "done"

        import asyncio

        svc = TestService()
        result = asyncio.run(svc.run())
        assert result == "done"
        assert call_count == 1

    def test_decorator_preserves_name(self) -> None:
        class TestService:
            @observe_service("test.method", metrics=False, tracing=False)
            async def my_method(self) -> None:
                pass

        assert TestService.my_method.__name__ == "my_method"

    def test_decorator_with_exception(self) -> None:
        class FailingService:
            @observe_service("fail.method", metrics=False, tracing=False)
            async def run(self) -> None:
                msg = "intentional failure"
                raise ValueError(msg)

        import asyncio

        svc = FailingService()
        with pytest.raises(ValueError, match="intentional failure"):
            asyncio.run(svc.run())

    def test_decorator_with_metrics(self) -> None:
        class TestService:
            @observe_service("metric.test", metrics=True, tracing=False)
            async def run(self) -> int:
                return 42

        reg = MetricsRegistry(prefix="test_int")
        configure_observability(metrics_registry=reg)

        import asyncio

        svc = TestService()
        result = asyncio.run(svc.run())
        assert result == 42


class TestServiceObserver:
    def test_wraps_async_method(self) -> None:
        class Engine:
            async def run(self) -> str:
                return "engine_result"

            async def health_check(self) -> dict:
                return {"status": "ok"}

        engine = Engine()
        observed = ServiceObserver(
            engine, "test_engine", metrics_enabled=False, tracing_enabled=False
        )
        import asyncio

        result = asyncio.run(observed.run())
        assert result == "engine_result"

    def test_health_delegates_to_wrapped(self) -> None:
        class Engine:
            async def health_check(self) -> dict:
                return {"status": "healthy", "version": "1.0"}

        observed = ServiceObserver(Engine(), "test", metrics_enabled=False, tracing_enabled=False)
        import asyncio

        health = asyncio.run(observed.health())
        assert health["service"] == "test"
        assert health["observed"] is True
        assert health["status"] == "healthy"

    def test_health_check_alias(self) -> None:
        class Engine:
            async def health_check(self) -> dict:
                return {"status": "ok"}

        observed = ServiceObserver(Engine(), "test", metrics_enabled=False, tracing_enabled=False)
        import asyncio

        result = asyncio.run(observed.health_check())
        assert result["status"] == "ok"

    def test_health_handles_exception(self) -> None:
        class BrokenEngine:
            async def health_check(self) -> dict:
                msg = "broken"
                raise RuntimeError(msg)

        observed = ServiceObserver(
            BrokenEngine(), "broken", metrics_enabled=False, tracing_enabled=False
        )
        import asyncio

        health = asyncio.run(observed.health())
        assert health["service"] == "broken"
        assert health["health_error"] is not None

    def test_health_without_method(self) -> None:
        class Minimal:
            pass

        observed = ServiceObserver(
            Minimal(), "minimal", metrics_enabled=False, tracing_enabled=False
        )
        import asyncio

        health = asyncio.run(observed.health())
        assert health["service"] == "minimal"
        assert health["observed"] is True

    def test_wrapped_property(self) -> None:
        engine = object()
        observed = ServiceObserver(engine, "test")
        assert observed.wrapped is engine

    def test_getattr_proxies_methods(self) -> None:
        class Engine:
            async def do_work(self) -> str:
                return "working"

        engine = Engine()
        observed = ServiceObserver(engine, "test", metrics_enabled=False, tracing_enabled=False)
        assert hasattr(observed, "do_work")
        assert callable(getattr(observed, "do_work"))


class TestConfigureObservability:
    def test_configure_defaults(self) -> None:
        configure_observability()
        assert True  # Should not raise

    def test_configure_with_all_params(self) -> None:
        reg = MetricsRegistry(prefix="cfg_test")
        configure_observability(
            service_name="my-svc",
            service_version="2.0.0",
            environment="staging",
            metrics_registry=reg,
        )
        assert True  # Should not raise
