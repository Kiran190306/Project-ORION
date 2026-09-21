"""Unit tests for BrokerReconciliationEngine."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from libraries.domain.execution.models import BrokerOrderId, OrderSide, OrderStatus
from libraries.domain.reconciliation.engine import BrokerReconciliationEngine
from libraries.domain.reconciliation.models import DiscrepancyType, ReconciliationStatus
from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    OrderExecutionInfo,
    PositionInfo,
)


def test_reconciliation_perfect_match() -> None:
    engine = BrokerReconciliationEngine()

    local_account = {
        "balance": Decimal("10000.00"),
        "equity": Decimal("10050.00"),
    }
    remote_account = AccountInfo(
        account_id="acc-001",
        broker_name="mock",
        balance=Decimal("10000.00"),
        equity=Decimal("10050.00"),
        margin=Decimal("200.00"),
        margin_free=Decimal("9850.00"),
        margin_level=5025.0,
        currency="USD",
        leverage=50,
    )

    local_orders = [
        {
            "id": "ord-1",
            "broker_order_id": "b-ord-1",
            "symbol": "EUR/USD",
            "status": "FILLED",
            "quantity": Decimal("10000"),
        }
    ]
    remote_orders = [
        OrderExecutionInfo(
            broker_order_id=BrokerOrderId("b-ord-1"),
            status=OrderStatus.FILLED,
            filled_quantity=Decimal("10000"),
            metadata={"symbol": "EUR/USD"},
        )
    ]

    local_positions = [
        {
            "id": "pos-1",
            "symbol": "EUR/USD",
            "side": "BUY",
            "quantity": Decimal("10000"),
            "entry_price": Decimal("1.0850"),
        }
    ]
    remote_positions = [
        PositionInfo(
            position_id="pos-1",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            quantity=Decimal("10000"),
            open_price=Decimal("1.0850"),
            current_price=Decimal("1.0855"),
        )
    ]

    snapshot = engine.reconcile(
        organization_id="org-123",
        broker_account_id="broker-acc-1",
        local_account=local_account,
        local_orders=local_orders,
        local_positions=local_positions,
        remote_account=remote_account,
        remote_orders=remote_orders,
        remote_positions=remote_positions,
    )

    assert snapshot.status == ReconciliationStatus.MATCHED
    assert not snapshot.has_discrepancies
    assert len(snapshot.order_discrepancies) == 0
    assert len(snapshot.position_discrepancies) == 0
    assert len(snapshot.account_discrepancies) == 0


def test_reconciliation_detects_position_drift() -> None:
    engine = BrokerReconciliationEngine()

    local_account = {"balance": Decimal("10000.00"), "equity": Decimal("10000.00")}
    remote_account = AccountInfo(
        account_id="acc-001",
        broker_name="mock",
        balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
        margin=Decimal("0"),
        margin_free=Decimal("10000.00"),
        margin_level=0.0,
        currency="USD",
        leverage=50,
    )

    # Local has open position EUR/USD 10,000, but broker has 5,000
    local_positions = [
        {
            "id": "pos-1",
            "symbol": "EUR/USD",
            "side": "BUY",
            "quantity": Decimal("10000"),
            "entry_price": Decimal("1.0850"),
        }
    ]
    remote_positions = [
        PositionInfo(
            position_id="pos-1",
            symbol="EUR/USD",
            side=OrderSide.BUY,
            quantity=Decimal("5000"),
            open_price=Decimal("1.0850"),
            current_price=Decimal("1.0850"),
        )
    ]

    snapshot = engine.reconcile(
        organization_id="org-123",
        broker_account_id="broker-acc-1",
        local_account=local_account,
        local_orders=[],
        local_positions=local_positions,
        remote_account=remote_account,
        remote_orders=[],
        remote_positions=remote_positions,
    )

    assert snapshot.status == ReconciliationStatus.DISCREPANCY
    assert snapshot.has_discrepancies
    assert len(snapshot.position_discrepancies) == 1
    assert snapshot.position_discrepancies[0].discrepancy_type == DiscrepancyType.POSITION_QTY_MISMATCH
    assert snapshot.position_discrepancies[0].delta_qty == Decimal("5000")


def test_reconciliation_detects_untracked_broker_order() -> None:
    engine = BrokerReconciliationEngine()

    local_account = {"balance": Decimal("10000.00"), "equity": Decimal("10000.00")}
    remote_account = AccountInfo(
        account_id="acc-001",
        broker_name="mock",
        balance=Decimal("10000.00"),
        equity=Decimal("10000.00"),
        margin=Decimal("0"),
        margin_free=Decimal("10000.00"),
        margin_level=0.0,
        currency="USD",
        leverage=50,
    )

    # Broker has order b-ord-99 not present in ORION
    remote_orders = [
        OrderExecutionInfo(
            broker_order_id=BrokerOrderId("b-ord-99"),
            status=OrderStatus.SUBMITTED,
            filled_quantity=Decimal("20000"),
            metadata={"symbol": "GBP/USD"},
        )
    ]

    snapshot = engine.reconcile(
        organization_id="org-123",
        broker_account_id="broker-acc-1",
        local_account=local_account,
        local_orders=[],
        local_positions=[],
        remote_account=remote_account,
        remote_orders=remote_orders,
        remote_positions=[],
    )

    assert snapshot.status == ReconciliationStatus.DISCREPANCY
    assert len(snapshot.order_discrepancies) == 1
    assert snapshot.order_discrepancies[0].discrepancy_type == DiscrepancyType.ORDER_UNTRACKED_ON_BROKER
    assert snapshot.order_discrepancies[0].broker_order_id == "b-ord-99"


def test_reconciliation_detects_balance_drift() -> None:
    engine = BrokerReconciliationEngine(balance_tolerance=Decimal("0.05"))

    local_account = {"balance": Decimal("10000.00"), "equity": Decimal("10000.00")}
    remote_account = AccountInfo(
        account_id="acc-001",
        broker_name="mock",
        balance=Decimal("10005.50"),  # $5.50 drift
        equity=Decimal("10005.50"),
        margin=Decimal("0"),
        margin_free=Decimal("10005.50"),
        margin_level=0.0,
        currency="USD",
        leverage=50,
    )

    snapshot = engine.reconcile(
        organization_id="org-123",
        broker_account_id="broker-acc-1",
        local_account=local_account,
        local_orders=[],
        local_positions=[],
        remote_account=remote_account,
        remote_orders=[],
        remote_positions=[],
    )

    assert snapshot.status == ReconciliationStatus.DISCREPANCY
    assert len(snapshot.account_discrepancies) >= 1
    assert any(d.discrepancy_type == DiscrepancyType.BALANCE_DRIFT for d in snapshot.account_discrepancies)
    assert snapshot.balance_delta == Decimal("5.50")
