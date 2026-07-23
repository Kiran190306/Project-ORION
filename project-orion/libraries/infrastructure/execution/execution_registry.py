"""Execution registry for managing broker adapter lifecycle.

Manages adapter registration, health tracking, lifecycle management,
and integration with the execution router.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from libraries.infrastructure.execution.broker_adapter import BrokerAdapter
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    RoutingTarget,
)


class AdapterHealthStatus(StrEnum):
    """Health status of a registered adapter."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISCONNECTED = "disconnected"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RegisteredAdapter:
    """A registered adapter with its health and routing metadata."""

    adapter: BrokerAdapter
    target: RoutingTarget
    health_status: AdapterHealthStatus = AdapterHealthStatus.UNKNOWN
    health_score: float = 1.0
    last_health_check: datetime | None = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_error: str = ""


@dataclass(frozen=True, slots=True)
class ExecutionRegistryConfig:
    """Configuration for the execution registry."""

    health_check_interval_seconds: float = 30.0
    degraded_health_threshold: float = 0.5
    unhealthy_health_threshold: float = 0.2
    auto_remove_unhealthy: bool = False
    max_unhealthy_age_seconds: float = 300.0


class ExecutionRegistry:
    """Registry managing adapter lifecycle and routing integration.

    Supports:
    - Adapter registration and removal
    - Health tracking and periodic health checks
    - Automatic health-based routing target updates
    - Lifecycle management (connect/disconnect on register/unregister)
    - Integration with ExecutionRouter
    """

    def __init__(
        self,
        router: ExecutionRouter,
        config: ExecutionRegistryConfig | None = None,
    ) -> None:
        self._router = router
        self._config = config or ExecutionRegistryConfig()
        self._adapters: dict[str, RegisteredAdapter] = {}
        self._lock = asyncio.Lock()
        self._health_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def config(self) -> ExecutionRegistryConfig:
        return self._config

    async def start(self) -> None:
        """Start the registry and health check loop."""
        self._running = True
        self._health_task = asyncio.create_task(
            self._health_check_loop(),
            name="execution-registry-health",
        )

    async def stop(self) -> None:
        """Stop the registry and health check loop."""
        self._running = False
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # Disconnect all adapters
        async with self._lock:
            for name, registered in self._adapters.items():
                try:
                    await registered.adapter.disconnect()
                except Exception:
                    pass

    async def register(
        self,
        adapter: BrokerAdapter,
        target: RoutingTarget | None = None,
        auto_connect: bool = True,
    ) -> RegisteredAdapter:
        """Register a broker adapter.

        Args:
            adapter: The broker adapter to register.
            target: Routing metadata (optional).
            auto_connect: Whether to auto-connect the adapter.

        Returns:
            RegisteredAdapter instance.

        Raises:
            ValueError: If an adapter with the same name is already registered.
        """
        name = adapter.broker_name

        async with self._lock:
            if name in self._adapters:
                raise ValueError(f"Adapter '{name}' is already registered")

            if target is None:
                target = RoutingTarget(broker_name=name)

            registered = RegisteredAdapter(
                adapter=adapter,
                target=target,
            )
            self._adapters[name] = registered

        # Register with router
        await self._router.register_adapter(adapter, target)

        # Auto-connect if requested
        if auto_connect:
            try:
                await adapter.connect()
                async with self._lock:
                    self._adapters[name] = RegisteredAdapter(
                        adapter=adapter,
                        target=target,
                        health_status=AdapterHealthStatus.HEALTHY,
                        health_score=1.0,
                        last_health_check=datetime.now(timezone.utc),
                        registered_at=registered.registered_at,
                    )
            except Exception as e:
                async with self._lock:
                    self._adapters[name] = RegisteredAdapter(
                        adapter=adapter,
                        target=target,
                        health_status=AdapterHealthStatus.DISCONNECTED,
                        last_error=str(e),
                        registered_at=registered.registered_at,
                    )

        return registered

    async def unregister(self, broker_name: str) -> bool:
        """Unregister a broker adapter.

        Args:
            broker_name: Name of the adapter to unregister.

        Returns:
            True if successfully unregistered.
        """
        async with self._lock:
            registered = self._adapters.pop(broker_name, None)
            if registered is None:
                return False

        # Unregister from router
        await self._router.unregister_adapter(broker_name)

        # Disconnect adapter
        try:
            await registered.adapter.disconnect()
        except Exception:
            pass

        return True

    async def get_adapter(self, broker_name: str) -> BrokerAdapter | None:
        """Get a registered adapter by name.

        Args:
            broker_name: Name of the adapter.

        Returns:
            BrokerAdapter if found, None otherwise.
        """
        async with self._lock:
            registered = self._adapters.get(broker_name)
            return registered.adapter if registered else None

    async def get_registered(self, broker_name: str) -> RegisteredAdapter | None:
        """Get registered adapter metadata.

        Args:
            broker_name: Name of the adapter.

        Returns:
            RegisteredAdapter if found, None otherwise.
        """
        async with self._lock:
            return self._adapters.get(broker_name)

    async def get_all_registered(self) -> list[RegisteredAdapter]:
        """Get all registered adapters with their metadata.

        Returns:
            List of RegisteredAdapter instances.
        """
        async with self._lock:
            return list(self._adapters.values())

    async def update_health(
        self,
        broker_name: str,
        health_score: float,
        status: AdapterHealthStatus | None = None,
        error: str = "",
    ) -> None:
        """Update health status for a registered adapter.

        Args:
            broker_name: Name of the adapter.
            health_score: Health score (0.0 to 1.0).
            status: Health status (auto-derived if not provided).
            error: Error message if unhealthy.
        """
        async with self._lock:
            registered = self._adapters.get(broker_name)
            if registered is None:
                return

            if status is None:
                if health_score >= 0.8:
                    status = AdapterHealthStatus.HEALTHY
                elif health_score >= self._config.degraded_health_threshold:
                    status = AdapterHealthStatus.DEGRADED
                else:
                    status = AdapterHealthStatus.UNHEALTHY

            self._adapters[broker_name] = RegisteredAdapter(
                adapter=registered.adapter,
                target=registered.target,
                health_status=status,
                health_score=health_score,
                last_health_check=datetime.now(timezone.utc),
                registered_at=registered.registered_at,
                last_error=error,
            )

        # Update router health
        await self._router.update_health(broker_name, health_score)

    async def adapter_count(self) -> int:
        """Return the number of registered adapters."""
        async with self._lock:
            return len(self._adapters)

    async def _health_check_loop(self) -> None:
        """Periodic health check for all registered adapters."""
        while self._running:
            await asyncio.sleep(self._config.health_check_interval_seconds)

            async with self._lock:
                adapters = dict(self._adapters)

            for name, registered in adapters.items():
                try:
                    health = await registered.adapter.health_check()
                    is_connected = health.get("connected", False)
                    health_score = 1.0 if is_connected else 0.0

                    await self.update_health(
                        name,
                        health_score=health_score,
                        error="" if is_connected else "Not connected",
                    )
                except Exception as e:
                    await self.update_health(
                        name,
                        health_score=0.0,
                        status=AdapterHealthStatus.DISCONNECTED,
                        error=str(e),
                    )

