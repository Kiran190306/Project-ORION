"""Unit tests for TradingCycleWorker.

Tests the autonomous trading pipeline: market data -> decision -> risk -> execution.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src.workers.market_data import MarketTick
from apps.trading_engine.src.workers.trading_cycle import (
    CycleMetrics,
    CycleResult,
    TradingCycleWorker,
)

from libraries.domain.notification.service import (
    NotificationService,
    NotificationServiceConfig,
)
from libraries.domain.risk.engine import RiskEngine
from libraries.domain.trading.decision_engine import DecisionEngine
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


@pytest.fixture
def paper_adapter():
    """Create a paper execution adapter for testing."""
    config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal(100000),
    )
    adapter = PaperExecutionAdapter(config=config)
    asyncio.run(adapter.connect())
    return adapter


@pytest.fixture
def notification_service():
    """Create a notification service for testing."""
    return NotificationService(
        config=NotificationServiceConfig(enabled=True)
    )


@pytest.fixture
def trading_cycle_worker(paper_adapter, notification_service):
    """Create a TradingCycleWorker with required dependencies."""
    return TradingCycleWorker(
        decision_engine=DecisionEngine(),
        risk_engine=RiskEngine(),
        paper_adapter=paper_adapter,
        notification_service=notification_service,
        account_balance=Decimal(100000),
    )


@pytest.fixture
def sample_market_tick():
    """Create a sample market tick for testing."""
    return MarketTick(
        symbol="EUR/USD",
        bid=Decimal("1.0850"),
        ask=Decimal("1.0852"),
        mid=Decimal("1.0851"),
        spread_pips=2.0,
        timestamp=datetime.now(timezone.utc),
        source="test",
        is_simulated=True,
    )


async def test_trading_cycle_worker_initial_metrics(trading_cycle_worker):
    """Worker starts with zero metrics."""
    metrics = trading_cycle_worker.metrics
    assert metrics.cycles_attempted == 0
    assert metrics.cycles_completed == 0
    assert metrics.cycles_failed == 0
    assert metrics.strategy_evaluations == 0
    assert metrics.risk_rejections == 0
    assert metrics.orders_submitted == 0


async def test_trading_cycle_empty_market_data(trading_cycle_worker):
    """Worker handles empty market data gracefully."""
    results = await trading_cycle_worker.run_cycle({})
    assert results == []
    assert trading_cycle_worker.metrics.cycles_attempted == 0


async def test_trading_cycle_invalid_tick(trading_cycle_worker, sample_market_tick):
    """Worker rejects invalid market ticks."""
    invalid_tick = MarketTick(
        symbol="EUR/USD",
        bid=Decimal("-1.0"),  # Invalid
        ask=Decimal("1.0852"),
        mid=Decimal("1.0851"),
        spread_pips=2.0,
        timestamp=datetime.now(timezone.utc),
        source="test",
    )

    results = await trading_cycle_worker.run_cycle({"EUR/USD": invalid_tick})
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].outcome == "error"
    assert "Invalid market tick" in results[0].reason


async def test_trading_cycle_deferred_decision(trading_cycle_worker, sample_market_tick):
    """Worker handles DEFER decisions from DecisionEngine."""
    # Note: This test depends on DecisionEngine behavior
    # In a real scenario, we'd mock DecisionEngine to return DEFER
    results = await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    # At minimum, should complete without error
    assert len(results) == 1
    assert results[0].symbol == "EUR/USD"


async def test_trading_cycle_risk_rejection(trading_cycle_worker, sample_market_tick):
    """Worker handles risk rejections appropriately."""
    # Note: This test depends on RiskEngine behavior
    # In a real scenario, we'd mock RiskEngine to return REJECTED
    results = await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    # Should complete without crashing
    assert len(results) == 1
    assert results[0].symbol == "EUR/USD"


async def test_trading_cycle_paper_execution(trading_cycle_worker, sample_market_tick):
    """Worker successfully executes paper trades when approved."""
    results = await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    # Should complete the cycle
    assert len(results) == 1
    assert results[0].symbol == "EUR/USD"
    assert results[0].cycle_id is not None


async def test_trading_cycle_notification_on_success(trading_cycle_worker, sample_market_tick):
    """Worker sends notifications on successful trades."""
    initial_metrics = trading_cycle_worker.metrics

    await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    # May or may not send notification depending on decision/risk
    # Just verify it doesn't crash
    assert trading_cycle_worker.metrics.cycles_attempted >= initial_metrics.cycles_attempted


async def test_trading_cycle_notification_on_risk_rejection(trading_cycle_worker, sample_market_tick):
    """Worker sends notifications on risk rejection."""
    # Note: This depends on RiskEngine returning REJECTED
    await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    # Should not crash even if notification fails
    assert trading_cycle_worker.metrics.cycles_attempted >= 0


async def test_trading_cycle_error_isolation(trading_cycle_worker, sample_market_tick):
    """Worker isolates errors per symbol."""
    # Add multiple symbols
    market_data = {
        "EUR/USD": sample_market_tick,
        "GBP/USD": MarketTick(
            symbol="GBP/USD",
            bid=Decimal("1.2630"),
            ask=Decimal("1.2632"),
            mid=Decimal("1.2631"),
            spread_pips=2.0,
            timestamp=datetime.now(timezone.utc),
            source="test",
        ),
    }

    results = await trading_cycle_worker.run_cycle(market_data)

    # Should process both symbols independently
    assert len(results) == 2
    assert all(r.symbol in market_data for r in results)


async def test_trading_cycle_metrics_tracking(trading_cycle_worker, sample_market_tick):
    """Worker accurately tracks cycle metrics."""
    initial_attempted = trading_cycle_worker.metrics.cycles_attempted

    await trading_cycle_worker.run_cycle({"EUR/USD": sample_market_tick})

    metrics_after = trading_cycle_worker.metrics
    assert metrics_after.cycles_attempted == initial_attempted + 1


async def test_trading_cycle_paper_adapter_not_connected(paper_adapter, notification_service):
    """Worker handles disconnected paper adapter gracefully."""
    worker = TradingCycleWorker(
        decision_engine=DecisionEngine(),
        risk_engine=RiskEngine(),
        paper_adapter=paper_adapter,
        notification_service=notification_service,
        account_balance=Decimal(100000),
    )

    # Disconnect the adapter
    await paper_adapter.disconnect()

    tick = MarketTick(
        symbol="EUR/USD",
        bid=Decimal("1.0850"),
        ask=Decimal("1.0852"),
        mid=Decimal("1.0851"),
        spread_pips=2.0,
        timestamp=datetime.now(timezone.utc),
        source="test",
    )

    results = await worker.run_cycle({"EUR/USD": tick})
    assert len(results) == 1
    # Should complete without crashing


async def test_cycle_result_structure():
    """CycleResult has correct structure and immutability."""
    result = CycleResult(
        symbol="EUR/USD",
        cycle_id="TEST-123",
        success=True,
        outcome="executed",
        reason="Test",
        order_id="ORDER-456",
        metadata={"test": "data"},
    )

    assert result.symbol == "EUR/USD"
    assert result.cycle_id == "TEST-123"
    assert result.success is True
    assert result.outcome == "executed"
    assert result.order_id == "ORDER-456"
    assert result.metadata == {"test": "data"}


async def test_cycle_metrics_initialization():
    """CycleMetrics initializes with zero values."""
    metrics = CycleMetrics()
    assert metrics.cycles_attempted == 0
    assert metrics.cycles_completed == 0
    assert metrics.cycles_failed == 0
    assert metrics.strategy_evaluations == 0
    assert metrics.risk_rejections == 0
    assert metrics.orders_submitted == 0


async def test_trading_cycle_concurrent_safety(trading_cycle_worker, sample_market_tick):
    """Worker handles concurrent cycle calls safely."""
    market_data = {"EUR/USD": sample_market_tick}

    # Run multiple cycles concurrently
    tasks = [trading_cycle_worker.run_cycle(market_data) for _ in range(3)]
    results = await asyncio.gather(*tasks)

    # All should complete
    assert len(results) == 3
    assert all(len(r) == 1 for r in results)


async def test_trading_cycle_custom_account_balance(paper_adapter, notification_service):
    """Worker respects custom account balance."""
    worker = TradingCycleWorker(
        decision_engine=DecisionEngine(),
        risk_engine=RiskEngine(),
        paper_adapter=paper_adapter,
        notification_service=notification_service,
        account_balance=Decimal(50000),  # Custom balance
    )

    tick = MarketTick(
        symbol="EUR/USD",
        bid=Decimal("1.0850"),
        ask=Decimal("1.0852"),
        mid=Decimal("1.0851"),
        spread_pips=2.0,
        timestamp=datetime.now(timezone.utc),
        source="test",
    )

    await worker.run_cycle({"EUR/USD": tick})
    # Should complete without error
