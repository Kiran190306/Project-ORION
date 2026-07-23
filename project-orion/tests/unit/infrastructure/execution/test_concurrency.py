"""Concurrency tests for the execution layer components."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderType,
)
from libraries.infrastructure.execution.execution_router import (
    ExecutionRouter,
    RoutingTarget,
)
from libraries.infrastructure.execution.idempotency import IdempotencyGuard
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


class TestConcurrency:
    """Tests for thread-safe concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_router_registrations(self):
        """Test concurrent adapter registration."""
        router = ExecutionRouter()

        async def register(name: str):
            adapter = PaperExecutionAdapter(
                PaperExecutionConfig(broker_name=name, balance=Decimal("10000"))
            )
            await router.register_adapter(
                adapter,
                RoutingTarget(broker_name=name),
            )

        await asyncio.gather(*[register(f"broker_{i}") for i in range(10)])
        assert await router.adapter_count() == 10

    @pytest.mark.asyncio
    async def test_concurrent_idempotency_checks(self):
        """Test concurrent idempotency checks."""
        guard = IdempotencyGuard()

        async def register_and_check(i: int):
            exec_id = f"exec_{i}"
            order_id = f"order_{i}"
            hash_val = f"hash_{i}"
            try:
                await guard.check_and_register(exec_id, order_id, hash_val)
                return True
            except Exception:
                return False

        results = await asyncio.gather(*[register_and_check(i) for i in range(20)])
        assert all(results)  # All unique should succeed
        assert await guard.record_count() > 0

    @pytest.mark.asyncio
    async def test_concurrent_paper_execution(self):
        """Test concurrent order submissions to paper adapter."""
        adapter = PaperExecutionAdapter(
            PaperExecutionConfig(
                broker_name="paper",
                balance=Decimal("1000000"),
                latency_ms_mean=0.0,
            )
        )
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        async def submit_order(i: int):
            order = Order(
                order_id=OrderId(f"concurrent_{i}"),
                decision_id=f"dec_{i}",
                execution_id=f"exec_{i}",
                symbol="EURUSD",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1"),
            )
            try:
                result = await adapter.submit_order(order)
                return result.status.value
            except Exception as e:
                return str(e)

        results = await asyncio.gather(*[submit_order(i) for i in range(10)])
        # All should succeed (filled or partially_filled)
        assert all(r in ("filled", "partially_filled") for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_router_routing(self):
        """Test concurrent routing operations."""
        router = ExecutionRouter()

        # Register adapters
        for i in range(3):
            adapter = PaperExecutionAdapter(
                PaperExecutionConfig(broker_name=f"broker_{i}", balance=Decimal("10000"))
            )
            await adapter.connect()
            await router.register_adapter(
                adapter,
                RoutingTarget(broker_name=f"broker_{i}", priority=i),
            )

        async def route_order(i: int):
            order = Order(
                order_id=OrderId(f"route_{i}"),
                decision_id=f"dec_{i}",
                execution_id=f"exec_{i}",
                symbol="EURUSD",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1"),
            )
            return await router.route(order)

        decisions = await asyncio.gather(*[route_order(i) for i in range(5)])
        assert all(d.selected_broker == "broker_0" for d in decisions)

    @pytest.mark.asyncio
    async def test_concurrent_health_updates(self):
        """Test concurrent health score updates."""
        router = ExecutionRouter()
        adapter = PaperExecutionAdapter(
            PaperExecutionConfig(broker_name="test", balance=Decimal("10000"))
        )
        await router.register_adapter(adapter)

        async def update_health(score: float):
            await router.update_health("test", score)

        await asyncio.gather(*[update_health(i / 10.0) for i in range(10)])
        active = await router.get_active_adapters()
        assert len(active) == 1
        # active[0] is (broker_name, adapter, routing_target)
        broker_name, adapter, target = active[0]
        assert 0.0 <= target.health_score <= 1.0

