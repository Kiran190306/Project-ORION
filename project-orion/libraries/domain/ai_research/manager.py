"""Manager for the AI research platform lifecycle.

Responsibilities:
    - Lifecycle management (initialize, shutdown, reset)
    - Configuration validation
    - Dependency injection for engine construction
    - Health checks
    - Shutdown coordination
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from libraries.domain.ai_research.engine import AIResearchEngine
from libraries.domain.ai_research.exceptions import (
    AIResearchError,
    ConfigurationError,
)
from libraries.domain.ai_research.models import PlatformState, ResearchPlatformConfig


class AIResearchManager:
    """Manages the AI research platform lifecycle.

    Owns startup, shutdown, health checks, and state management.
    Delegates research execution to the injected AIResearchEngine.
    """

    def __init__(
        self,
        config: ResearchPlatformConfig | None = None,
        engine: AIResearchEngine | None = None,
    ) -> None:
        self._config = config or ResearchPlatformConfig()
        self._engine = engine
        self._state = PlatformState.INITIALIZING
        self._start_time: datetime | None = None

    @property
    def state(self) -> PlatformState:
        return self._state

    @property
    def config(self) -> ResearchPlatformConfig:
        return self._config

    @property
    def engine(self) -> AIResearchEngine | None:
        return self._engine

    async def initialize(self) -> None:
        """Initialize the platform.

        Validates configuration and transitions to READY state.
        """
        if self._state != PlatformState.INITIALIZING:
            raise AIResearchError(f"Cannot initialize from state: {self._state.value}")

        self._validate_configuration()
        self._state = PlatformState.READY
        self._start_time = datetime.now(timezone.utc)

    async def shutdown(self) -> None:
        """Shutdown the platform gracefully."""
        if self._state == PlatformState.SHUTDOWN:
            raise AIResearchError("Already shut down")
        self._state = PlatformState.SHUTDOWN
        self._engine = None

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check.

        Returns:
            Health check result with state, uptime, and engine status.
        """
        uptime = None
        if self._start_time and self._state == PlatformState.READY:
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        return {
            "state": self._state.value,
            "uptime_seconds": uptime,
            "is_healthy": self._state == PlatformState.READY,
            "engine_configured": self._engine is not None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def reset(self) -> None:
        """Reset platform to initial state."""
        self._state = PlatformState.INITIALIZING
        self._start_time = None

    def _validate_configuration(self) -> None:
        """Validate the platform configuration.

        Raises ConfigurationError if validation fails.
        """
        if self._config.random_seed is not None and (
            not isinstance(self._config.random_seed, int)
            or isinstance(self._config.random_seed, bool)
        ):
            raise ConfigurationError("random_seed must be an integer")
        if not self._config.name or not isinstance(self._config.name, str):
            raise ConfigurationError("platform name must be a non-empty string")
        if not self._config.name.strip():
            raise ConfigurationError("platform name must be a non-empty string")
