"""Unit tests for Alembic migration configuration, environment, and DDL execution."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


@pytest.fixture
def alembic_config(tmp_path: Path) -> Config:
    """Fixture providing an Alembic Config pointing to project root and a temporary SQLite DB."""
    project_root = Path(__file__).resolve().parents[4]
    ini_path = project_root / "alembic.ini"
    db_path = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    config = Config(str(ini_path))
    config.set_main_option("sqlalchemy.url", db_url)
    config.set_main_option("script_location", str(project_root / "database" / "migrations"))
    return config


def test_alembic_script_directory(alembic_config: Config) -> None:
    """Verify Alembic script directory discovers initial schema revision."""
    script_dir = ScriptDirectory.from_config(alembic_config)
    revisions = list(script_dir.walk_revisions())
    assert len(revisions) >= 1
    assert revisions[-1].revision == "0001_initial_schema"


def test_alembic_upgrade_and_downgrade_lifecycle(alembic_config: Config) -> None:
    """Test running upgrade head and downgrade base against a fresh database."""
    # Run full migration to head
    command.upgrade(alembic_config, "head")

    # Revert migration to base
    command.downgrade(alembic_config, "base")

    # Re-apply migration to ensure idempotency and cleanliness
    command.upgrade(alembic_config, "head")
