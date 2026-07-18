"""
Project ORION - Settings Management

Centralized settings system with environment variable loading,
type coercion, validation, and hierarchical configuration.

Supports:
- Environment variable loading (.env files)
- Type coercion (int, float, bool, str, list, dict)
- Nested configuration via dot notation
- Default values
- Validation constraints
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union, cast

from libraries.infrastructure.environment import Environment, get_environment

T = TypeVar("T")


class SettingsError(Exception):
    """Raised when settings loading or validation fails."""

    pass


class SettingNotFoundError(SettingsError):
    """Raised when a requested setting is not found."""

    pass


class SettingValidationError(SettingsError):
    """Raised when a setting fails validation."""

    pass


@dataclass
class SettingDefinition:
    """Definition of a single configuration setting."""

    key: str
    default: Any = None
    description: str = ""
    required: bool = False
    env_var: Optional[str] = None
    validator: Optional[Callable[[Any], bool]] = None
    type_cast: Optional[Callable[[str], Any]] = None
    secret: bool = False


class Settings:
    """
    Hierarchical settings container with environment variable support.

    Supports dot-notation access (e.g., settings.database.host)
    and environment variable overrides.

    Usage:
        settings = Settings()
        settings.load_from_env("ORION_")
        db_host = settings.get("database.host", "localhost")
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._definitions: dict[str, SettingDefinition] = {}
        self._loaded = False
        self._environment = get_environment()

    def define(self, definition: SettingDefinition) -> SettingDefinition:
        """Register a setting definition."""
        self._definitions[definition.key] = definition
        return definition

    def load_from_env(
        self,
        prefix: str = "ORION_",
        separator: str = "__",
    ) -> None:
        """
        Load settings from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., "ORION_").
            separator: Separator for nested keys (e.g., "__" for DATABASE__HOST).
        """
        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Convert env var name to config key
            config_key = env_key[len(prefix) :].lower().replace(separator, ".")
            self._set_nested(config_key, self._coerce_value(config_key, env_value))

        self._loaded = True

    def load_from_dict(self, data: dict[str, Any], prefix: str = "") -> None:
        """Load settings from a dictionary, optionally with a key prefix."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self.load_from_dict(value, full_key)
            else:
                self._set_nested(full_key, value)
        self._loaded = True

    def load_from_file(self, path: Union[str, Path]) -> None:
        """
        Load settings from a JSON or YAML file.

        Args:
            path: Path to configuration file.

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If JSON is malformed.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Settings file not found: {path}")

        content = path.read_text(encoding="utf-8")
        if path.suffix in (".json",):
            data = json.loads(content)
            self.load_from_dict(data)
        elif path.suffix in (".yaml", ".yml"):
            try:
                import yaml

                data = yaml.safe_load(content)
                self.load_from_dict(data)
            except ImportError:
                raise SettingsError(
                    "PyYAML is required to load YAML settings files. "
                    "Install with: pip install pyyaml"
                )
        else:
            raise SettingsError(f"Unsupported settings file format: {path.suffix}")

    def get(self, key: str, default: Optional[T] = None) -> T:
        """
        Get a setting value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., "database.host").
            default: Default value if key is not found.

        Returns:
            Setting value.

        Raises:
            SettingNotFoundError: If key not found and no default.
        """
        parts = key.split(".")
        current: Any = self._data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    break
            else:
                current = None
                break

        if current is not None:
            return cast(T, current)

        # Check definition default
        definition = self._definitions.get(key)
        if definition is not None and definition.default is not None:
            return cast(T, definition.default)

        if default is not None:
            return default

        if definition is not None and definition.required:
            raise SettingNotFoundError(f"Required setting '{key}' is not configured")

        return cast(T, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._set_nested(key, value)

    def has(self, key: str) -> bool:
        """Check if a setting exists."""
        try:
            self.get(key)
            return True
        except SettingNotFoundError:
            return False

    def all(self) -> dict[str, Any]:
        """Get all settings as a flat dictionary."""
        return self._flatten(self._data)

    def to_dict(self) -> dict[str, Any]:
        """Get all settings as a nested dictionary."""
        return self._data.copy()

    def validate(self) -> list[str]:
        """
        Validate all required settings are present.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []
        for definition in self._definitions.values():
            try:
                value: Any = self.get(definition.key)
                if definition.validator and not definition.validator(value):
                    errors.append(f"Setting '{definition.key}' failed validation")
            except SettingNotFoundError:
                if definition.required:
                    errors.append(f"Required setting '{definition.key}' is missing")
        return errors

    def _set_nested(self, key: str, value: Any) -> None:
        """Set a value using dot notation, creating intermediate dicts."""
        parts = key.split(".")
        current: dict[str, Any] = self._data
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = cast(dict[str, Any], child)
        current[parts[-1]] = value

    def _get_nested(self, key: str) -> Any:
        """Get a value using dot notation."""
        parts = key.split(".")
        current: Any = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            else:
                return None
        return current

    def _coerce_value(self, key: str, value: str) -> Any:
        """Coerce a string value to its proper type."""
        definition = self._definitions.get(key)
        if definition and definition.type_cast:
            try:
                return definition.type_cast(value)
            except (ValueError, TypeError):
                pass

        # Auto-coercion
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _flatten(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dictionary to dot-notation keys."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten(value, full_key))
            else:
                result[full_key] = value
        return result


# ─── Singleton Instance ───────────────────────────────────────

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.load_from_env()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (for testing)."""
    global _settings
    _settings = None


# ─── Common Setting Definitions ──────────────────────────────


def define_common_settings(settings: Settings) -> None:
    """Define common standard settings."""
    settings.define(
        SettingDefinition(
            key="app.name",
            default="project-orion",
            description="Application name",
        )
    )
    settings.define(
        SettingDefinition(
            key="app.version",
            default="0.1.0",
            description="Application version",
        )
    )
    settings.define(
        SettingDefinition(
            key="app.debug",
            default=False,
            description="Debug mode flag",
            env_var="ORION_APP__DEBUG",
            type_cast=lambda v: v.lower() in ("true", "1", "yes"),
        )
    )
    settings.define(
        SettingDefinition(
            key="logging.level",
            default="INFO",
            description="Logging level",
            validator=lambda v: v in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        )
    )
    settings.define(
        SettingDefinition(
            key="logging.format",
            default="json",
            description="Log output format (json or text)",
        )
    )
    settings.define(
        SettingDefinition(
            key="database.url",
            required=True,
            description="Database connection URL",
            env_var="ORION_DATABASE_URL",
            secret=True,
        )
    )
    settings.define(
        SettingDefinition(
            key="database.pool_size",
            default=10,
            description="Database connection pool size",
            type_cast=int,
        )
    )
    settings.define(
        SettingDefinition(
            key="redis.url",
            default="redis://localhost:6379/0",
            description="Redis connection URL",
            secret=True,
        )
    )
    settings.define(
        SettingDefinition(
            key="kafka.bootstrap_servers",
            default="localhost:9092",
            description="Kafka bootstrap servers",
        )
    )
    settings.define(
        SettingDefinition(
            key="server.host",
            default="0.0.0.0",
            description="Server bind host",
        )
    )
    settings.define(
        SettingDefinition(
            key="server.port",
            default=8000,
            description="Server bind port",
            type_cast=int,
        )
    )
    settings.define(
        SettingDefinition(
            key="server.workers",
            default=1,
            description="Number of worker processes",
            type_cast=int,
        )
    )
