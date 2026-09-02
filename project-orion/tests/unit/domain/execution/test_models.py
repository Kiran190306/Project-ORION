"""Tests for execution domain models."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    BrokerOrderId,
    ExecutionReport,
    ExecutionResult,
    ExecutionResultStatus,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderTimeInForce,
    OrderType,
)
from tests.unit.domain.execution.conftest import make_execution_report, make_order


class TestOrder:
    def test_order_creation(self) -> None:
        order = make_order()
        assert str(order.order_id) == "ORD-001"
        assert order.decision_id == "DEC-001"
        assert order.symbol == "EURUSD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == Decimal("1000")
        assert order.status == OrderStatus.NEW
        assert order.created_at is not None

    def test_order_with_optional_fields(self) -> None:
        order = make_order(
            order_id="ORD-002",
            decision_id="DEC-002",
            symbol="GBPUSD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=Decimal("500"),
            price=Decimal("1.25000"),
            stop_price=Decimal("1.24000"),
            metadata={"take_profit": "1.27000"},
        )
        assert order.price == Decimal("1.25000")
        assert order.stop_price == Decimal("1.24000")
        assert order.metadata["take_profit"] == "1.27000"
        assert order.time_in_force == OrderTimeInForce.GTC

    def test_order_immutable_by_default(self) -> None:
        order = make_order(order_id="ORD-003", decision_id="DEC-003", symbol="USDJPY", quantity=Decimal("100"))
        with pytest.raises(AttributeError):
            order.status = OrderStatus.FILLED  # type: ignore

    def test_order_default_status(self) -> None:
        order = make_order(order_id="ORD-004", decision_id="DEC-004")
        assert order.status == OrderStatus.NEW

    def test_order_str_representation(self) -> None:
        order = make_order(order_id="ORD-005", decision_id="DEC-005")
        s = str(order)
        assert "ORD-005" in s
        assert "EURUSD" in s
        assert "BUY" in s

    def test_order_with_metadata(self) -> None:
        order = make_order(
            order_id="ORD-006",
            decision_id="DEC-006",
            metadata={"strategy": "scalping", "confidence": 85.0},
        )
        assert order.metadata["strategy"] == "scalping"
        assert order.metadata["confidence"] == 85.0


class TestOrderEnums:
    def test_order_side_values(self) -> None:
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"

    def test_order_type_values(self) -> None:
        assert OrderType.MARKET.value == "market"
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.STOP.value == "stop"
        assert OrderType.STOP_LIMIT.value == "stop_limit"
        assert OrderType.OCO.value == "oco"
        assert OrderType.TRAILING_STOP.value == "trailing_stop"
        assert OrderType.IOC.value == "ioc"
        assert OrderType.FOK.value == "fok"

    def test_order_status_values(self) -> None:
        assert OrderStatus.NEW.value == "new"
        assert OrderStatus.VALIDATED.value == "validated"
        assert OrderStatus.BUILT.value == "built"
        assert OrderStatus.ROUTED.value == "routed"
        assert OrderStatus.SUBMITTED.value == "submitted"
        assert OrderStatus.ACKNOWLEDGED.value == "acknowledged"
        assert OrderStatus.PARTIALLY_FILLED.value == "partially_filled"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.REJECTED.value == "rejected"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.EXPIRED.value == "expired"
        assert OrderStatus.SETTLED.value == "settled"
        assert OrderStatus.COMPLETED.value == "completed"

    def test_time_in_force_values(self) -> None:
        assert OrderTimeInForce.GTC.value == "gtc"
        assert OrderTimeInForce.DAY.value == "day"
        assert OrderTimeInForce.IOC.value == "ioc"
        assert OrderTimeInForce.FOK.value == "fok"
        assert OrderTimeInForce.GTD.value == "gtd"


class TestExecutionReport:
    def test_execution_report_creation(self) -> None:
        order = make_order()
        report = make_execution_report(execution_id="RPT-001", order=order)
        assert report.execution_id == "RPT-001"
        assert report.order.order_id == order.order_id
        assert report.result.broker_order_id == BrokerOrderId(value="BROKER-001")
        assert report.order.symbol == "EURUSD"
        assert report.order.side == OrderSide.BUY

    def test_execution_report_with_fill_details(self) -> None:
        order = make_order(
            order_id="ORD-002",
            symbol="GBPUSD",
            side=OrderSide.SELL,
            quantity=Decimal("500"),
        )
        report = make_execution_report(
            execution_id="RPT-002",
            order=order,
            filled_quantity=Decimal("500"),
            average_price=Decimal("1.25500"),
            commission=Decimal("0.50"),
            broker_order_id="BROKER-002",
        )
        assert report.result.filled_quantity == Decimal("500")
        assert report.result.average_price == Decimal("1.25500")
        assert report.result.commission == Decimal("0.50")

    def test_execution_report_defaults(self) -> None:
        order = make_order(order_id="ORD-003", symbol="USDJPY")
        report = make_execution_report(
            execution_id="RPT-003",
            order=order,
            filled_quantity=Decimal("0"),
            average_price=None,
            commission=Decimal("0"),
            broker_order_id="BROKER-003",
            status=ExecutionResultStatus.PENDING,
        )
        assert report.result.filled_quantity == Decimal("0")
        assert report.result.average_price is None
        assert report.result.commission == Decimal("0")


class TestOrderId:
    def test_order_id_generation(self) -> None:
        oid = OrderId(value="ORD-GEN-001")
        assert oid.value is not None
        assert len(oid.value) > 0

    def test_order_id_str(self) -> None:
        oid = OrderId(value="ORD-STR-001")
        assert str(oid) == "ORD-STR-001"

    def test_order_id_unique(self) -> None:
        oid1 = OrderId(value="ORD-A")
        oid2 = OrderId(value="ORD-B")
        assert oid1.value != oid2.value
