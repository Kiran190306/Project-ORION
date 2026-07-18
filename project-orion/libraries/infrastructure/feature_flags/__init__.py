"""
Project ORION - Feature Flags

Feature flag system for gradual rollout and environment-specific features.
Supports percentage-based rollouts, user targeting, and environment gating.

Provides:
- Boolean feature flags
- Percentage-based rollouts
- Environment-specific flags
- User targeting
- Flag evaluation
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from libraries.infrastructure.environment import Environment, get_environment
from libraries.infrastructure.logging import get_logger

logger = get_logger("infrastructure.feature_flags")


class FlagStatus(str, Enum):
    """Status of a feature flag."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    CONDITIONAL = "conditional"


@dataclass
class FeatureFlag:
    """Definition of a feature flag."""

    name: str
    description: str = ""
    status: FlagStatus = FlagStatus.DISABLED
    enabled_environments: list[Environment] = field(default_factory=list)
    rollout_percentage: int = 0
    enabled_users: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def is_enabled(
        self,
        environment: Optional[Environment] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Check if this feature flag is enabled.

        Args:
            environment: Current environment (uses detected if None).
            user_id: Optional user ID for targeted rollouts.

        Returns:
            True if the feature is enabled.
        """
        if self.status == FlagStatus.ENABLED:
            return True

        if self.status == FlagStatus.DISABLED:
            return False

        # Conditional: check environment
        env = environment or get_environment()
        if self.enabled_environments and env in self.enabled_environments:
            return True

        # Conditional: check user targeting
        if user_id and user_id in self.enabled_users:
            return True

        # Conditional: check rollout percentage
        if self.rollout_percentage > 0 and user_id:
            hash_input = f"{self.name}:{user_id}"
            # Deterministic bucketing hash. This is NOT for security purposes.
            user_hash = int(
                hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:8],
                16,
            )

            if (user_hash % 100) < self.rollout_percentage:
                return True

        return False


class FeatureFlagManager:
    """
    Manages feature flags for the application.

    Usage:
        manager = FeatureFlagManager()
        manager.register(FeatureFlag("new-dashboard", status=FlagStatus.ENABLED))

        if manager.is_enabled("new-dashboard"):
            # show new dashboard
    """

    def __init__(self) -> None:
        self._flags: dict[str, FeatureFlag] = {}

    def register(self, flag: FeatureFlag) -> FeatureFlag:
        """Register a feature flag."""
        self._flags[flag.name] = flag
        return flag

    def register_from_dict(self, data: dict[str, Any]) -> None:
        """Register flags from a dictionary."""
        for name, config in data.items():
            flag = FeatureFlag(
                name=name,
                description=config.get("description", ""),
                status=FlagStatus(config.get("status", "disabled")),
                enabled_environments=[
                    Environment(e) for e in config.get("environments", [])
                ],
                rollout_percentage=config.get("rollout_percentage", 0),
                enabled_users=config.get("enabled_users", []),
                dependencies=config.get("dependencies", []),
            )
            self.register(flag)

    def register_from_file(self, path: str | Path) -> None:
        """Register flags from a JSON file."""
        path = Path(path)
        if not path.exists():
            logger.warning("Feature flags file not found: %s", path)
            return

        data = json.loads(path.read_text(encoding="utf-8"))
        self.register_from_dict(data)

    def is_enabled(
        self,
        flag_name: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag_name: Name of the feature flag.
            user_id: Optional user ID for targeted rollouts.

        Returns:
            True if the feature is enabled.

        Raises:
            KeyError: If flag is not registered.
        """
        flag = self._flags.get(flag_name)
        if flag is None:
            raise KeyError(f"Feature flag '{flag_name}' not registered")

        # Check dependencies
        for dep_name in flag.dependencies:
            if not self.is_enabled(dep_name, user_id):
                return False

        return flag.is_enabled(environment=get_environment(), user_id=user_id)

    def enable(self, flag_name: str) -> None:
        """Force enable a feature flag."""
        flag = self._flags.get(flag_name)
        if flag:
            flag.status = FlagStatus.ENABLED

    def disable(self, flag_name: str) -> None:
        """Force disable a feature flag."""
        flag = self._flags.get(flag_name)
        if flag:
            flag.status = FlagStatus.DISABLED

    def get_all_flags(self) -> dict[str, dict[str, Any]]:
        """Get all registered flags with their status."""
        env = get_environment()
        return {
            name: {
                "name": flag.name,
                "description": flag.description,
                "status": flag.status.value,
                "enabled": flag.is_enabled(environment=env),
            }
            for name, flag in self._flags.items()
        }

    def clear(self) -> None:
        """Clear all registered flags."""
        self._flags.clear()


# ─── Singleton ────────────────────────────────────────────────

_manager: Optional[FeatureFlagManager] = None


def get_feature_flags() -> FeatureFlagManager:
    """Get the global feature flag manager."""
    global _manager
    if _manager is None:
        _manager = FeatureFlagManager()
    return _manager


def reset_feature_flags() -> None:
    """Reset the feature flag manager (for testing)."""
    global _manager
    _manager = None
