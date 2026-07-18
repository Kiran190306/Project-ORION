"""Smoke tests for Project ORION repository bootstrap."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TOP_LEVEL_DIRS = (
    "shared",
    "libraries",
    "services",
    "sdk",
    "configs",
    "docker",
    "kubernetes",
    "docs",
    "tests",
)

REQUIRED_FILES = (
    "Makefile",
    "pyproject.toml",
    "docker-compose.dev.yml",
    "README.md",
    ".github/workflows/ci.yml",
)


@pytest.mark.parametrize("directory", REQUIRED_TOP_LEVEL_DIRS)
def test_required_top_level_directory_exists(directory: str) -> None:
    """Verify core repository directories from the architecture blueprint exist."""
    assert (
        PROJECT_ROOT / directory
    ).is_dir(), f"Missing required directory: {directory}"


@pytest.mark.parametrize("relative_path", REQUIRED_FILES)
def test_required_bootstrap_file_exists(relative_path: str) -> None:
    """Verify bootstrap tooling files exist."""
    assert (
        PROJECT_ROOT / relative_path
    ).is_file(), f"Missing required file: {relative_path}"


def test_pyproject_toml_is_valid() -> None:
    """Verify Poetry project metadata is present."""
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    assert "[tool.poetry]" in content
    assert 'name = "project-orion"' in content


def test_docker_compose_dev_defines_postgres_and_redis() -> None:
    """Verify development compose file defines PostgreSQL and Redis."""
    compose_path = PROJECT_ROOT / "docker-compose.dev.yml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose.get("services", {})
    assert "postgres" in services
    assert "redis" in services


def test_shared_enums_package_is_importable() -> None:
    """Verify the shared Python package layout supports imports."""
    spec = importlib.util.find_spec("shared.enums")
    assert spec is not None
    enums = importlib.import_module("shared.enums")
    assert enums.OrderSide.BUY.value == "buy"


def test_makefile_declares_bootstrap_targets() -> None:
    """Verify Makefile exposes CI/CD bootstrap targets."""
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "install",
        "lint",
        "test",
        "format",
        "typecheck",
        "clean",
        "docker-up",
        "docker-down",
    ):
        assert f"{target}:" in makefile, f"Missing Makefile target: {target}"
