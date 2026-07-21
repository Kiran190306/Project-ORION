"""Tests for execution domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.execution.models import (
    ExecutionReport,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderTimeInForce,
    OrderType,
)


class TestOrder:
    def test_order_creation(self) -> None:
        order = Order(
            order_id="ORD-001",
            decision_id="DEC-001",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
            status=OrderStatus.NEW,
        )
        assert order.order_id == "ORD-001"
        assert order.decision_id == "DEC-001"
        assert order.symbol == "EURUSD"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.volume == Decimal("1000")
        assert order.status == OrderStatus.NEW
        assert order.created_at is not None

    def test_order_with_optional_fields(self) -> None:
        order = Order(
            order_id="ORD-002",
            decision_id="DEC-002",
            symbol="GBPUSD",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            volume=Decimal("500"),
            price=Decimal("1.25000"),
            stop_loss=Decimal("1.24000"),
            take_profit=Decimal("1.27000"),
            time_in_force=OrderTimeInForce.GTC,
            status=OrderStatus.NEW,
        )
        assert order.price == Decimal("1.25000")
        assert order.stop_loss == Decimal("1.24000")
        assert order.take_profit == Decimal("1.27000")
        assert order.time_in_force == OrderTimeInForce.GTC

    def test_order_immutable_by_default(self) -> None:
        order = Order(
            order_id="ORD-003",
            decision_id="DEC-003",
            symbol="USDJPY",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("100"),
        )
        with pytest.raises(AttributeError):
            order.status = OrderStatus.FILLED  # type: ignore

    def test_order_default_status(self) -> None:
        order = Order(
            order_id="ORD-004",
            decision_id="DEC-004",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
        )
        assert order.status == OrderStatus.NEW

    def test_order_str_representation(self) -> None:
        order = Order(
            order_id="ORD-005",
            decision_id="DEC-005",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
        )
        s = str(order)
        assert "ORD-005" in s
        assert "EURUSD" in s
        assert "BUY" in s

    def test_order_with_metadata(self) -> None:
        order = Order(
            order_id="ORD-006",
            decision_id="DEC-006",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
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
        report = ExecutionReport(
            report_id="RPT-001",
            order_id="ORD-001",
            broker_order_id="BROKER-001",
            symbol="EURUSD",
            side="buy",
        )
        assert report.report_id == "RPT-001"
        assert report.order_id == "ORD-001"
        assert report.broker_order_id == "BROKER-001"
        assert report.symbol == "EURUSD"
        assert report.side == "buy"

    def test_execution_report_with_fill_details(self) -> None:
        report = ExecutionReport(
            report_id="RPT-002",
            order_id="ORD-002",
            broker_order_id="BROKER-002",
            symbol="GBPUSD",
            side="sell",
            filled_volume=Decimal("500"),
            price=Decimal("1.25500"),
            cost=Decimal("627.50"),
            commission=Decimal("0.50"),
            liquidity="taker",
        )
        assert report.filled_volume == Decimal("500")
        assert report.price == Decimal("1.25500")
        assert report.cost == Decimal("627.50")
        assert report.commission == Decimal("0.50")
        assert report.liquidity == "taker"

    def test_execution_report_defaults(self) -> None:
        report = ExecutionReport(
            report_id="RPT-003",
            order_id="ORD-003",
            broker_order_id="BROKER-003",
            symbol="USDJPY",
            side="buy",
        )
        assert report.filled_volume is None
        assert report.price is None
        assert report.commission is None
        assert report.liquidity == ""


class TestOrderId:
    def test_order_id_generation(self) -> None:
        oid = OrderId()
        assert oid.id is not None
        assert len(oid.id) > 0

    def test_order_id_str(self) -> None:
        oid = OrderId()
        assert str(oid) == oid.id

    def test_order_id_unique(self) -> None:
        oid1 = OrderId()
        oid2 = OrderId()
        assert oid1.id != oid2.id
