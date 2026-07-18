"""
Project ORION - Plugin Loader

Plugin discovery and loading system for extensible components.
Supports loading plugins from packages, modules, and entry points.

Provides:
- Plugin discovery (entry points, packages, files)
- Plugin registry
- Plugin validation
- Lifecycle management
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from libraries.infrastructure.logging import get_logger

logger = get_logger("infrastructure.plugin_loader")

T = TypeVar("T")


class PluginError(Exception):
    """Raised when plugin operations fail."""

    pass


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""

    pass


@dataclass
class PluginInfo:
    """Metadata about a loaded plugin."""

    name: str
    module: str
    class_name: str
    version: str = "0.1.0"
    description: str = ""
    dependencies: list[str] = field(default_factory=list)


class PluginBase(ABC):
    """Base class that all plugins must implement."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin."""
        ...

    @property
    def plugin_info(self) -> PluginInfo:
        """Get plugin metadata."""
        return PluginInfo(
            name=self.__class__.__name__,
            module=self.__class__.__module__,
            class_name=self.__class__.__qualname__,
        )


class PluginLoader:
    """
    Loads and manages plugins for the platform.

    Usage:
        loader = PluginLoader()
        loader.discover_entry_points("orion.strategies")
        loader.load("my_strategy")

        for plugin in loader.get_loaded():
            plugin.initialize()
    """

    def __init__(self) -> None:
        self._registry: dict[str, type] = {}
        self._loaded: dict[str, PluginBase] = {}
        self._plugin_info: dict[str, PluginInfo] = {}

    def register(self, name: str, plugin_class: type) -> None:
        """Register a plugin class."""
        self._registry[name] = plugin_class
        logger.debug("Registered plugin: %s", name)

    def discover_package(self, package_name: str) -> list[str]:
        """
        Discover plugins in a Python package.

        Args:
            package_name: Dot-notation package name.

        Returns:
            List of discovered plugin names.
        """
        discovered: list[str] = []
        try:
            package = importlib.import_module(package_name)
            package_path = getattr(package, "__path__", [])
        except ImportError:
            logger.warning("Package not found: %s", package_name)
            return discovered

        for importer, modname, is_pkg in pkgutil.iter_modules(package_path):
            try:
                full_name = f"{package_name}.{modname}"
                module = importlib.import_module(full_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, PluginBase)
                        and obj is not PluginBase
                        and not inspect.isabstract(obj)
                    ):
                        self.register(name, obj)
                        discovered.append(name)

            except Exception as exc:
                logger.error(
                    "Failed to discover plugin in %s: %s",
                    modname,
                    exc,
                )

        return discovered

    def discover_entry_points(self, group: str) -> list[str]:
        """
        Discover plugins via Python package entry points.

        Args:
            group: Entry point group name (e.g., "orion.plugins").

        Returns:
            List of discovered plugin names.
        """
        discovered: list[str] = []
        try:
            for entry_point in entry_points(group=group):
                try:
                    plugin_class = entry_point.load()
                    if inspect.isclass(plugin_class) and issubclass(plugin_class, PluginBase):
                        self.register(entry_point.name, plugin_class)
                        discovered.append(entry_point.name)
                except Exception as exc:
                    logger.error(
                        "Failed to load entry point %s: %s",
                        entry_point.name,
                        exc,
                    )
        except Exception as exc:
            logger.error("Failed to discover entry points for %s: %s", group, exc)

        return discovered

    def discover_directory(self, directory: str | Path) -> list[str]:
        """
        Discover plugins from .py files in a directory.

        Args:
            directory: Path to directory containing plugin files.

        Returns:
            List of discovered plugin names.
        """
        discovered: list[str] = []
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            logger.warning("Plugin directory not found: %s", directory)
            return discovered

        sys.path.insert(0, str(directory.parent))

        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, PluginBase)
                            and obj is not PluginBase
                            and not inspect.isabstract(obj)
                        ):
                            self.register(name, obj)
                            discovered.append(name)

            except Exception as exc:
                logger.error(
                    "Failed to load plugin from %s: %s",
                    file_path,
                    exc,
                )

        sys.path.pop(0)
        return discovered

    def load(self, name: str, **kwargs: Any) -> Optional[PluginBase]:
        """
        Load and instantiate a registered plugin.

        Args:
            name: Plugin name.
            **kwargs: Arguments to pass to plugin constructor.

        Returns:
            Plugin instance or None if loading fails.
        """
        plugin_class = self._registry.get(name)
        if plugin_class is None:
            logger.error("Plugin not registered: %s", name)
            return None

        try:
            instance = plugin_class(**kwargs)
            if not isinstance(instance, PluginBase):
                raise PluginValidationError(f"Plugin {name} does not implement PluginBase")
            self._loaded[name] = instance
            self._plugin_info[name] = instance.plugin_info
            logger.info("Loaded plugin: %s (v%s)", name, instance.plugin_info.version)
            return instance
        except Exception as exc:
            logger.error("Failed to instantiate plugin %s: %s", name, exc)
            return None

    def unload(self, name: str) -> None:
        """Unload a loaded plugin."""
        plugin = self._loaded.pop(name, None)
        if plugin:
            try:
                plugin.shutdown()
            except Exception as exc:
                logger.error("Plugin shutdown error for %s: %s", name, exc)
            logger.info("Unloaded plugin: %s", name)

    def get_loaded(self) -> dict[str, PluginBase]:
        """Get all loaded plugin instances."""
        return self._loaded.copy()

    def get_registered(self) -> dict[str, type]:
        """Get all registered plugin classes."""
        return self._registry.copy()

    def get_plugin_info(self, name: str) -> Optional[PluginInfo]:
        """Get metadata for a loaded plugin."""
        return self._plugin_info.get(name)

    def initialize_all(self) -> list[str]:
        """Initialize all loaded plugins."""
        initialized: list[str] = []
        for name, plugin in self._loaded.items():
            try:
                plugin.initialize()
                initialized.append(name)
            except Exception as exc:
                logger.error("Failed to initialize plugin %s: %s", name, exc)
        return initialized

    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for name in list(self._loaded.keys()):
            self.unload(name)


# ─── Singleton ────────────────────────────────────────────────

_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> PluginLoader:
    """Get the global plugin loader."""
    global _loader
    if _loader is None:
        _loader = PluginLoader()
    return _loader


def reset_plugin_loader() -> None:
    """Reset the plugin loader (for testing)."""
    global _loader
    _loader = None
