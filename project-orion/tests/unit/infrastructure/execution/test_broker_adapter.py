"""Tests for the broker adapter base class."""

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
    AccountInfo,
    AdapterNotConnectedError,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionAdapterError,
    ExecutionSymbolInfo,
    OrderExecutionInfo,
    PositionInfo,
)


class _ConcreteAdapter(BrokerAdapter):
    """Concrete adapter for testing the base class."""

    def __init__(self, config: BrokerAdapterConfig) -> None:
        super().__init__(config)

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def health_check(self) -> dict:
        self._validate_connected()
        return {"connected": True, "latency_ms": 5.0}

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        self._validate_connected()
        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId("test_001"),
            status=OrderStatus.FILLED,
        )

    async def modify_order(self, broker_order_id, **kwargs) -> OrderExecutionInfo:
        self._validate_connected()
        return OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=OrderStatus.SUBMITTED,
        )

    async def cancel_order(self, broker_order_id) -> bool:
        self._validate_connected()
        return True

    async def close_position(self, position_id) -> OrderExecutionInfo:
        self._validate_connected()
        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId("close_001"),
            status=OrderStatus.FILLED,
        )

    async def get_open_positions(self) -> list:
        self._validate_connected()
        return []

    async def get_account(self) -> AccountInfo:
        self._validate_connected()
        return AccountInfo(
            account_id="test",
            broker_name=self.broker_name,
            balance=Decimal("10000"),
            equity=Decimal("10000"),
            margin=Decimal("0"),
            margin_free=Decimal("10000"),
            margin_level=0.0,
            currency="USD",
            leverage=100,
        )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        self._validate_connected()
        return ExecutionSymbolInfo(symbol=symbol)

    async def get_execution_history(self, symbol=None, since=None, limit=100) -> list:
        self._validate_connected()
        return []


class TestBrokerAdapter:
    """Test suite for BrokerAdapter base class."""

    @pytest.fixture
    def adapter(self):
        config = BrokerAdapterConfig(broker_name="test")
        return _ConcreteAdapter(config)

    @pytest.mark.asyncio
    async def test_connect(self, adapter):
        assert not adapter.is_connected
        result = await adapter.connect()
        assert result is True
        assert adapter.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        assert adapter.is_connected
        result = await adapter.disconnect()
        assert result is True
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_health_check_raises_when_disconnected(self, adapter):
        with pytest.raises(AdapterNotConnectedError):
            await adapter.health_check()

    @pytest.mark.asyncio
    async def test_submit_order_raises_when_disconnected(self, adapter):
        order = Order(
            order_id=OrderId("test"),
            decision_id="dec1",
            execution_id="exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        with pytest.raises(AdapterNotConnectedError):
            await adapter.submit_order(order)

    @pytest.mark.asyncio
    async def test_submit_order_succeeds_when_connected(self, adapter):
        await adapter.connect()
        order = Order(
            order_id=OrderId("test"),
            decision_id="dec1",
            execution_id="exec1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        result = await adapter.submit_order(order)
        assert isinstance(result, OrderExecutionInfo)
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_broker_name_property(self, adapter):
        assert adapter.broker_name == "test"

    @pytest.mark.asyncio
    async def test_config_property(self, adapter):
        assert adapter.config.broker_name == "test"
        assert isinstance(adapter.config, BrokerAdapterConfig)

    def test_account_info_defaults(self):
        info = AccountInfo(
            account_id="acc1",
            broker_name="test",
            balance=Decimal("1000"),
            equity=Decimal("1000"),
            margin=Decimal("0"),
            margin_free=Decimal("1000"),
            margin_level=0.0,
            currency="USD",
            leverage=100,
        )
        assert info.account_id == "acc1"
        assert info.balance == Decimal("1000")
        assert not info.is_live

    def test_position_info_defaults(self):
        pos = PositionInfo(
            position_id="pos1",
            symbol="EURUSD",
            side=OrderSide.BUY,
            quantity=Decimal("0.1"),
            open_price=Decimal("1.2000"),
            current_price=Decimal("1.2050"),
        )
        assert pos.profit == Decimal("0")
        assert pos.commission == Decimal("0")

    def test_execution_symbol_info_defaults(self):
        info = ExecutionSymbolInfo(symbol="EURUSD")
        assert info.digits == 5
        assert info.min_volume == Decimal("0.01")
        assert info.max_volume == Decimal("100")

    def test_broker_adapter_config_defaults(self):
        config = BrokerAdapterConfig(broker_name="test")
        assert config.timeout_seconds == 30.0
        assert config.max_retries == 3
        assert not config.is_paper

    def test_execution_adapter_error(self):
        error = ExecutionAdapterError("Test error", broker_name="test")
        assert str(error) == "Test error"
        assert error.broker_name == "test"
