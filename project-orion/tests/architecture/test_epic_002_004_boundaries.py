"""Static architecture checks for the frozen EPIC-002--004 package boundaries."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOTS = (PROJECT_ROOT / "shared", PROJECT_ROOT / "libraries")


def source_files() -> list[Path]:
    """Return only real source files.

    Excludes generated/cache directories that may contain Python stubs.
    """

    excluded_dir_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".git",
        ".idea",
        ".vscode",
        "build",
        "dist",
    }

    files: list[Path] = []
    for root in SOURCE_ROOTS:
        for path in root.rglob("*.py"):
            # If any parent directory name is excluded, skip.
            if any(parent.name in excluded_dir_names for parent in path.parents):
                continue
            files.append(path)
    return files


def imported_modules(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def test_every_epic_source_file_parses_as_python() -> None:
    failures: list[str] = []
    for path in source_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            failures.append(f"{path.relative_to(PROJECT_ROOT)}:{error.lineno}: {error.msg}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize(
    "module_name",
    [
        (
            ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts[:-1])
            if path.name == "__init__.py"
            else ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
        )
        for path in source_files()
    ],
)
def test_all_epic_public_modules_are_importable(module_name: str) -> None:
    """Every EPIC module must be importable from the monorepo package root."""
    importlib.import_module(module_name)


def test_internal_imports_use_the_declared_monorepo_package_roots() -> None:
    violations: list[str] = []
    for path in source_files():
        for line, module in imported_modules(path):
            if module == "infrastructure" or module.startswith("infrastructure."):
                violations.append(
                    f"{path.relative_to(PROJECT_ROOT)}:{line}: {module} must start with libraries.infrastructure"
                )
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize(
    "package_path",
    [
        "shared",
        "libraries/infrastructure",
        "libraries/data",
    ],
)
def test_package_boundaries_have_explicit_python_package_markers(package_path: str) -> None:
    root = PROJECT_ROOT / package_path

    excluded_dir_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".git",
        ".idea",
        ".vscode",
        "build",
        "dist",
    }

    missing = [
        path
        for path in root.rglob("*")
        if path.is_dir()
        and path.name not in excluded_dir_names
        and not (path / "__init__.py").is_file()
    ]
    assert not missing, [str(path.relative_to(PROJECT_ROOT)) for path in missing]
