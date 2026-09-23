#!/usr/bin/env python3
"""Project ORION — Production Database Migration Runner (EPIC-027 Phase 6B).

Deterministic, fail-fast CLI migration runner designed for Render PaaS preDeployCommand
and standalone CI/CD deployment pipelines.

Safety Invariants:
- Strictly executes forward migrations: `alembic upgrade head`.
- Never performs destructive drop/reset operations.
- Never performs downgrade during deployment.
- Exits with code 1 immediately upon any migration error to halt deployment.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Configure structured logging for deployment logs
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [deploy.migrate] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("deploy.migrate")


def resolve_project_root() -> Path:
    """Resolve the Project ORION repository root directory."""
    # scripts/deploy/migrate.py -> parents[2] is project-orion root
    current = Path(__file__).resolve()
    candidate = current.parents[2]
    if (candidate / "alembic.ini").exists():
        return candidate
    # Fallback to current working directory
    cwd = Path.cwd()
    if (cwd / "alembic.ini").exists():
        return cwd
    return candidate


def resolve_database_url(cli_url: str | None = None) -> str:
    """Resolve target database URL with environment variable fallbacks."""
    url = (
        cli_url
        or os.environ.get("ORION_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
    )
    if not url:
        logger.error(
            "CRITICAL: No database URL provided. Set ORION_DATABASE_URL or DATABASE_URL."
        )
        sys.exit(1)

    # Normalize PostgreSQL URL for asyncpg driver if standard postgres:// is supplied
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


def run_migrations(database_url: str, check_only: bool = False) -> int:
    """Execute Alembic upgrade head or verify configuration.

    Args:
        database_url: Target database connection string.
        check_only: If True, inspect heads without executing DDL.

    Returns:
        0 on success, non-zero on failure.
    """
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError as err:
        logger.error("Failed to import Alembic: %s. Is Alembic installed?", err)
        return 1

    project_root = resolve_project_root()
    ini_path = project_root / "alembic.ini"
    migrations_dir = project_root / "database" / "migrations"

    if not ini_path.exists():
        logger.error("Alembic configuration not found at: %s", ini_path)
        return 1

    logger.info("Project root resolved: %s", project_root)
    logger.info("Alembic INI location: %s", ini_path)

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.set_main_option("script_location", str(migrations_dir))

    # Inspect migration chain heads
    try:
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        heads = script_dir.get_heads()
        logger.info("Alembic script directory verified. Expected target head(s): %s", heads)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse Alembic script directory: %s", exc)
        return 1

    if check_only:
        logger.info("CHECK-ONLY mode: Migration configuration and heads verified successfully.")
        return 0

    # Execute forward migrations to head
    start_time = time.monotonic()
    # Mask credentials for logging
    masked_url = database_url
    if "@" in masked_url:
        prefix, host_part = masked_url.rsplit("@", 1)
        scheme_user = prefix.split("://")[0] + "://***"
        masked_url = f"{scheme_user}@{host_part}"
    logger.info("Beginning database migration execution against: %s", masked_url)

    try:
        command.upgrade(alembic_cfg, "head")
        duration = round(time.monotonic() - start_time, 2)
        logger.info(
            "SUCCESS: Database migrations applied successfully to head(s) %s in %ss.",
            heads,
            duration,
        )
        return 0
    except Exception:
        duration = round(time.monotonic() - start_time, 2)
        logger.exception(
            "CRITICAL: Database migration execution FAILED after %ss",
            duration,
        )
        return 1


def main() -> None:
    """CLI entrypoint for standalone migration execution."""
    parser = argparse.ArgumentParser(
        description="Project ORION Deterministic Production Migration Runner"
    )
    parser.add_argument(
        "--database-url",
        help="Target database URL (defaults to ORION_DATABASE_URL or DATABASE_URL env var)",
        default=None,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check configuration and target heads without applying DDL",
    )

    args = parser.parse_args()

    # For --check mode, database URL can use a dummy SQLite fallback if none provided
    if args.check and not (args.database_url or os.environ.get("ORION_DATABASE_URL") or os.environ.get("DATABASE_URL")):
        db_url = "sqlite+aiosqlite:///:memory:"
    else:
        db_url = resolve_database_url(args.database_url)

    exit_code = run_migrations(db_url, check_only=args.check)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
