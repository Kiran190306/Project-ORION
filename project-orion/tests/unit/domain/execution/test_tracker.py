"""Tests for order tracker."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from libraries.domain.execution.exceptions import OrderNotFoundError
from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import Order, OrderSide, OrderStatus, OrderType
from libraries.domain.execution.tracker import OrderTracker
from tests.unit.domain.execution.conftest import make_order


@pytest.fixture
def tracker() -> OrderTracker:
    return OrderTracker()


@pytest.fixture
def order1() -> Order:
    return make_order()


@pytest.fixture
def order2() -> Order:
    return make_order(
        order_id="ORD-002",
        decision_id="DEC-002",
        symbol="GBPUSD",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=Decimal("500"),
    )


class TestOrderTracker:
    async def test_register_and_get_order(self, tracker: OrderTracker, order1: Order) -> None:
        lifecycle = OrderLifecycleTracker(order1)
        await tracker.register(order1, lifecycle)
        result = await tracker.get_order("ORD-001")
        assert str(result.order_id) == "ORD-001"

    async def test_get_order_not_found(self, tracker: OrderTracker) -> None:
        with pytest.raises(OrderNotFoundError):
            await tracker.get_order("NONEXISTENT")

    async def test_get_by_decision(self, tracker: OrderTracker, order1: Order) -> None:
        lifecycle = OrderLifecycleTracker(order1)
        await tracker.register(order1, lifecycle)
        result = await tracker.get_by_decision("DEC-001")
        assert str(result.order_id) == "ORD-001"

    async def test_get_by_decision_not_found(self, tracker: OrderTracker) -> None:
        with pytest.raises(OrderNotFoundError):
            await tracker.get_by_decision("NONEXISTENT")

    async def test_get_by_symbol(self, tracker: OrderTracker, order1: Order, order2: Order) -> None:
        await tracker.register(order1, OrderLifecycleTracker(order1))
        await tracker.register(order2, OrderLifecycleTracker(order2))
        results = await tracker.get_by_symbol("EURUSD")
        assert len(results) == 1
        assert results[0].symbol == "EURUSD"

    async def test_get_active_orders(self, tracker: OrderTracker, order1: Order) -> None:
        lifecycle = OrderLifecycleTracker(order1)
        await tracker.register(order1, lifecycle)
        active = await tracker.get_active_orders()
        assert len(active) == 1

    async def test_get_by_status(self, tracker: OrderTracker, order1: Order, order2: Order) -> None:
        await tracker.register(order1, OrderLifecycleTracker(order1))
        await tracker.register(order2, OrderLifecycleTracker(order2))
        results = await tracker.get_by_status(OrderStatus.NEW)
        assert len(results) == 2

    async def test_update_order(self, tracker: OrderTracker, order1: Order) -> None:
        lifecycle = OrderLifecycleTracker(order1)
        await tracker.register(order1, lifecycle)
        updated = replace(order1, status=OrderStatus.FILLED)
        await tracker.update_order(updated)
        result = await tracker.get_order("ORD-001")
        assert result.status == OrderStatus.FILLED

    async def test_remove_order(self, tracker: OrderTracker, order1: Order) -> None:
        lifecycle = OrderLifecycleTracker(order1)
        await tracker.register(order1, lifecycle)
        await tracker.remove("ORD-001")
        with pytest.raises(OrderNotFoundError):
            await tracker.get_order("ORD-001")

    async def test_order_count(self, tracker: OrderTracker, order1: Order, order2: Order) -> None:
        assert await tracker.order_count() == 0
        await tracker.register(order1, OrderLifecycleTracker(order1))
        assert await tracker.order_count() == 1
        await tracker.register(order2, OrderLifecycleTracker(order2))
        assert await tracker.order_count() == 2

    async def test_clear(self, tracker: OrderTracker, order1: Order, order2: Order) -> None:
        await tracker.register(order1, OrderLifecycleTracker(order1))
        await tracker.register(order2, OrderLifecycleTracker(order2))
        assert await tracker.order_count() == 2
        await tracker.clear()
        assert await tracker.order_count() == 0
