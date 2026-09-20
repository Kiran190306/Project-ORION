"""Unit tests for PaperTradingService orchestration."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from apps.trading_engine.src.services.paper_trading import (
    PaperExecutionResult,
    PaperTradingError,
    PaperTradingService,
)

from libraries.domain.trading.decision_result import DecisionOutcome, TradeDecision
from libraries.domain.trading.signals import SignalDirection
from libraries.infrastructure.execution.broker_adapter import (
    AdapterOrderRejectedError,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


@pytest.fixture
def paper_adapter() -> PaperExecutionAdapter:
    config = PaperExecutionConfig(
        broker_name="test_paper",
        is_paper=True,
        balance=Decimal("100000.00"),
        latency_ms_mean=0.0,
        latency_ms_std=0.0,
    )
    return PaperExecutionAdapter(config)


@pytest.fixture
def service(paper_adapter: PaperExecutionAdapter) -> PaperTradingService:
    return PaperTradingService(adapter=paper_adapter)


@pytest.mark.asyncio
async def test_paper_trade_successful_market_buy(
    service: PaperTradingService, paper_adapter: PaperExecutionAdapter
) -> None:
    """Execute a valid BUY trade decision through paper trading pipeline."""
    await paper_adapter.connect()

    decision = TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=85.0,
        entry_price=Decimal("1.10500"),
        stop_loss=Decimal("1.10000"),
        take_profit=Decimal("1.11500"),
        position_size=Decimal(10000),
        decision_id="DEC-TEST-001",
    )

    result = await service.execute(decision)

    assert isinstance(result, PaperExecutionResult)
    assert result.symbol == "EURUSD"
    assert result.direction == "buy"
    assert result.is_paper is True
    assert result.order_id.startswith("ORD-")
    assert result.status in ("filled", "partially_filled", "submitted")
    assert result.metadata is not None
    assert result.metadata["decision_id"] == "DEC-TEST-001"
    assert result.metadata["confidence"] == 85.0


@pytest.mark.asyncio
async def test_paper_trade_successful_market_sell(
    service: PaperTradingService, paper_adapter: PaperExecutionAdapter
) -> None:
    """Execute a valid SELL trade decision through paper trading pipeline."""
    await paper_adapter.connect()

    decision = TradeDecision(
        symbol="GBPUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.SELL,
        confidence=72.0,
        entry_price=Decimal("1.25000"),
        position_size=Decimal(5000),
        decision_id="DEC-TEST-002",
    )

    result = await service.execute(decision)

    assert result.symbol == "GBPUSD"
    assert result.direction == "sell"
    assert result.is_paper is True


@pytest.mark.asyncio
async def test_paper_trade_connects_if_disconnected(
    service: PaperTradingService, paper_adapter: PaperExecutionAdapter
) -> None:
    """Service automatically connects the adapter if it is disconnected."""
    assert not paper_adapter.is_connected

    decision = TradeDecision(
        symbol="USDJPY",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=90.0,
        entry_price=Decimal("150.00"),
        position_size=Decimal(1000),
        decision_id="DEC-TEST-003",
    )

    result = await service.execute(decision)
    assert paper_adapter.is_connected
    assert result.symbol == "USDJPY"


@pytest.mark.asyncio
async def test_paper_trade_non_executable_decision_raises(
    service: PaperTradingService,
) -> None:
    """Non-executable decision (REJECT / DEFER) must raise PaperTradingError."""
    decision = TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.REJECT,
        direction=SignalDirection.BUY,
        reason="Risk limit exceeded",
    )

    with pytest.raises(PaperTradingError, match="Decision is not executable"):
        await service.execute(decision)


@pytest.mark.asyncio
async def test_paper_trade_broker_rejection_raises(
    service: PaperTradingService, paper_adapter: PaperExecutionAdapter
) -> None:
    """Broker rejection raises PaperTradingError with descriptive reason."""
    await paper_adapter.connect()
    paper_adapter.submit_order = AsyncMock(
        side_effect=AdapterOrderRejectedError("Insufficient margin for order", broker_name="paper")
    )

    decision = TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=80.0,
        entry_price=Decimal("1.1000"),
        position_size=Decimal(50000),
    )

    with pytest.raises(PaperTradingError, match="Paper broker rejected order"):
        await service.execute(decision)


@pytest.mark.asyncio
async def test_paper_trade_order_validation_failure_raises(
    service: PaperTradingService, paper_adapter: PaperExecutionAdapter
) -> None:
    """Domain OrderValidator rejects order exceeding maximum volume bounds."""
    await paper_adapter.connect()

    decision = TradeDecision(
        symbol="EURUSD",
        outcome=DecisionOutcome.EXECUTE,
        direction=SignalDirection.BUY,
        confidence=80.0,
        entry_price=Decimal("1.1000"),
        position_size=Decimal(5000000),  # Exceeds max volume of 1,000,000
    )

    with pytest.raises(PaperTradingError, match="Order validation failed.*exceeds maximum"):
        await service.execute(decision)


def test_create_decision_factory() -> None:
    """create_decision helper produces a valid EXECUTE TradeDecision."""
    decision = PaperTradingService.create_decision(
        symbol="EURUSD",
        direction="buy",
        confidence=88.5,
        entry_price=Decimal("1.08500"),
        stop_loss=Decimal("1.08000"),
        take_profit=Decimal("1.09500"),
        position_size=Decimal(20000),
    )

    assert decision.symbol == "EURUSD"
    assert decision.direction == SignalDirection.BUY
    assert decision.outcome == DecisionOutcome.EXECUTE
    assert decision.confidence == 88.5
    assert decision.entry_price == Decimal("1.08500")
    assert decision.stop_loss == Decimal("1.08000")
    assert decision.take_profit == Decimal("1.09500")
    assert decision.position_size == Decimal(20000)
    assert decision.decision_id.startswith("DEC-")
    assert decision.is_executable is True
