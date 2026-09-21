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

    @pytest.mark.asyncio
    async def test_side_aware_pricing_and_adverse_slippage(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))
        # Ask should be around 1.20006, Bid around 1.19994
        buy_order = Order(
            order_id=OrderId("test_buy_side"),
            decision_id="d1",
            execution_id="e1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )
        buy_res = await adapter.submit_order(buy_order)
        # BUY fills at Ask >= 1.20000
        assert buy_res.average_fill_price >= Decimal("1.20000")

        # Now test SELL
        sell_order = Order(
            order_id=OrderId("test_sell_side"),
            decision_id="d2",
            execution_id="e2",
            symbol="EURUSD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.5"),
        )
        sell_res = await adapter.submit_order(sell_order)
        # SELL fills at Bid <= 1.20000
        assert sell_res.average_fill_price <= Decimal("1.20000")

    @pytest.mark.asyncio
    async def test_resting_limit_buy_triggers_when_ask_drops(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        limit_order = Order(
            order_id=OrderId("lim_buy_1"),
            decision_id="d3",
            execution_id="e3",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("1.0"),
            price=Decimal("1.19500"),
        )
        res = await adapter.submit_order(limit_order)
        assert res.status == OrderStatus.SUBMITTED
        assert len(adapter._pending_orders) == 1

        # Price drops below limit price
        await adapter.set_current_price("EURUSD", Decimal("1.19400"))
        # Pending order should now be triggered and filled
        assert len(adapter._pending_orders) == 0
        order_tracked = adapter._orders[str(limit_order.order_id)] if str(limit_order.order_id) in adapter._orders else list(adapter._orders.values())[-1]
        assert order_tracked.status == OrderStatus.FILLED.value
        assert len(adapter._positions) == 1

    @pytest.mark.asyncio
    async def test_resting_stop_sell_triggers_when_bid_drops(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        stop_order = Order(
            order_id=OrderId("stp_sell_1"),
            decision_id="d4",
            execution_id="e4",
            symbol="EURUSD",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=Decimal("1.0"),
            stop_price=Decimal("1.19500"),
        )
        res = await adapter.submit_order(stop_order)
        assert res.status == OrderStatus.SUBMITTED

        # Price drops below stop price
        await adapter.set_current_price("EURUSD", Decimal("1.19400"))
        assert len(adapter._pending_orders) == 0

    @pytest.mark.asyncio
    async def test_position_accumulation_and_netting(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        # 1. Buy 1.0 lot
        o1 = Order(
            order_id=OrderId("acc_1"),
            decision_id="d5",
            execution_id="e5",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        await adapter.submit_order(o1)
        positions = await adapter.get_open_positions()
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("1.0")
        assert positions[0].side == OrderSide.BUY

        # 2. Accumulate: Buy another 1.0 lot at higher price
        await adapter.set_current_price("EURUSD", Decimal("1.21000"))
        o2 = Order(
            order_id=OrderId("acc_2"),
            decision_id="d6",
            execution_id="e6",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        await adapter.submit_order(o2)
        positions = await adapter.get_open_positions()
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("2.0")
        # Weighted average entry price should be ~1.20500
        assert Decimal("1.20") < positions[0].open_price < Decimal("1.21")

        # 3. Partial reduction: Sell 1.0 lot at 1.22000
        await adapter.set_current_price("EURUSD", Decimal("1.22000"))
        o3 = Order(
            order_id=OrderId("acc_3"),
            decision_id="d7",
            execution_id="e7",
            symbol="EURUSD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        await adapter.submit_order(o3)
        positions = await adapter.get_open_positions()
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("1.0")

        # 4. Full close: Sell remaining 1.0 lot
        o4 = Order(
            order_id=OrderId("acc_4"),
            decision_id="d8",
            execution_id="e8",
            symbol="EURUSD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        await adapter.submit_order(o4)
        positions = await adapter.get_open_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_stop_loss_trigger_closes_position(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        order = Order(
            order_id=OrderId("sl_order"),
            decision_id="d9",
            execution_id="e9",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            stop_loss=Decimal("1.19500"),
        )
        await adapter.submit_order(order)
        assert len(await adapter.get_open_positions()) == 1

        # Drop price to breach SL (1.19400 <= 1.19500)
        await adapter.set_current_price("EURUSD", Decimal("1.19400"))
        # Position should be closed
        assert len(await adapter.get_open_positions()) == 0

    @pytest.mark.asyncio
    async def test_take_profit_trigger_closes_position(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        order = Order(
            order_id=OrderId("tp_order"),
            decision_id="d10",
            execution_id="e10",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
            take_profit=Decimal("1.20500"),
        )
        await adapter.submit_order(order)
        assert len(await adapter.get_open_positions()) == 1

        # Raise price to hit TP (1.20600 >= 1.20500)
        await adapter.set_current_price("EURUSD", Decimal("1.20600"))
        # Position should be closed
        assert len(await adapter.get_open_positions()) == 0

    @pytest.mark.asyncio
    async def test_account_reset_clears_all_state(self, adapter):
        await adapter.connect()
        await adapter.set_current_price("EURUSD", Decimal("1.20000"))

        order = Order(
            order_id=OrderId("rst_order"),
            decision_id="d11",
            execution_id="e11",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1.0"),
        )
        await adapter.submit_order(order)
        assert len(await adapter.get_open_positions()) == 1

        # Reset account
        await adapter.reset_account(Decimal("50000.00"))
        acct = await adapter.get_account()
        assert acct.balance == Decimal("50000.00")
        assert len(await adapter.get_open_positions()) == 0
        assert len(adapter._orders) == 0

