"""Tests for order router."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.exceptions import RoutingError
from libraries.domain.execution.models import Order, OrderSide, OrderType
from libraries.domain.execution.router import (
    BrokerCapabilities,
    OrderRouter,
    OrderRouterConfig,
    RouterScore,
    RoutingResult,
)


@pytest.fixture
def router() -> OrderRouter:
    return OrderRouter()


@pytest.fixture
def order() -> Order:
    return Order(
        order_id="ORD-001",
        decision_id="DEC-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1000"),
    )


@pytest.fixture
def broker1() -> BrokerCapabilities:
    return BrokerCapabilities(
        broker_id="broker-1",
        broker_name="Alpha Broker",
        supported_symbols=frozenset({"EURUSD", "GBPUSD"}),
        latency_ms=10.0,
        health_score=0.95,
        is_available=True,
    )


@pytest.fixture
def broker2() -> BrokerCapabilities:
    return BrokerCapabilities(
        broker_id="broker-2",
        broker_name="Beta Broker",
        supported_symbols=frozenset({"EURUSD", "USDJPY"}),
        latency_ms=5.0,
        health_score=0.85,
        is_available=True,
    )


class TestOrderRouter:
    async def test_route_to_best_broker(
        self,
        router: OrderRouter,
        order: Order,
        broker1: BrokerCapabilities,
        broker2: BrokerCapabilities,
    ) -> None:
        await router.register_broker(broker1)
        await router.register_broker(broker2)
        result = await router.route(order)
        assert result.selected_broker in ("broker-1", "broker-2")
        assert len(result.all_scores) > 0

    async def test_route_no_brokers_raises(self, router: OrderRouter, order: Order) -> None:
        with pytest.raises(RoutingError) as exc:
            await router.route(order)
        assert "No brokers" in str(exc.value)

    async def test_route_no_eligible_broker_raises(
        self, router: OrderRouter, order: Order, broker1: BrokerCapabilities
    ) -> None:
        limited = BrokerCapabilities(
            broker_id="broker-limited",
            broker_name="Limited",
            supported_symbols=frozenset({"USDJPY"}),
            is_available=True,
        )
        await router.register_broker(limited)
        with pytest.raises(RoutingError):
            await router.route(order)

    async def test_unavailable_broker_skipped(
        self, router: OrderRouter, order: Order, broker1: BrokerCapabilities
    ) -> None:
        unavailable = BrokerCapabilities(
            broker_id="broker-down",
            broker_name="Down",
            supported_symbols=frozenset({"EURUSD"}),
            is_available=False,
        )
        await router.register_broker(unavailable)
        await router.register_broker(broker1)
        result = await router.route(order)
        assert result.selected_broker == "broker-1"

    async def test_low_health_broker_skipped(
        self, router: OrderRouter, order: Order, broker1: BrokerCapabilities
    ) -> None:
        low_health = BrokerCapabilities(
            broker_id="broker-unhealthy",
            broker_name="Unhealthy",
            supported_symbols=frozenset({"EURUSD"}),
            health_score=0.1,
            is_available=True,
        )
        await router.register_broker(low_health)
        await router.register_broker(broker1)
        result = await router.route(order)
        assert result.selected_broker == "broker-1"

    async def test_fallback_routing(self, router: OrderRouter, order: Order) -> None:
        high_latency = BrokerCapabilities(
            broker_id="broker-slow",
            broker_name="Slow",
            supported_symbols=frozenset({"EURUSD"}),
            latency_ms=5000.0,
            health_score=0.9,
            is_available=True,
        )
        await router.register_broker(high_latency)
        config = OrderRouterConfig(max_latency_ms=100.0)
        strict_router = OrderRouter(config=config)
        await strict_router.register_broker(high_latency)
        result = await strict_router.route(order)
        assert result.fallback_used

    async def test_register_and_unregister_broker(
        self, router: OrderRouter, broker1: BrokerCapabilities
    ) -> None:
        await router.register_broker(broker1)
        assert await router.broker_count() == 1
        await router.unregister_broker("broker-1")
        assert await router.broker_count() == 0

    async def test_update_broker_health(
        self, router: OrderRouter, broker1: BrokerCapabilities
    ) -> None:
        await router.register_broker(broker1)
        await router.update_broker_health("broker-1", 0.5)
        brokers = await router.get_available_brokers()
        assert brokers[0].health_score == 0.5

    async def test_broker_capabilities_supports_order_type(self) -> None:
        bc = BrokerCapabilities(
            broker_id="test",
            broker_name="Test",
            supports_market_orders=True,
            supports_limit_orders=False,
        )
        assert bc.supports_order_type(OrderType.MARKET)
        assert not bc.supports_order_type(OrderType.LIMIT)

    async def test_router_score_properties(self) -> None:
        score = RouterScore(
            broker_id="test",
            broker_name="Test",
            score=90.0,
            latency_ms=5.0,
            health_score=0.95,
        )
        assert score.is_preferred
        assert "Test" in score.summary

    async def test_routing_result_creation(self) -> None:
        result = RoutingResult(
            selected_broker="broker-1",
            fallback_used=True,
            fallback_reason="Primary unavailable",
        )
        assert result.selected_broker == "broker-1"
        assert result.fallback_used
