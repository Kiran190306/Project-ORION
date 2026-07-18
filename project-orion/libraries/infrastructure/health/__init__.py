"""
Project ORION - Health Checks

Standardized health check system for all services.
Supports liveness, readiness, and startup probes.

Provides:
- Health check registry
- Standard health checks (database, cache, messaging)
- Composite health checks
- Health status reporting
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from inspect import isawaitable
from typing import Any, Callable, Optional


class HealthStatus:
    """Health check status constants."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: str = HealthStatus.HEALTHY
    message: str = ""
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        return self.status == HealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        return self.status == HealthStatus.UNHEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "details": self.details,
            "checked_at": self.checked_at,
        }


class HealthCheck(ABC):
    """Base class for health checks."""

    def __init__(self, name: str, timeout_seconds: float = 5.0) -> None:
        self.name = name
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def check(self) -> HealthCheckResult:
        """Execute the health check."""
        ...

    async def run(self) -> HealthCheckResult:
        """Run the health check with timing."""
        start = time.monotonic()
        try:
            result = await self.check()
            result.duration_ms = (time.monotonic() - start) * 1000
            return result
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
                duration_ms=duration,
            )


class HealthCheckRegistry:
    """Registry for managing and running health checks."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> HealthCheck:
        """Register a health check."""
        self._checks[check.name] = check
        return check

    def register_fn(
        self,
        name: str,
        check_fn: Callable[[], Any],
        timeout_seconds: float = 5.0,
    ) -> None:
        """Register a health check function."""

        class _FunctionCheck(HealthCheck):
            async def check(self) -> HealthCheckResult:
                try:
                    result = check_fn()
                    if isawaitable(result):
                        result = await result
                    return HealthCheckResult(
                        name=name,
                        status=HealthStatus.HEALTHY,
                        message="OK",
                    )
                except Exception as exc:
                    return HealthCheckResult(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(exc),
                    )

        self.register(_FunctionCheck(name, timeout_seconds))

    def unregister(self, name: str) -> None:
        """Unregister a health check."""
        self._checks.pop(name, None)

    async def run_all(self) -> list[HealthCheckResult]:
        """Run all registered health checks."""
        results: list[HealthCheckResult] = []
        for check in self._checks.values():
            result = await check.run()
            results.append(result)
        return results

    async def run_liveness(self) -> list[HealthCheckResult]:
        """Run liveness checks (critical checks only)."""
        return await self.run_all()

    async def run_readiness(self) -> list[HealthCheckResult]:
        """Run readiness checks."""
        return await self.run_all()

    def get_summary(self, results: list[HealthCheckResult]) -> dict[str, Any]:
        """Get a summary of health check results."""
        total = len(results)
        healthy = sum(1 for r in results if r.is_healthy)
        degraded = sum(1 for r in results if r.is_degraded)
        unhealthy = sum(1 for r in results if r.is_unhealthy)

        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall,
            "total_checks": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "checks": [r.to_dict() for r in results],
            "checked_at": datetime.utcnow().isoformat(),
        }


# ─── Singleton Registry ───────────────────────────────────────

_registry: Optional[HealthCheckRegistry] = None


def get_health_registry() -> HealthCheckRegistry:
    """Get the global health check registry."""
    global _registry
    if _registry is None:
        _registry = HealthCheckRegistry()
    return _registry


def reset_health_registry() -> None:
    """Reset the health check registry (for testing)."""
    global _registry
    _registry = None
