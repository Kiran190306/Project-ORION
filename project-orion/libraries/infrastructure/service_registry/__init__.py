"""
Project ORION - Service Registry

Service registration and discovery for microservice architecture.
Supports service metadata, health tracking, and discovery.

Provides:
- Service registration
- Service discovery (by name, type)
- Health tracking
- Service metadata
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from libraries.infrastructure.logging import get_logger

logger = get_logger("infrastructure.service_registry")


class ServiceStatus(str, Enum):
    """Status of a registered service."""

    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ServiceInstance:
    """A registered service instance."""

    service_id: str
    service_name: str
    service_type: str
    version: str = "0.1.0"
    host: str = "localhost"
    port: int = 0
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: dict[str, Any] = field(default_factory=dict)
    registered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    health_endpoint: str = ""

    @property
    def address(self) -> str:
        """Get service address (host:port)."""
        return f"{self.host}:{self.port}" if self.port else self.host

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "version": self.version,
            "address": self.address,
            "status": self.status.value,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
        }


class ServiceRegistry:
    """
    In-memory service registry for service discovery.

    Usage:
        registry = ServiceRegistry()
        registry.register(ServiceInstance(
            service_id="market-data-1",
            service_name="market-data",
            service_type="data",
            port=50051,
        ))

        instances = registry.discover("market-data")
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceInstance] = {}
        self._service_types: dict[str, list[str]] = {}

    def register(self, instance: ServiceInstance) -> ServiceInstance:
        """Register a service instance."""
        existing = self._services.get(instance.service_id)
        if existing is not None and existing.service_type != instance.service_type:
            previous_type = self._service_types.get(existing.service_type, [])
            if instance.service_id in previous_type:
                previous_type.remove(instance.service_id)
        self._services[instance.service_id] = instance

        if instance.service_type not in self._service_types:
            self._service_types[instance.service_type] = []
        if instance.service_id not in self._service_types[instance.service_type]:
            self._service_types[instance.service_type].append(instance.service_id)

        logger.info(
            "Registered service: %s (%s) at %s",
            instance.service_name,
            instance.service_id,
            instance.address,
        )
        return instance

    def unregister(self, service_id: str) -> None:
        """Unregister a service instance."""
        instance = self._services.pop(service_id, None)
        if instance:
            type_list = self._service_types.get(instance.service_type, [])
            if service_id in type_list:
                type_list.remove(service_id)
            logger.info(
                "Unregistered service: %s (%s)",
                instance.service_name,
                service_id,
            )

    def get(self, service_id: str) -> Optional[ServiceInstance]:
        """Get a service instance by ID."""
        return self._services.get(service_id)

    def discover(
        self,
        service_name: Optional[str] = None,
        service_type: Optional[str] = None,
        status: Optional[ServiceStatus] = None,
    ) -> list[ServiceInstance]:
        """
        Discover service instances matching criteria.

        Args:
            service_name: Filter by service name.
            service_type: Filter by service type.
            status: Filter by service status.

        Returns:
            List of matching service instances.
        """
        results: list[ServiceInstance] = []

        for instance in self._services.values():
            if service_name and instance.service_name != service_name:
                continue
            if service_type and instance.service_type != service_type:
                continue
            if status and instance.status != status:
                continue
            results.append(instance)

        return results

    def get_all(self) -> list[ServiceInstance]:
        """Get all registered services."""
        return list(self._services.values())

    def get_by_type(self, service_type: str) -> list[ServiceInstance]:
        """Get all services of a specific type."""
        return self.discover(service_type=service_type)

    def heartbeat(self, service_id: str) -> bool:
        """Update a service's heartbeat timestamp."""
        instance = self._services.get(service_id)
        if instance:
            instance.last_heartbeat = datetime.utcnow().isoformat()
            instance.status = ServiceStatus.RUNNING
            return True
        return False

    def check_stale_services(
        self,
        timeout_seconds: float = 30.0,
    ) -> list[str]:
        """
        Check for stale services that haven't sent heartbeats.

        Args:
            timeout_seconds: Maximum time since last heartbeat.

        Returns:
            List of stale service IDs.
        """
        now = time.time()
        stale: list[str] = []

        for service_id, instance in self._services.items():
            try:
                heartbeat_time = datetime.fromisoformat(instance.last_heartbeat).timestamp()
                if now - heartbeat_time > timeout_seconds:
                    instance.status = ServiceStatus.DEGRADED
                    stale.append(service_id)
            except (ValueError, TypeError):
                stale.append(service_id)

        return stale

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all registered services."""
        total = len(self._services)
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}

        for instance in self._services.values():
            by_status[instance.status.value] = by_status.get(instance.status.value, 0) + 1
            by_type[instance.service_type] = by_type.get(instance.service_type, 0) + 1

        return {
            "total_services": total,
            "by_status": by_status,
            "by_type": by_type,
            "services": [s.to_dict() for s in self._services.values()],
        }

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._service_types.clear()
        logger.info("Service registry cleared")


# ─── Singleton ────────────────────────────────────────────────

_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def reset_service_registry() -> None:
    """Reset the service registry (for testing)."""
    global _registry
    _registry = None
