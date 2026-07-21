"""Tests for order recovery handler."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.execution.exceptions import RecoveryError
from libraries.domain.execution.models import Order, OrderSide, OrderStatus, OrderType
from libraries.domain.execution.recovery import (
    OrderRecoveryHandler,
    RecoveryConfig,
    RecoveryAttempt,
    RecoveryState,
)


@pytest.fixture
def handler() -> OrderRecoveryHandler:
    return OrderRecoveryHandler()


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


class TestOrderRecoveryHandler:
    async def test_mark_for_recovery(self, handler: OrderRecoveryHandler, order: Order) -> None:
        state = await handler.mark_for_recovery(order)
        assert state.order_id == "ORD-001"
        assert state.is_recovering
        assert state.attempts == 0

    async def test_needs_recovery_for_stale_order(self, handler: OrderRecoveryHandler) -> None:
        from datetime import datetime, timezone, timedelta
        order = Order(
            order_id="ORD-002",
            decision_id="DEC-002",
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            volume=Decimal("1000"),
            status=OrderStatus.SUBMITTED,
            created_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        )
        assert await handler.needs_recovery(order)

    async def test_no_recovery_for_new_order(self, handler: OrderRecoveryHandler, order: Order) -> None:
        assert not await handler.needs_recovery(order)

    async def test_attempt_recovery(self, handler: OrderRecoveryHandler, order: Order) -> None:
        await handler.mark_for_recovery(order)

        async def query_broker(oid: str, symbol: str) -> tuple[bool, str, str]:
            return True, "filled", ""

        attempt = await handler.attempt_recovery(order, query_broker)
        assert attempt.attempt_number == 1
        assert attempt.order_id == "ORD-001"
        assert attempt.recovered

    async def test_attempt_recovery_not_marked_raises(
        self, handler: OrderRecoveryHandler, order: Order
    ) -> None:
        with pytest.raises(RecoveryError):
            await handler.attempt_recovery(order)

    async def test_exhausted_recovery_raises(
        self, handler: OrderRecoveryHandler, order: Order
    ) -> None:
        config = RecoveryConfig(max_recovery_attempts=2)
        limited_handler = OrderRecoveryHandler(config=config)
        await limited_handler.mark_for_recovery(order)

        async def query_broker(oid: str, symbol: str) -> tuple[bool, str, str]:
            return False, "not_found", "error"

        await limited_handler.attempt_recovery(order, query_broker)
        await limited_handler.attempt_recovery(order, query_broker)
        with pytest.raises(RecoveryError):
            await limited_handler.attempt_recovery(order, query_broker)

    async def test_is_recovering(self, handler: OrderRecoveryHandler, order: Order) -> None:
        assert not await handler.is_recovering("ORD-001")
        await handler.mark_for_recovery(order)
        assert await handler.is_recovering("ORD-001")

    async def test_cancel_recovery(self, handler: OrderRecoveryHandler, order: Order) -> None:
        await handler.mark_for_recovery(order)
        assert await handler.is_recovering("ORD-001")
        await handler.cancel_recovery("ORD-001")
        assert not await handler.is_recovering("ORD-001")

    async def test_recovery_count(self, handler: OrderRecoveryHandler, order: Order) -> None:
        assert await handler.recovery_count() == 0
        await handler.mark_for_recovery(order)
        assert await handler.recovery_count() == 1

    async def test_get_attempts(self, handler: OrderRecoveryHandler, order: Order) -> None:
        await handler.mark_for_recovery(order)

        async def query_broker(oid: str, symbol: str) -> tuple[bool, str, str]:
            return True, "filled", ""

        await handler.attempt_recovery(order, query_broker)
        attempts = await handler.get_attempts("ORD-001")
        assert len(attempts) == 1

    async def test_recovery_attempt_creation(self) -> None:
        attempt = RecoveryAttempt(
            attempt_number=1,
            order_id="ORD-001",
            broker_queried=True,
            broker_found=True,
            broker_status="filled",
            recovered=True,
        )
        assert attempt.attempt_number == 1
        assert attempt.recovered
        assert attempt.broker_status == "filled"

    async def test_recovery_state_creation(self) -> None:
        state = RecoveryState(
            order_id="ORD-001",
            is_recovering=True,
            attempts=1,
            max_attempts=3,
        )
        assert state.order_id == "ORD-001"
        assert state.is_recovering
        assert state.attempts == 1
