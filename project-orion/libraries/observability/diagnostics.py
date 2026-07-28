"""Diagnostics service for ORION services.

Provides version, git commit, build metadata, environment,
loaded configuration, dependency versions, and runtime information.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """System runtime information."""

    python_version: str
    platform: str
    hostname: str
    pid: int
    cpus: int
    memory_total_mb: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "hostname": self.hostname,
            "pid": self.pid,
            "cpus": self.cpus,
            "memory_total_mb": round(self.memory_total_mb, 2),
        }


class DiagnosticsService:
    """Provides diagnostic information about the running service.

    Usage:
        diag = DiagnosticsService("my-service", version="1.0.0")
        info = diag.collect()
    """

    def __init__(
        self,
        service_name: str = "orion",
        version: str = "0.0.0",
        environment: str = "development",
        git_commit: str = "",
        build_metadata: dict[str, str] | None = None,
    ) -> None:
        self._service_name = service_name
        self._version = version
        self._environment = environment
        self._git_commit = git_commit or os.getenv("GIT_COMMIT", "")
        self._build_metadata = dict(build_metadata or {})
        self._collected_at: datetime | None = None

    def collect(self) -> dict[str, Any]:
        """Collect comprehensive diagnostic information."""
        self._collected_at = datetime.now(timezone.utc)

        # System info
        system_info = SystemInfo(
            python_version=sys.version.split()[0],
            platform=sys.platform,
            hostname=platform.node(),
            pid=os.getpid(),
            cpus=os.cpu_count() or 0,
            memory_total_mb=self._get_total_memory(),
        )

        # Dependency versions
        deps = self._get_dependency_versions()

        return {
            "service": {
                "name": self._service_name,
                "version": self._version,
                "environment": self._environment,
                "git_commit": self._git_commit,
                "build_metadata": dict(self._build_metadata),
            },
            "system": system_info.to_dict(),
            "runtime": {
                "started_at": self._collected_at.isoformat(),
                "uptime_seconds": 0,  # Set externally if needed
                "python_path": list(sys.path),
            },
            "dependencies": deps,
            "environment_variables": self._get_safe_env_vars(),
        }

    def service_info(self) -> dict[str, Any]:
        """Get information about the service."""
        return {
            "name": self._service_name,
            "version": self._version,
            "environment": self._environment,
            "git_commit": self._git_commit,
            "build_metadata": dict(self._build_metadata),
        }

    @staticmethod
    def _get_total_memory() -> float:
        """Get total system memory in MB."""
        try:
            import psutil

            return psutil.virtual_memory().total / (1024 * 1024)
        except ImportError:
            return 0.0

    @staticmethod
    def _get_dependency_versions() -> dict[str, str]:
        """Get versions of key dependencies."""
        deps: dict[str, str] = {}
        for mod_name in ("os", "sys", "json", "logging", "dataclasses", "asyncio"):
            try:
                mod = __import__(mod_name)
                deps[mod_name] = getattr(mod, "__version__", "stdlib")
            except ImportError:
                pass
        return deps

    @staticmethod
    def _get_safe_env_vars() -> dict[str, str]:
        """Get environment variables, masking sensitive values."""
        safe: dict[str, str] = {}
        sensitive_keys = {"password", "secret", "token", "key", "credit"}
        for key, value in os.environ.items():
            if not any(s in key.lower() for s in sensitive_keys):
                safe[key] = value
            else:
                safe[key] = "***REDACTED***"
        return safe
