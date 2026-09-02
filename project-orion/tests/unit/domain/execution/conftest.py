"""Shared fixtures and helpers for execution domain tests."""

from __future__ import annotations

from decimal import Decimal

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
from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection


def make_order(
    order_id: str = "ORD-001",
    decision_id: str = "DEC-001",
    execution_id: str = "EXEC-001",
    symbol: str = "EURUSD",
    side: OrderSide = OrderSide.BUY,
    order_type: OrderType = OrderType.MARKET,
    quantity: Decimal = Decimal("1000"),
    price: Decimal | None = None,
    stop_price: Decimal | None = None,
    time_in_force: OrderTimeInForce = OrderTimeInForce.GTC,
    status: OrderStatus = OrderStatus.NEW,
    **kwargs: object,
) -> Order:
    """Build an Order using the canonical OrderId representation."""
    return Order(
        order_id=OrderId(value=order_id),
        decision_id=decision_id,
        execution_id=execution_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        status=status,
        **kwargs,  # type: ignore[arg-type]
    )


def make_executable_decision(
    symbol: str = "EURUSD",
    decision_id: str = "DEC-001",
    position_size: Decimal = Decimal("10000"),
) -> TradeDecision:
    """Build a canonical executable TradeDecision fixture."""
    return TradeDecision(
        symbol=symbol,
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=85.0,
        entry_price=Decimal("1.10500"),
        stop_loss=Decimal("1.10000"),
        take_profit=Decimal("1.11500"),
        position_size=position_size,
        risk_amount=Decimal("50"),
        account_risk_pct=1.0,
        decision_id=decision_id,
    )


def make_execution_report(
    execution_id: str = "RPT-001",
    order: Order | None = None,
    filled_quantity: Decimal = Decimal("1000"),
    average_price: Decimal | None = Decimal("1.10500"),
    commission: Decimal = Decimal("0"),
    broker_order_id: str = "BROKER-001",
    status: ExecutionResultStatus = ExecutionResultStatus.SUCCESS,
) -> ExecutionReport:
    """Build an ExecutionReport using the canonical order/result structure."""
    base_order = order or make_order()
    result = ExecutionResult(
        execution_id=execution_id,
        decision_id=base_order.decision_id,
        order_id=base_order.order_id,
        symbol=base_order.symbol,
        side=base_order.side,
        quantity=base_order.quantity,
        status=status,
        filled_quantity=filled_quantity,
        average_price=average_price,
        commission=commission,
        broker_order_id=BrokerOrderId(value=broker_order_id),
    )
    return ExecutionReport(
        execution_id=execution_id,
        decision_id=base_order.decision_id,
        order=base_order,
        result=result,
    )
