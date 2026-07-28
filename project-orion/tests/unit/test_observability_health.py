"""Tests for observability health module."""

from __future__ import annotations

import asyncio

import pytest

from libraries.observability.health import HealthCheckResult, HealthRegistry, HealthStatus


class TestHealthStatus:
    def test_values(self) -> None:
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"


class TestHealthCheckResult:
    def test_defaults(self) -> None:
        result = HealthCheckResult(name="test", status=HealthStatus.HEALTHY)
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == ""
        assert result.duration_ms == 0.0

    def test_to_dict(self) -> None:
        result = HealthCheckResult(
            name="test", status=HealthStatus.HEALTHY, message="ok", details={"key": "val"}
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "healthy"
        assert d["message"] == "ok"
        assert d["details"]["key"] == "val"

    def test_is_frozen(self) -> None:
        result = HealthCheckResult(name="t", status=HealthStatus.HEALTHY)
        with pytest.raises((AttributeError, TypeError)):
            result.name = "new"  # type: ignore[misc]


class TestHealthRegistry:
    @pytest.mark.asyncio
    async def test_liveness_healthy(self) -> None:
        health = HealthRegistry()
        health.register_liveness("app", HealthRegistry.app_alive())
        results = await health.check_liveness()
        assert len(results) == 1
        assert results[0].status == HealthStatus.HEALTHY
        assert results[0].duration_ms >= 0

    @pytest.mark.asyncio
    async def test_readiness_healthy(self) -> None:
        health = HealthRegistry()
        health.register_readiness("db", lambda: HealthCheckResult("db", HealthStatus.HEALTHY))
        results = await health.check_readiness()
        assert len(results) == 1
        assert results[0].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_startup_healthy(self) -> None:
        health = HealthRegistry()
        health.register_startup("init", lambda: HealthCheckResult("init", HealthStatus.HEALTHY))
        results = await health.check_startup()
        assert len(results) == 1
        assert results[0].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_all_healthy(self) -> None:
        health = HealthRegistry()
        health.register_liveness("app", HealthRegistry.app_alive())
        report = await health.check_all()
        assert report["status"] == "healthy"
        assert "liveness" in report
        assert "readiness" in report
        assert "startup" in report

    @pytest.mark.asyncio
    async def test_unhealthy_check(self) -> None:
        health = HealthRegistry()
        health.register_liveness("failing", lambda: (_ for _ in ()).throw(Exception("fail")))
        results = await health.check_liveness()
        assert len(results) == 1
        assert results[0].status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_async_check(self) -> None:
        health = HealthRegistry()

        async def async_check() -> HealthCheckResult:
            return HealthCheckResult("async", HealthStatus.HEALTHY)

        health.register_liveness("async_check", async_check)
        results = await health.check_liveness()
        assert len(results) == 1
        assert results[0].status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_degraded_overall(self) -> None:
        health = HealthRegistry()
        health.register_liveness("ok", lambda: HealthCheckResult("ok", HealthStatus.HEALTHY))
        health.register_readiness(
            "degraded", lambda: HealthCheckResult("deg", HealthStatus.DEGRADED)
        )
        report = await health.check_all()
        assert report["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_app_alive_check(self) -> None:
        check = HealthRegistry.app_alive("test_app")
        result = check()
        assert isinstance(result, HealthCheckResult)
        assert result.name == "test_app"
        assert result.details.get("pid") is not None

    @pytest.mark.asyncio
    async def test_register_multiple_checks(self) -> None:
        health = HealthRegistry()
        for i in range(3):
            health.register_liveness(
                f"check_{i}", lambda i=i: HealthCheckResult(f"c{i}", HealthStatus.HEALTHY)
            )
        results = await health.check_liveness()
        assert len(results) == 3
