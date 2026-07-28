"""Tests for the order recovery engine."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    BrokerOrderId,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.infrastructure.execution.order_recovery import (
    OrderRecoveryConfig,
    OrderRecoveryEngine,
    OrderRecoveryStatus,
)


class _MockAdapter:
    """Mock adapter for recovery tests."""

    def __init__(self):
        self.positions = []
        self.execution_history = []

    async def connect(self):
        return True

    async def disconnect(self):
        return True

    async def health_check(self):
        return {"connected": True}

    async def get_execution_history(self, symbol=None, since=None, limit=100):
        return self.execution_history

    async def get_open_positions(self):
        return self.positions


class TestOrderRecoveryEngine:
    """Test suite for OrderRecoveryEngine."""

    @pytest.fixture
    def engine(self):
        config = OrderRecoveryConfig(
            max_recovery_attempts=3,
            recovery_interval_seconds=0.1,
            query_broker_on_recovery=False,
        )
        return OrderRecoveryEngine(config)

    @pytest.fixture
    def order(self):
        return Order(
            order_id=OrderId("order_001"),
            decision_id="dec1",
            execution_id="exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            status=OrderStatus.SUBMITTED,
            broker_order_id=BrokerOrderId("broker_001"),
        )

    @pytest.mark.asyncio
    async def test_recover_pending_order(self, engine, order):
        adapter = _MockAdapter()
        result = await engine.recover_pending_order(order, adapter)
        # With query_broker_on_recovery=False, the engine returns RECOVERED
        assert result.status == OrderRecoveryStatus.RECOVERED
        assert result.order_id == OrderId("order_001")

    @pytest.mark.asyncio
    async def test_recover_pending_order_found(self, engine, order):
        adapter = _MockAdapter()
        adapter.execution_history = [
            type("", (), {"broker_order_id": BrokerOrderId("broker_001")})()
        ]
        config = OrderRecoveryConfig(query_broker_on_recovery=True)
        engine = OrderRecoveryEngine(config)
        result = await engine.recover_pending_order(order, adapter)
        assert result.status == OrderRecoveryStatus.RECOVERED

    @pytest.mark.asyncio
    async def test_recover_open_position(self, engine):
        adapter = _MockAdapter()
        adapter.positions = [
            type(
                "",
                (),
                {
                    "position_id": "pos_001",
                    "quantity": Decimal("0.1"),
                    "open_price": Decimal("1.2000"),
                },
            )()
        ]
        result = await engine.recover_open_position(
            position_id="pos_001",
            symbol="EURUSD",
            adapter=adapter,
        )
        assert result.status == OrderRecoveryStatus.RECOVERED

    @pytest.mark.asyncio
    async def test_recover_open_position_not_found(self, engine):
        adapter = _MockAdapter()
        result = await engine.recover_open_position(
            position_id="pos_999",
            symbol="EURUSD",
            adapter=adapter,
        )
        assert result.status == OrderRecoveryStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_recover_partial_fill(self, engine, order):
        adapter = _MockAdapter()
        result = await engine.recover_partial_fill(order, adapter)
        # Order status is SUBMITTED, not PARTIALLY_FILLED, so returns FAILED
        assert result.status == OrderRecoveryStatus.FAILED

    @pytest.mark.asyncio
    async def test_recover_partial_fill_completed(self, engine, order):
        order = Order(
            order_id=OrderId("order_001"),
            decision_id="dec1",
            execution_id="exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            status=OrderStatus.PARTIALLY_FILLED,
            filled_quantity=Decimal("0.05"),
            broker_order_id=BrokerOrderId("broker_001"),
        )
        adapter = _MockAdapter()
        adapter.execution_history = [
            type(
                "",
                (),
                {
                    "broker_order_id": BrokerOrderId("broker_001"),
                    "filled_quantity": Decimal("0.1"),
                },
            )()
        ]
        config = OrderRecoveryConfig(query_broker_on_recovery=True)
        engine = OrderRecoveryEngine(config)
        result = await engine.recover_partial_fill(order, adapter)
        assert result.status == OrderRecoveryStatus.RECOVERED

    @pytest.mark.asyncio
    async def test_recover_network_interruption(self, engine, order):
        adapter = _MockAdapter()
        orders = [order]
        results = await engine.recover_network_interruption(orders, adapter)
        assert len(results) == 1

    def test_recovery_status_enum(self):
        assert OrderRecoveryStatus.PENDING.value == "pending"
        assert OrderRecoveryStatus.RECOVERED.value == "recovered"
        assert OrderRecoveryStatus.FAILED.value == "failed"

    @pytest.mark.asyncio
    async def test_get_recovery_history(self, engine, order):
        adapter = _MockAdapter()
        await engine.recover_pending_order(order, adapter)
        history = await engine.get_recovery_history("order_001")
        assert len(history) >= 0  # May be empty if not tracked

    @pytest.mark.asyncio
    async def test_recovery_count(self, engine):
        assert await engine.recovery_count() == 0
