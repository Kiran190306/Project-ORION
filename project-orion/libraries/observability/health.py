"""Health check system for ORION services.

Provides application, configuration, memory, CPU, disk, database,
message queue, readiness, liveness, and startup probe support.
"""

from __future__ import annotations

import os
import platform
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, Coroutine

from libraries.observability.config import HealthConfig


class HealthStatus(StrEnum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 2),
            "details": dict(self.details),
        }


HealthCheckFn = Callable[[], HealthCheckResult | Coroutine[Any, Any, HealthCheckResult]]


class HealthRegistry:
    """Registry for health checks organized by probe type.

    Supports liveness, readiness, and startup probes.
    """

    def __init__(self, config: HealthConfig | None = None) -> None:
        self._config = config or HealthConfig()
        self._liveness_checks: dict[str, HealthCheckFn] = {}
        self._readiness_checks: dict[str, HealthCheckFn] = {}
        self._startup_checks: dict[str, HealthCheckFn] = {}

    def register_liveness(self, name: str, check_fn: HealthCheckFn) -> None:
        """Register a liveness probe check."""
        self._liveness_checks[name] = check_fn

    def register_readiness(self, name: str, check_fn: HealthCheckFn) -> None:
        """Register a readiness probe check."""
        self._readiness_checks[name] = check_fn

    def register_startup(self, name: str, check_fn: HealthCheckFn) -> None:
        """Register a startup probe check."""
        self._startup_checks[name] = check_fn

    async def check_liveness(self) -> list[HealthCheckResult]:
        """Run all liveness checks."""
        return await self._run_checks(self._liveness_checks)

    async def check_readiness(self) -> list[HealthCheckResult]:
        """Run all readiness checks."""
        return await self._run_checks(self._readiness_checks)

    async def check_startup(self) -> list[HealthCheckResult]:
        """Run all startup checks."""
        return await self._run_checks(self._startup_checks)

    async def check_all(self) -> dict[str, Any]:
        """Run all health checks and return a comprehensive report."""
        liveness = await self.check_liveness()
        readiness = await self.check_readiness()
        startup = await self.check_startup()

        all_checks = liveness + readiness + startup
        overall = (
            HealthStatus.HEALTHY
            if all(c.status == HealthStatus.HEALTHY for c in all_checks)
            else (
                HealthStatus.UNHEALTHY
                if any(c.status == HealthStatus.UNHEALTHY for c in all_checks)
                else HealthStatus.DEGRADED
            )
        )

        return {
            "status": overall.value,
            "timestamp": time.time(),
            "liveness": [r.to_dict() for r in liveness],
            "readiness": [r.to_dict() for r in readiness],
            "startup": [r.to_dict() for r in startup],
        }

    async def _run_checks(self, checks: dict[str, HealthCheckFn]) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for name, check_fn in checks.items():
            start = time.time()
            try:
                result = check_fn()
                if hasattr(result, "__await__"):
                    result = await result
                if not isinstance(result, HealthCheckResult):
                    result = HealthCheckResult(name=name, status=HealthStatus.HEALTHY)
            except Exception as exc:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(exc),
                )
            duration = (time.time() - start) * 1000.0
            object.__setattr__(result, "duration_ms", duration)
            results.append(result)
        return results

    # ── Built-in checks ──────────────────────────────────────────────

    @staticmethod
    def app_alive(name: str = "application") -> HealthCheckFn:
        """Check that the application process is alive."""

        def check() -> HealthCheckResult:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY,
                details={"pid": os.getpid(), "python": platform.python_version()},
            )

        return check

    @staticmethod
    def disk_space(path: str = "/", threshold_mb: float = 100.0) -> HealthCheckFn:
        """Check available disk space."""

        def check() -> HealthCheckResult:
            try:
                usage = os.statvfs(path)
                free_mb = (usage.f_frsize * usage.f_bavail) / (1024 * 1024)
                status = HealthStatus.HEALTHY if free_mb > threshold_mb else HealthStatus.DEGRADED
                return HealthCheckResult(
                    name=f"disk_{path.replace('/', '_')}",
                    status=status,
                    details={
                        "free_mb": round(free_mb, 2),
                        "path": path,
                        "threshold_mb": threshold_mb,
                    },
                )
            except Exception as exc:
                return HealthCheckResult(
                    name=f"disk_{path.replace('/', '_')}",
                    status=HealthStatus.UNHEALTHY,
                    message=str(exc),
                )

        return check

    @staticmethod
    def memory_available(threshold_mb: float = 50.0) -> HealthCheckFn:
        """Check available memory."""
        import psutil

        def check() -> HealthCheckResult:
            try:
                mem = psutil.virtual_memory()
                free_mb = mem.available / (1024 * 1024)
                status = HealthStatus.HEALTHY if free_mb > threshold_mb else HealthStatus.DEGRADED
                return HealthCheckResult(
                    name="memory",
                    status=status,
                    details={
                        "available_mb": round(free_mb, 2),
                        "total_mb": round(mem.total / (1024 * 1024), 2),
                        "percent_used": mem.percent,
                        "threshold_mb": threshold_mb,
                    },
                )
            except ImportError:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    message="psutil not available",
                )
            except Exception as exc:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.UNHEALTHY,
                    message=str(exc),
                )

        return check
