"""Tests for the paper trading execution adapter."""

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
from libraries.infrastructure.execution.broker_adapter import (
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


class TestPaperExecutionAdapter:
    """Test suite for PaperExecutionAdapter."""

    @pytest.fixture
    def adapter(self):
        config = PaperExecutionConfig(
            broker_name="paper_test",
            balance=Decimal("100000"),
            latency_ms_mean=0.0,
            latency_ms_std=0.0,
        )
        return PaperExecutionAdapter(config)

    @pytest.fixture
    def market_order(self):
        return Order(
            order_id=OrderId("test_market"),
            decision_id="dec1",
            execution_id="exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )

    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        result = await adapter.connect()
        assert result is True
        assert adapter.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        await adapter.disconnect()
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        await adapter.connect()
        health = await adapter.health_check()
        assert health["connected"]
        assert health["details"]["paper_trading"]

    @pytest.mark.asyncio
    async def test_submit_market_order(self, adapter, market_order):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        result = await adapter.submit_order(market_order)
        assert result.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
        assert result.filled_quantity <= market_order.quantity

    @pytest.mark.asyncio
    async def test_submit_limit_order(self, adapter):
        await adapter.connect()
        order = Order(
            order_id=OrderId("test_limit"),
            decision_id="dec2",
            execution_id="exec2",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("1.15000"),
        )
        result = await adapter.submit_order(order)
        assert result.status == OrderStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_submit_stop_order(self, adapter):
        await adapter.connect()
        order = Order(
            order_id=OrderId("test_stop"),
            decision_id="dec3",
            execution_id="exec3",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=Decimal("0.1"),
            stop_price=Decimal("1.25000"),
        )
        result = await adapter.submit_order(order)
        assert result.status == OrderStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_submit_order_raises_when_disconnected(self, adapter, market_order):
        with pytest.raises(AdapterNotConnectedError):
            await adapter.submit_order(market_order)

    @pytest.mark.asyncio
    async def test_cancel_order(self, adapter):
        await adapter.connect()
        result = await adapter.cancel_order(BrokerOrderId("paper_1000"))
        # Returns False when order doesn't exist
        assert not result

    @pytest.mark.asyncio
    async def test_get_account(self, adapter):
        await adapter.connect()
        account = await adapter.get_account()
        assert account.balance == Decimal("100000")
        assert account.currency == "USD"
        assert not account.is_live

    @pytest.mark.asyncio
    async def test_get_open_positions(self, adapter):
        await adapter.connect()
        positions = await adapter.get_open_positions()
        assert isinstance(positions, list)

    @pytest.mark.asyncio
    async def test_get_symbol_information(self, adapter):
        await adapter.connect()
        info = await adapter.get_symbol_information("EURUSD")
        assert info.symbol == "EURUSD"
        assert info.digits == 5

    @pytest.mark.asyncio
    async def test_get_execution_history(self, adapter):
        await adapter.connect()
        history = await adapter.get_execution_history()
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_close_position(self, adapter):
        await adapter.connect()
        with pytest.raises(AdapterOrderRejectedError):
            await adapter.close_position("nonexistent")

    @pytest.mark.asyncio
    async def test_market_order_fills_at_price(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        order = Order(
            order_id=OrderId("test_price"),
            decision_id="dec4",
            execution_id="exec4",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        result = await adapter.submit_order(order)
        assert result.average_fill_price is not None
        # Fill price should be within spread + slippage range of 1.20000
        assert Decimal("1.19") <= result.average_fill_price <= Decimal("1.21")

