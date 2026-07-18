"""
Project ORION - Environment Management

Centralized environment detection and management.
Supports multiple deployment environments with consistent API.

Provides:
- Environment enum (development, staging, production, test)
- Environment detection (env vars, files)
- Feature gating based on environment
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"

    @property
    def is_development(self) -> bool:
        return self == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        return self == Environment.STAGING

    @property
    def is_production(self) -> bool:
        return self == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self == Environment.TEST

    @property
    def is_local(self) -> bool:
        """Check if running in a local/dev environment."""
        return self in (Environment.DEVELOPMENT, Environment.TEST)

    @property
    def is_deployed(self) -> bool:
        """Check if running in a deployed (non-local) environment."""
        return self in (Environment.STAGING, Environment.PRODUCTION)


_ENVIRONMENT_VAR = "ORION_ENV"
_DEFAULT_ENVIRONMENT = Environment.DEVELOPMENT

_environment: Optional[Environment] = None


def get_environment() -> Environment:
    """
    Get the current deployment environment.

    Detection order:
    1. ORION_ENV environment variable
    2. .environment file content
    3. Default (development)

    Returns:
        Current Environment value.
    """
    global _environment
    if _environment is not None:
        return _environment

    # 1. Check environment variable
    env_str = os.environ.get(_ENVIRONMENT_VAR, "").lower()
    if env_str:
        for env in Environment:
            if env.value == env_str:
                _environment = env
                return _environment

    # 2. Check .environment file
    try:
        with open(".environment", "r", encoding="utf-8") as f:
            env_str = f.read().strip().lower()
            for env in Environment:
                if env.value == env_str:
                    _environment = env
                    return _environment
    except (FileNotFoundError, IOError):
        pass

    # 3. Default
    _environment = _DEFAULT_ENVIRONMENT
    return _environment


def set_environment(env: Environment) -> None:
    """
    Explicitly set the environment (primarily for testing).

    Args:
        env: Environment to set.
    """
    global _environment
    _environment = env


def is_environment(env: Environment) -> bool:
    """Check if the current environment matches the given one."""
    return get_environment() == env


def require_environment(*allowed: Environment) -> None:
    """
    Require that the current environment is one of the allowed ones.
    Raises RuntimeError if not.

    Args:
        *allowed: Allowed environment values.

    Raises:
        RuntimeError: If current environment is not in allowed list.
    """
    current = get_environment()
    if current not in allowed:
        allowed_names = ", ".join(e.value for e in allowed)
        raise RuntimeError(
            f"Environment '{current.value}' not allowed. "
            f"Must be one of: {allowed_names}"
        )


def reset_environment() -> None:
    """Reset cached environment (for testing)."""
    global _environment
    _environment = None
