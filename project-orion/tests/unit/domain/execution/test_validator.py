"""Tests for order validator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.exceptions import OrderValidationError
from libraries.domain.execution.models import OrderSide, OrderType
from libraries.domain.execution.validator import (
    OrderValidator,
    OrderValidatorConfig,
    ValidationResult,
)
from tests.unit.domain.execution.conftest import make_order


@pytest.fixture
def validator() -> OrderValidator:
    return OrderValidator()


@pytest.fixture
def valid_order() -> object:
    return make_order()


class TestOrderValidator:
    async def test_valid_order_passes(self, validator: OrderValidator, valid_order: object) -> None:
        result = await validator.validate(valid_order, market_open=True, broker_available=True)  # type: ignore[arg-type]
        assert result.is_valid

    async def test_negative_volume_fails(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-002", decision_id="DEC-002", quantity=Decimal("-100"))
        result = await validator.validate(order)
        assert result.is_invalid
        assert any("positive" in e.lower() for e in result.errors)

    async def test_zero_volume_fails(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-003", decision_id="DEC-003", quantity=Decimal("0"))
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_volume_below_minimum_fails(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-004", decision_id="DEC-004", quantity=Decimal("0.0001"))
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_volume_above_maximum_fails(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-005", decision_id="DEC-005", quantity=Decimal("10000000"))
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_negative_price_fails(self, validator: OrderValidator) -> None:
        order = make_order(
            order_id="ORD-006",
            decision_id="DEC-006",
            quantity=Decimal("1000"),
            price=Decimal("-1.25"),
        )
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_market_closed_warning(self, validator: OrderValidator, valid_order: object) -> None:
        result = await validator.validate(valid_order, market_open=False)  # type: ignore[arg-type]
        assert result.is_invalid

    async def test_broker_unavailable_warning(
        self, validator: OrderValidator, valid_order: object
    ) -> None:
        result = await validator.validate(valid_order, broker_available=False)  # type: ignore[arg-type]
        assert result.is_invalid

    async def test_limit_order_requires_price(self, validator: OrderValidator) -> None:
        order = make_order(
            order_id="ORD-007",
            decision_id="DEC-007",
            order_type=OrderType.LIMIT,
            quantity=Decimal("1000"),
            price=None,
        )
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_stop_order_requires_price(self, validator: OrderValidator) -> None:
        order = make_order(
            order_id="ORD-008",
            decision_id="DEC-008",
            order_type=OrderType.STOP,
            quantity=Decimal("1000"),
            price=None,
        )
        result = await validator.validate(order)
        assert result.is_invalid

    async def test_high_spread_generates_warning(
        self, validator: OrderValidator, valid_order: object
    ) -> None:
        result = await validator.validate(valid_order, current_spread=15.0)  # type: ignore[arg-type]
        assert result.is_valid
        assert len(result.warnings) > 0

    async def test_lot_size_precision_check(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-009", decision_id="DEC-009", quantity=Decimal("1.234"))
        result = await validator.validate(order, lot_size=Decimal("0.01"))
        assert result.is_invalid

    async def test_tick_size_precision_check(self, validator: OrderValidator) -> None:
        order = make_order(
            order_id="ORD-010",
            decision_id="DEC-010",
            order_type=OrderType.LIMIT,
            quantity=Decimal("1000"),
            price=Decimal("1.23456"),
        )
        result = await validator.validate(order, tick_size=Decimal("0.0001"))
        assert result.is_invalid

    async def test_raise_if_invalid(self, validator: OrderValidator) -> None:
        order = make_order(order_id="ORD-011", decision_id="DEC-011", quantity=Decimal("-100"))
        result = await validator.validate(order)
        with pytest.raises(OrderValidationError):
            result.raise_if_invalid()

    def test_validation_result_properties(self) -> None:
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert not result.is_invalid

        result2 = ValidationResult(is_valid=False, errors=("error1", "error2"))
        assert result2.is_invalid
        assert len(result2.errors) == 2

    async def test_custom_config(self) -> None:
        config = OrderValidatorConfig(min_volume=Decimal("0.01"), max_volume=Decimal("100"))
        validator = OrderValidator(config=config)
        order = make_order(order_id="ORD-012", decision_id="DEC-012", quantity=Decimal("500"))
        result = await validator.validate(order)
        assert result.is_invalid
