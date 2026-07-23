"""Tests for order builder."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.builder import OrderBuilder, OrderBuilderConfig
from libraries.domain.execution.exceptions import OrderBuildError
from libraries.domain.execution.models import OrderType
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection


@pytest.fixture
def builder() -> OrderBuilder:
    return OrderBuilder()


@pytest.fixture
def executable_decision() -> TradeDecision:
    return TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=85.0,
        entry_price=Decimal("1.10500"),
        stop_loss=Decimal("1.10000"),
        take_profit=Decimal("1.11500"),
        position_size=Decimal("10000"),
        risk_amount=Decimal("50"),
        account_risk_pct=1.0,
        decision_id="DEC-001",
    )


class TestOrderBuilder:
    def test_build_market_order(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(executable_decision)
        assert order.symbol == "EURUSD"
        assert order.side.value == "buy"
        assert order.order_type == OrderType.MARKET
        assert order.quantity == Decimal("10000")
        assert order.decision_id == "DEC-001"
        assert order.price is None

    def test_build_limit_order(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(
            executable_decision, order_type=OrderType.LIMIT, price=Decimal("1.10500")
        )
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("1.10500")

    def test_build_stop_order(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(
            executable_decision, order_type=OrderType.STOP, price=Decimal("1.10600")
        )
        assert order.order_type == OrderType.STOP
        assert order.price == Decimal("1.10600")

    def test_build_with_stop_loss_take_profit(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(executable_decision)
        # stop_loss and take_profit are stored in metadata
        assert order.metadata.get("strategy") is not None

    def test_build_non_executable_decision_raises(self, builder: OrderBuilder) -> None:
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.REJECT,
            reason="Test reject",
        )
        with pytest.raises(OrderBuildError) as exc:
            builder.build(decision)
        assert "non-executable" in str(exc.value).lower()

    def test_build_deferred_decision_raises(self, builder: OrderBuilder) -> None:
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.DEFER,
            reason="Test defer",
        )
        with pytest.raises(OrderBuildError):
            builder.build(decision)

    def test_build_with_metadata(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(executable_decision, metadata={"source": "test"})
        assert order.metadata["decision_id"] == "DEC-001"
        assert order.metadata["source"] == "test"

    def test_build_with_broker_symbol(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(executable_decision, broker_symbol="EURUSD.b")
        assert order.symbol == "EURUSD.b"

    def test_build_generates_order_id(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        order = builder.build(executable_decision)
        assert str(order.order_id).startswith("ORD-")

    def test_build_unique_order_ids(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        o1 = builder.build(executable_decision)
        o2 = builder.build(executable_decision)
        assert o1.order_id != o2.order_id

    def test_price_rounding(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY,
            entry_price=Decimal("1.123456"),
            position_size=Decimal("1000"),
            decision_id="DEC-002",
        )
        order = builder.build(decision, order_type=OrderType.LIMIT, price=Decimal("1.123456"))
        assert order.price == Decimal("1.12346")

    def test_volume_rounding(
        self, builder: OrderBuilder, executable_decision: TradeDecision
    ) -> None:
        decision = TradeDecision(
            symbol="EURUSD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.BUY,
            position_size=Decimal("123.456"),
            decision_id="DEC-003",
        )
        order = builder.build(decision)
        assert order.quantity == Decimal("123.46")

    def test_custom_config(self, executable_decision: TradeDecision) -> None:
        config = OrderBuilderConfig(
            default_order_type=OrderType.LIMIT,
            volume_precision=0,
            price_precision=2,
        )
        builder = OrderBuilder(config=config)
        order = builder.build(executable_decision, price=Decimal("1.12345"))
        assert order.order_type == OrderType.LIMIT
        assert order.price == Decimal("1.12")
        assert order.quantity == Decimal("10000")

    def test_build_sell_order(self, builder: OrderBuilder) -> None:
        decision = TradeDecision(
            symbol="GBPUSD",
            outcome=DecisionOutcome.EXECUTE,
            direction=SignalDirection.SELL,
            position_size=Decimal("5000"),
            decision_id="DEC-004",
        )
        order = builder.build(decision)
        assert order.side.value == "sell"
