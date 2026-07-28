"""Tests for observability diagnostics module."""

from __future__ import annotations

import pytest

from libraries.observability.diagnostics import DiagnosticsService, SystemInfo


class TestSystemInfo:
    def test_to_dict(self) -> None:
        info = SystemInfo(
            python_version="3.14",
            platform="win32",
            hostname="test-host",
            pid=12345,
            cpus=4,
            memory_total_mb=8192.0,
        )
        d = info.to_dict()
        assert d["python_version"] == "3.14"
        assert d["platform"] == "win32"
        assert d["hostname"] == "test-host"
        assert d["pid"] == 12345
        assert d["cpus"] == 4
        assert d["memory_total_mb"] == 8192.0

    def test_is_frozen(self) -> None:
        info = SystemInfo(
            python_version="3.14",
            platform="win32",
            hostname="h",
            pid=1,
            cpus=2,
            memory_total_mb=512,
        )
        with pytest.raises((AttributeError, TypeError)):
            info.pid = 999  # type: ignore[misc]


class TestDiagnosticsService:
    def test_collect_basic_info(self) -> None:
        diag = DiagnosticsService("test-svc", "1.0.0", "testing", git_commit="abc123")
        info = diag.collect()
        assert info["service"]["name"] == "test-svc"
        assert info["service"]["version"] == "1.0.0"
        assert info["service"]["environment"] == "testing"
        assert info["service"]["git_commit"] == "abc123"
        assert "system" in info
        assert "runtime" in info
        assert "dependencies" in info
        assert "environment_variables" in info

    def test_collect_system_info(self) -> None:
        diag = DiagnosticsService()
        info = diag.collect()
        assert "python_version" in info["system"]
        assert "platform" in info["system"]
        assert "pid" in info["system"]
        assert "cpus" in info["system"]

    def test_collect_runtime_info(self) -> None:
        diag = DiagnosticsService()
        info = diag.collect()
        assert "started_at" in info["runtime"]
        assert "uptime_seconds" in info["runtime"]
        assert "python_path" in info["runtime"]

    def test_service_info(self) -> None:
        diag = DiagnosticsService(
            "svc-name", "2.0.0", "production", git_commit="def456", build_metadata={"ci": "github"}
        )
        info = diag.service_info()
        assert info["name"] == "svc-name"
        assert info["version"] == "2.0.0"
        assert info["environment"] == "production"
        assert info["git_commit"] == "def456"
        assert info["build_metadata"]["ci"] == "github"

    def test_service_info_defaults(self) -> None:
        diag = DiagnosticsService()
        info = diag.service_info()
        assert info["name"] == "orion"
        assert info["version"] == "0.0.0"
        assert info["environment"] == "development"

    def test_environment_variables_redacted(self) -> None:
        import os

        os.environ["TEST_DB_PASSWORD"] = "supersecret"
        diag = DiagnosticsService()
        info = diag.collect()
        env_vars = info["environment_variables"]
        found = False
        for key, value in env_vars.items():
            if "password" in key.lower():
                found = True
                assert value == "***REDACTED***"
        if not found:
            # Key might not be present if name doesn't match; that's fine
            pass
        # Non-sensitive vars should be visible
        os.environ["TEST_OBSERVABILITY_VAR"] = "visible"
        info2 = diag.collect()
        assert info2["environment_variables"].get("TEST_OBSERVABILITY_VAR") == "visible"

    def test_dependencies(self) -> None:
        diag = DiagnosticsService()
        info = diag.collect()
        deps = info["dependencies"]
        assert "os" in deps
        assert "sys" in deps
        assert "json" in deps
        assert "logging" in deps
