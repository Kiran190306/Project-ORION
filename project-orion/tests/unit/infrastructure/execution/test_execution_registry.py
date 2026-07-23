"""Tests for the execution registry."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionSymbolInfo,
)
from libraries.infrastructure.execution.execution_registry import (
    AdapterHealthStatus,
    ExecutionRegistry,
    ExecutionRegistryConfig,
)
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    ExecutionRouterConfig,
)


class _RegistryAdapter(BrokerAdapter):
    """Simple adapter for registry tests."""

    def __init__(self, name: str, connect_ok: bool = True):
        super().__init__(BrokerAdapterConfig(broker_name=name))
        self._connect_ok = connect_ok

    async def connect(self) -> bool:
        if self._connect_ok:
            self._connected = True
            return True
        return False

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def health_check(self) -> dict:
        return {"connected": self._connected, "latency_ms": 5.0}

    async def submit_order(self, order): return None
    async def modify_order(self, broker_order_id, **kwargs): return None
    async def cancel_order(self, broker_order_id): return True
    async def close_position(self, position_id): return None
    async def get_open_positions(self): return []
    async def get_account(self):
        return AccountInfo(
            account_id="test", broker_name=self.broker_name,
            balance=Decimal("1000"), equity=Decimal("1000"),
            margin=Decimal("0"), margin_free=Decimal("1000"),
            margin_level=0.0, currency="USD", leverage=100,
        )
    async def get_symbol_information(self, symbol):
        return ExecutionSymbolInfo(symbol=symbol)
    async def get_execution_history(self, symbol=None, since=None, limit=100): return []


@pytest.fixture
def router():
    return ExecutionRouter()


@pytest.fixture
def registry(router):
    config = ExecutionRegistryConfig(
        health_check_interval_seconds=3600,  # Long interval for tests
    )
    return ExecutionRegistry(router, config)


class TestExecutionRegistry:
    """Test suite for ExecutionRegistry."""

    @pytest.mark.asyncio
    async def test_register_adapter(self, registry):
        adapter = _RegistryAdapter("test_broker")
        registered = await registry.register(adapter, auto_connect=False)
        # When auto_connect=False, status remains UNKNOWN since connect wasn't attempted
        assert registered.health_status == AdapterHealthStatus.UNKNOWN
        assert await registry.adapter_count() == 1

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(self, registry):
        adapter = _RegistryAdapter("test_broker")
        await registry.register(adapter, auto_connect=False)
        with pytest.raises(ValueError):
            await registry.register(adapter, auto_connect=False)

    @pytest.mark.asyncio
    async def test_unregister_adapter(self, registry):
        adapter = _RegistryAdapter("test_broker")
        await registry.register(adapter, auto_connect=False)
        result = await registry.unregister("test_broker")
        assert result is True
        assert await registry.adapter_count() == 0

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, registry):
        result = await registry.unregister("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_adapter(self, registry):
        adapter = _RegistryAdapter("test_broker")
        await registry.register(adapter, auto_connect=False)
        result = await registry.get_adapter("test_broker")
        assert result is adapter

    @pytest.mark.asyncio
    async def test_get_adapter_nonexistent(self, registry):
        result = await registry.get_adapter("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_registered(self, registry):
        adapter = _RegistryAdapter("test_broker")
        await registry.register(adapter, auto_connect=False)
        registered = await registry.get_registered("test_broker")
        assert registered is not None
        assert registered.adapter is adapter

    @pytest.mark.asyncio
    async def test_get_all_registered(self, registry):
        a1 = _RegistryAdapter("broker1")
        a2 = _RegistryAdapter("broker2")
        await registry.register(a1, auto_connect=False)
        await registry.register(a2, auto_connect=False)
        all_registered = await registry.get_all_registered()
        assert len(all_registered) == 2

    @pytest.mark.asyncio
    async def test_update_health(self, registry):
        adapter = _RegistryAdapter("test_broker")
        await registry.register(adapter, auto_connect=False)
        await registry.update_health("test_broker", health_score=0.3, error="degraded")
        registered = await registry.get_registered("test_broker")
        assert registered is not None
        assert registered.health_score == 0.3
        assert registered.last_error == "degraded"

    @pytest.mark.asyncio
    async def test_start_stop(self, registry):
        await registry.start()
        assert registry._running
        await registry.stop()
        assert not registry._running

    @pytest.mark.asyncio
    async def test_auto_connect_on_register(self):
        router = ExecutionRouter()
        registry = ExecutionRegistry(router)
        adapter = _RegistryAdapter("test_broker", connect_ok=True)
        registered = await registry.register(adapter, auto_connect=True)
        assert adapter.is_connected

