"""Tests for the ExecutionRouter."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderType,
)
from libraries.infrastructure.execution.broker_adapter import (
    BrokerAdapter,
    BrokerAdapterConfig,
)
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    ExecutionRouterConfig,
    NoSuitableBrokerError,
    RouterNotReadyError,
    RoutingTarget,
)


class _TestAdapter(BrokerAdapter):
    def __init__(self, name: str, connected: bool = True):
        super().__init__(BrokerAdapterConfig(broker_name=name))
        self._test_connected = connected

    @property
    def is_connected(self) -> bool:
        return self._test_connected

    async def connect(self) -> bool:
        self._test_connected = True
        return True

    async def disconnect(self) -> bool:
        self._test_connected = False
        return True

    async def health_check(self) -> dict:
        return {"connected": self._test_connected}

    async def submit_order(self, order):
        return None

    async def modify_order(self, broker_order_id, **kwargs):
        return None

    async def cancel_order(self, broker_order_id):
        return True

    async def close_position(self, position_id):
        return None

    async def get_open_positions(self):
        return []

    async def get_account(self):
        return None

    async def get_symbol_information(self, symbol):
        return None

    async def get_execution_history(self, symbol=None, since=None, limit=100):
        return []


@pytest.fixture
def router():
    return ExecutionRouter()


@pytest.fixture
def order():
    return Order(
        order_id=OrderId("test_001"),
        decision_id="dec1",
        execution_id="exec1",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.1"),
    )


class TestExecutionRouter:
    """Test suite for ExecutionRouter."""

    @pytest.mark.asyncio
    async def test_register_adapter(self, router):
        adapter = _TestAdapter("broker1")
        await router.register_adapter(adapter)
        assert await router.adapter_count() == 1

    @pytest.mark.asyncio
    async def test_unregister_adapter(self, router):
        adapter = _TestAdapter("broker1")
        await router.register_adapter(adapter)
        await router.unregister_adapter("broker1")
        assert await router.adapter_count() == 0

    @pytest.mark.asyncio
    async def test_route_raises_when_no_adapters(self, router, order):
        with pytest.raises(RouterNotReadyError):
            await router.route(order)

    @pytest.mark.asyncio
    async def test_route_selects_connected_adapter(self, router, order):
        adapter = _TestAdapter("broker1", connected=True)
        await router.register_adapter(adapter)
        decision = await router.route(order)
        assert decision.selected_broker == "broker1"
        assert not decision.fallback_used

    @pytest.mark.asyncio
    async def test_route_skips_disconnected_adapters(self, router, order):
        adapter1 = _TestAdapter("broker1", connected=False)
        adapter2 = _TestAdapter("broker2", connected=True)
        await router.register_adapter(adapter1)
        await router.register_adapter(adapter2)
        decision = await router.route(order)
        assert decision.selected_broker == "broker2"

    @pytest.mark.asyncio
    async def test_route_uses_priority(self, router, order):
        adapter1 = _TestAdapter("primary", connected=True)
        adapter2 = _TestAdapter("backup", connected=True)
        await router.register_adapter(adapter1, RoutingTarget(broker_name="primary", priority=1))
        await router.register_adapter(adapter2, RoutingTarget(broker_name="backup", priority=100))
        decision = await router.route(order)
        assert decision.selected_broker == "primary"

    @pytest.mark.asyncio
    async def test_update_health(self, router):
        adapter = _TestAdapter("broker1")
        await router.register_adapter(adapter)
        await router.update_health("broker1", 0.5)
        active = await router.get_active_adapters()
        assert len(active) == 1
        assert active[0][2].health_score == 0.5

    @pytest.mark.asyncio
    async def test_fallback_on_no_candidates(self, router, order):
        adapter = _TestAdapter("broker1", connected=True)
        target = RoutingTarget(
            broker_name="broker1",
            health_score=0.1,
            supported_symbols=frozenset({"GBPUSD"}),
        )
        await router.register_adapter(adapter, target)
        config = ExecutionRouterConfig(enable_fallback=True, fallback_min_health=0.0)
        router._config = config
        decision = await router.route(order)
        assert decision.fallback_used

    @pytest.mark.asyncio
    async def test_get_adapter(self, router):
        adapter = _TestAdapter("broker1")
        await router.register_adapter(adapter)
        result = await router.get_adapter("broker1")
        assert result is adapter

    @pytest.mark.asyncio
    async def test_get_adapter_nonexistent(self, router):
        result = await router.get_adapter("nonexistent")
        assert result is None

    def test_routing_target_defaults(self):
        target = RoutingTarget(broker_name="test")
        assert target.priority == 100
        assert target.health_score == 1.0
        assert target.is_active
        assert target.supports_symbol("ANY")

    def test_routing_target_symbol_support(self):
        target = RoutingTarget(
            broker_name="test",
            supported_symbols=frozenset({"EURUSD", "GBPUSD"}),
        )
        assert target.supports_symbol("EURUSD")
        assert target.supports_symbol("eurusd")
        assert not target.supports_symbol("BTCUSD")
