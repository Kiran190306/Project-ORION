"""Public-contract tests for EPIC-003 core-platform infrastructure."""

from __future__ import annotations

import asyncio
import importlib
from typing import Any

import pytest


def load(module_name: str) -> Any:
    """Import lazily so unrelated quality checks still execute on failure."""
    return importlib.import_module(module_name)


def test_environment_configuration_is_cached_resettable_and_guarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = load("libraries.infrastructure.environment")
    monkeypatch.setenv("ORION_ENV", "test")
    environment.reset_environment()

    assert environment.get_environment() is environment.Environment.TEST
    environment.require_environment(environment.Environment.TEST)
    with pytest.raises(RuntimeError, match="not allowed"):
        environment.require_environment(environment.Environment.PRODUCTION)


def test_settings_load_environment_nested_configuration_and_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_module = load("libraries.infrastructure.settings")
    environment = load("libraries.infrastructure.environment")
    environment.set_environment(environment.Environment.TEST)
    settings = settings_module.Settings()
    settings.define(
        settings_module.SettingDefinition("service.port", default=8080, type_cast=int)
    )
    monkeypatch.setenv("ORION_SERVICE__PORT", "9090")

    settings.load_from_env()
    settings.load_from_dict({"service": {"name": "market-data"}})

    assert settings.get("service.port") == 9090
    assert settings.get("service.name") == "market-data"
    assert settings.validate() == []


def test_service_registry_lifecycle_discovery_and_staleness() -> None:
    registry_module = load("libraries.infrastructure.service_registry")
    registry = registry_module.ServiceRegistry()
    instance = registry_module.ServiceInstance(
        service_id="market-1",
        service_name="market-data",
        service_type="data",
        port=8080,
    )

    registry.register(instance)
    assert registry.discover(service_type="data") == [instance]
    assert registry.heartbeat("market-1")
    assert instance.status is registry_module.ServiceStatus.RUNNING
    assert registry.get_summary()["total_services"] == 1
    registry.unregister("market-1")
    assert registry.get("market-1") is None


def test_event_bus_delivers_direct_and_wildcard_subscriptions() -> None:
    bus_module = load("libraries.infrastructure.event_bus")
    events_module = load("shared.events")
    received: list[str] = []
    bus = bus_module.InMemoryEventBus()
    bus.subscribe("market.tick", lambda event: received.append(event.event_id))
    bus.subscribe("market.*", lambda event: received.append("wildcard"))

    async def exercise_bus() -> Any:
        await bus.start()
        event = events_module.create_event("tick.received", data={"symbol": "EUR/USD"})
        await bus.publish("market.tick", event)
        await bus._queue.join()
        await bus.stop()
        return event

    event = asyncio.run(exercise_bus())

    assert received == [event.event_id, "wildcard"]


def test_health_registry_converts_exceptions_to_unhealthy_results() -> None:
    health_module = load("libraries.infrastructure.health")
    registry = health_module.HealthCheckRegistry()
    registry.register_fn("ok", lambda: None)

    def fail() -> None:
        raise RuntimeError("dependency unavailable")

    registry.register_fn("fail", fail)
    results = asyncio.run(registry.run_all())
    summary = registry.get_summary(results)

    assert summary["status"] == health_module.HealthStatus.UNHEALTHY
    assert summary["unhealthy"] == 1


def test_dependency_container_honors_singleton_transient_and_factory_lifetimes() -> (
    None
):
    di = load("libraries.infrastructure.dependency_injection")

    class Port:
        pass

    class Adapter(Port):
        pass

    container = di.Container()
    container.register(Port, Adapter, di.ServiceLifetime.SINGLETON)
    assert container.resolve(Port) is container.resolve(Port)

    container.register_factory(str, lambda: "factory-value")
    assert container.resolve(str) == "factory-value"
