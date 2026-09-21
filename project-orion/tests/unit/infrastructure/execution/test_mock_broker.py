"""Unit tests for MockBrokerAdapter."""

from __future__ import annotations

from decimal import Decimal
import pytest

from libraries.domain.execution.models import (
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.infrastructure.execution.broker_adapter import (
    AdapterOrderRejectedError,
    AdapterRateLimitError,
    AdapterTimeoutError,
)
from libraries.infrastructure.execution.mock_broker import (
    MockBrokerAdapter,
    MockBrokerConfig,
)


@pytest.fixture
def adapter() -> MockBrokerAdapter:
    config = MockBrokerConfig(
        broker_name="mock_test",
        initial_balance=Decimal("10000.00"),
        seed=123,
    )
    return MockBrokerAdapter(config)


@pytest.mark.asyncio
async def test_connect_and_health_check(adapter: MockBrokerAdapter) -> None:
    assert not adapter.is_connected
    connected = await adapter.connect()
    assert connected
    assert adapter.is_connected

    health = await adapter.health_check()
    assert health["connected"] is True
    assert health["details"]["broker"] == "mock_test"

    account = await adapter.get_account()
    assert account.balance == Decimal("10000.00")
    assert account.equity == Decimal("10000.00")
    assert account.is_live is False  # Invariant


@pytest.mark.asyncio
async def test_immediate_fill(adapter: MockBrokerAdapter) -> None:
    await adapter.connect()

    order = Order(
        order_id=OrderId("ord-001"),
        decision_id="dec-1",
        execution_id="exec-1",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.08500"),
    )

    exec_info = await adapter.submit_order(order)
    assert exec_info.status == OrderStatus.FILLED
    assert exec_info.filled_quantity == Decimal("10000")
    assert len(exec_info.fills) == 1

    positions = await adapter.get_open_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "EUR/USD"
    assert positions[0].quantity == Decimal("10000")

    account = await adapter.get_account()
    assert account.margin > Decimal("0")


@pytest.mark.asyncio
async def test_partial_fill_mode(adapter: MockBrokerAdapter) -> None:
    adapter.set_mode("PARTIAL_FILL")
    await adapter.connect()

    order = Order(
        order_id=OrderId("ord-partial"),
        decision_id="dec-2",
        execution_id="exec-2",
        symbol="GBP/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.27500"),
    )

    exec_info = await adapter.submit_order(order)
    assert exec_info.status == OrderStatus.PARTIALLY_FILLED
    assert exec_info.filled_quantity == Decimal("5000.00")


@pytest.mark.asyncio
async def test_reject_mode(adapter: MockBrokerAdapter) -> None:
    adapter.set_mode("REJECT")
    await adapter.connect()

    order = Order(
        order_id=OrderId("ord-reject"),
        decision_id="dec-3",
        execution_id="exec-3",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.08500"),
    )

    exec_info = await adapter.submit_order(order)
    assert exec_info.status == OrderStatus.REJECTED
    assert exec_info.rejection_reason == "INSUFFICIENT_MARGIN"


@pytest.mark.asyncio
async def test_rate_limit_and_timeout_injection(adapter: MockBrokerAdapter) -> None:
    await adapter.connect()

    order = Order(
        order_id=OrderId("ord-fault"),
        decision_id="dec-4",
        execution_id="exec-4",
        symbol="USD/JPY",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("155.00"),
    )

    adapter.set_mode("RATE_LIMIT")
    with pytest.raises(AdapterRateLimitError, match="429 Too Many Requests"):
        await adapter.submit_order(order)

    adapter.set_mode("TIMEOUT")
    with pytest.raises(AdapterTimeoutError, match="timed out"):
        await adapter.submit_order(order)


@pytest.mark.asyncio
async def test_close_position_and_pnl(adapter: MockBrokerAdapter) -> None:
    await adapter.connect()

    # Buy EUR/USD at 1.08500
    order = Order(
        order_id=OrderId("ord-close-test"),
        decision_id="dec-5",
        execution_id="exec-5",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("1.08500"),
    )
    await adapter.submit_order(order)

    positions = await adapter.get_open_positions()
    pos = positions[0]

    # Change price to 1.08700 (+20 pips -> +$20 on 10,000 units)
    adapter.set_price("EUR/USD", Decimal("1.08700"))

    close_exec = await adapter.close_position(pos.position_id)
    assert close_exec.status == OrderStatus.FILLED

    positions_after = await adapter.get_open_positions()
    assert len(positions_after) == 0

    account = await adapter.get_account()
    # Initial 10000 + 20 = 10020
    assert account.balance == Decimal("10020.0000")
    assert account.margin == Decimal("0.0000")


@pytest.mark.asyncio
async def test_order_idempotency(adapter: MockBrokerAdapter) -> None:
    await adapter.connect()

    order = Order(
        order_id=OrderId("ord-idempotent-1"),
        decision_id="dec-6",
        execution_id="exec-6",
        symbol="AUD/USD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("10000"),
        price=Decimal("0.65500"),
    )

    exec1 = await adapter.submit_order(order)
    exec2 = await adapter.submit_order(order)

    # Same broker_order_id returned, no duplicate execution
    assert exec1.broker_order_id == exec2.broker_order_id
    positions = await adapter.get_open_positions()
    assert len(positions) == 1
    assert positions[0].quantity == Decimal("10000")
