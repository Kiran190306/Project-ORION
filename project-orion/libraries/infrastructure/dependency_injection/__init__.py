"""
Project ORION - Dependency Injection Container

Lightweight dependency injection container for service wiring.
Supports singleton, transient, and factory lifetimes.

Provides:
- Service registration (singleton, transient, factory)
- Auto-wiring via type hints
- Lazy initialization
- Scoped/lifetime management
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, cast

T = TypeVar("T")


class ServiceLifetime(str, Enum):
    """Lifetime of a registered service."""

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    FACTORY = "factory"


@dataclass
class ServiceRegistration:
    """Registration metadata for a service."""

    interface: type
    implementation: type
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    factory: Optional[Callable[..., Any]] = None
    instance: Any = None


class DependencyInjectionError(Exception):
    """Raised when dependency injection fails."""

    pass


class Container:
    """
    Dependency injection container.

    Usage:
        container = Container()
        container.register(DatabaseInterface, PostgresDatabase, ServiceLifetime.SINGLETON)
        container.register_instance(Config, config)

        service = container.resolve(DatabaseInterface)
    """

    def __init__(self) -> None:
        self._registrations: dict[type, ServiceRegistration] = {}
        self._instances: dict[type, Any] = {}

    def register(
        self,
        interface: type[T],
        implementation: type,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ) -> None:
        """
        Register a service implementation.

        Args:
            interface: The abstract type to register.
            implementation: The concrete implementation class.
            lifetime: Service lifetime (singleton, transient, factory).
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime,
        )

    def register_instance(self, interface: type[T], instance: T) -> None:
        """
        Register a pre-created instance.

        Args:
            interface: The type to register.
            instance: The instance to register.
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=type(instance),
            lifetime=ServiceLifetime.SINGLETON,
            instance=instance,
        )
        self._instances[interface] = instance

    def register_factory(
        self,
        interface: type[T],
        factory: Callable[..., T],
    ) -> None:
        """
        Register a factory function.

        Args:
            interface: The type to register.
            factory: Factory function that creates instances.
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=type,
            lifetime=ServiceLifetime.FACTORY,
            factory=factory,
        )

    def resolve(self, interface: type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            interface: The type to resolve.

        Returns:
            Resolved service instance.

        Raises:
            DependencyInjectionError: If resolution fails.
        """
        registration = self._registrations.get(interface)
        if registration is None:
            raise DependencyInjectionError(f"No registration for: {interface.__name__}")

        # Singleton: return cached instance or create
        if registration.lifetime == ServiceLifetime.SINGLETON:
            if interface in self._instances:
                return cast(T, self._instances[interface])
            instance = self._create_instance(registration)
            self._instances[interface] = instance
            return cast(T, instance)

        # Transient: always create new
        if registration.lifetime == ServiceLifetime.TRANSIENT:
            return cast(T, self._create_instance(registration))

        # Factory: call factory function
        if registration.lifetime == ServiceLifetime.FACTORY:
            if registration.factory:
                return cast(T, registration.factory())

        raise DependencyInjectionError(
            f"Cannot resolve {interface.__name__}: invalid registration"
        )

    def has(self, interface: type) -> bool:
        """Check if a service is registered."""
        return interface in self._registrations

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._registrations.clear()
        self._instances.clear()

    def _create_instance(self, registration: ServiceRegistration) -> Any:
        """Create an instance using constructor injection."""
        impl = registration.implementation
        try:
            # Get constructor signature
            # Inspect the class callable rather than its instance attribute.
            # An implementation subclass may supply an incompatible __init__.
            sig = inspect.signature(impl)
            params = list(sig.parameters.values())[1:]  # Skip self

            # Resolve constructor parameters
            kwargs: dict[str, Any] = {}
            for param in params:
                if param.annotation is not inspect.Parameter.empty:
                    try:
                        kwargs[param.name] = self.resolve(param.annotation)
                    except DependencyInjectionError:
                        if param.default is not inspect.Parameter.empty:
                            kwargs[param.name] = param.default
                        else:
                            raise

            return impl(**kwargs)
        except Exception as exc:
            raise DependencyInjectionError(
                f"Failed to create instance of {impl.__name__}: {exc}"
            ) from exc


# ─── Singleton Container ──────────────────────────────────────

container: Container = Container()
"""Global dependency injection container."""
