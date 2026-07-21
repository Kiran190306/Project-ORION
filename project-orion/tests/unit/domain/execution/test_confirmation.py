"""Tests for fill confirmation and validation."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.confirmation import (
    FillConfirmation,
    FillValidator,
    FillValidatorConfig,
)
from libraries.domain.execution.exceptions import FillValidationError
from libraries.domain.execution.models import (
    ExecutionReport,
    Order,
    OrderSide,
    OrderType,
)


@pytest.fixture
def validator() -> FillValidator:
    return FillValidator()


@pytest.fixture
def order() -> Order:
    return Order(
        order_id="ORD-001",
        decision_id="DEC-001",
        symbol="EURUSD",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        volume=Decimal("1000"),
    )


class TestFillValidator:
    async def test_valid_full_fill(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-001",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
            broker_fill_id="BROKER-FL-001",
        )
        await validator.validate_fill(order, fill)  # should not raise

    async def test_valid_partial_fill(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-002",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("500"),
            remaining_volume=Decimal("500"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("552.50"),
            broker_fill_id="BROKER-FL-002",
        )
        await validator.validate_fill(order, fill)  # should not raise

    async def test_wrong_order_id_raises(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-003",
            order_id="WRONG-ORD",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
        )
        with pytest.raises(FillValidationError):
            await validator.validate_fill(order, fill)

    async def test_wrong_symbol_raises(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-004",
            order_id="ORD-001",
            symbol="GBPUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
        )
        with pytest.raises(FillValidationError):
            await validator.validate_fill(order, fill)

    async def test_wrong_side_raises(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-005",
            order_id="ORD-001",
            symbol="EURUSD",
            side="sell",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
        )
        with pytest.raises(FillValidationError):
            await validator.validate_fill(order, fill)

    async def test_negative_volume_raises(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-006",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("-100"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
        )
        with pytest.raises(FillValidationError):
            await validator.validate_fill(order, fill)

    async def test_excessive_volume_raises(self, validator: FillValidator, order: Order) -> None:
        fill = FillConfirmation(
            fill_id="FL-007",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("2000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("2210.00"),
        )
        with pytest.raises(FillValidationError):
            await validator.validate_fill(order, fill)

    async def test_fill_properties(self) -> None:
        full = FillConfirmation(
            fill_id="FL-008",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
        )
        assert full.is_full_fill
        assert not full.is_partial_fill

        partial = FillConfirmation(
            fill_id="FL-009",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("500"),
            remaining_volume=Decimal("500"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("552.50"),
        )
        assert not partial.is_full_fill
        assert partial.is_partial_fill

    async def test_build_confirmation_from_report(
        self, validator: FillValidator, order: Order
    ) -> None:
        report = ExecutionReport(
            report_id="RPT-001",
            order_id="ORD-001",
            broker_order_id="BROKER-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            price=Decimal("1.10500"),
            cost=Decimal("1105.00"),
            commission=Decimal("0.50"),
            liquidity="taker",
        )
        confirmation = await validator.build_confirmation(order, report)
        assert confirmation.fill_id == "RPT-001"
        assert confirmation.filled_volume == Decimal("1000")
        assert confirmation.fill_price == Decimal("1.10500")
        assert confirmation.is_full_fill

    async def test_missing_broker_fill_id_raises(self, validator: FillValidator, order: Order) -> None:
        config = FillValidatorConfig(require_broker_fill_id=True)
        strict_validator = FillValidator(config=config)
        fill = FillConfirmation(
            fill_id="FL-010",
            order_id="ORD-001",
            symbol="EURUSD",
            side="buy",
            filled_volume=Decimal("1000"),
            remaining_volume=Decimal("0"),
            fill_price=Decimal("1.10500"),
            total_cost=Decimal("1105.00"),
            broker_fill_id="",
        )
        with pytest.raises(FillValidationError):
            await strict_validator.validate_fill(order, fill)
