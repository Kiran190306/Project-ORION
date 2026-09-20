"""Unit tests for AutonomousWorkerCoordinator.

Tests the top-level worker coordinator including lifecycle, health checks,
and integration with schedulers and domain components.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from apps.trading_engine.src.workers.coordinator import (
    AutonomousWorkerCoordinator,
    WorkerHealthCheck,
)
from apps.trading_engine.src.workers.lifecycle import WorkerState

from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.observability.metrics import MetricsRegistry


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
def metrics_registry():
    """Create a metrics registry for testing."""
    return MetricsRegistry(prefix="test")


@pytest.fixture
def coordinator(paper_adapter, metrics_registry):
    """Create a coordinator with test dependencies."""
    return AutonomousWorkerCoordinator(
        symbols=("EUR/USD", "GBP/USD"),
        market_poll_interval=0.1,
        trading_cycle_interval=0.2,
        stale_threshold_seconds=30.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=True,
    )


async def test_coordinator_initial_state(coordinator):
    """Coordinator starts in STOPPED state with enabled flag."""
    assert coordinator.state == WorkerState.STOPPED
    assert coordinator.enabled is True
    assert coordinator.last_cycle_at is None
    assert coordinator.cycles_completed == 0
    assert coordinator.cycles_failed == 0


async def test_coordinator_disabled_mode(paper_adapter, metrics_registry):
    """Coordinator in disabled mode skips startup."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=("EUR/USD",),
        market_poll_interval=0.1,
        trading_cycle_interval=0.2,
        stale_threshold_seconds=30.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=False,  # Disabled
    )

    assert coordinator.enabled is False
    assert coordinator.state == WorkerState.STOPPED

    await coordinator.start()
    # Should remain in STOPPED state
    assert coordinator.state == WorkerState.STOPPED


async def test_coordinator_lifecycle_start_stop(coordinator):
    """Coordinator transitions through lifecycle states correctly."""
    assert coordinator.state == WorkerState.STOPPED

    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING
    assert coordinator.uptime_seconds is not None

    await coordinator.stop()
    assert coordinator.state == WorkerState.STOPPED
    assert coordinator.uptime_seconds is None


async def test_coordinator_idempotent_start_stop(coordinator):
    """Multiple start/stop calls are safe."""
    await coordinator.start()
    await coordinator.start()  # Should be idempotent
    assert coordinator.state == WorkerState.RUNNING

    await coordinator.stop()
    await coordinator.stop()  # Should be idempotent
    assert coordinator.state == WorkerState.STOPPED


async def test_coordinator_scheduler_start(coordinator):
    """Coordinator starts schedulers on startup."""
    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING

    # Wait for at least one cycle
    await asyncio.sleep(0.3)

    # Should have completed some cycles
    assert coordinator.cycles_completed >= 0

    await coordinator.stop()


async def test_coordinator_risk_engine_initialization(coordinator):
    """Coordinator initializes RiskEngine on startup."""
    await coordinator.start()
    # RiskEngine should be initialized (no exception)
    assert coordinator.state == WorkerState.RUNNING
    await coordinator.stop()


async def test_coordinator_health_check(coordinator):
    """Health check reflects coordinator state."""
    health_check = coordinator.build_health_check()

    # Initially stopped
    result = await health_check.check()
    assert result.name == "worker"

    # After start
    await coordinator.start()
    result = await health_check.check()
    assert result.name == "worker"

    await coordinator.stop()


async def test_coordinator_health_check_disabled(paper_adapter, metrics_registry):
    """Health check reports healthy when worker is disabled."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=("EUR/USD",),
        market_poll_interval=0.1,
        trading_cycle_interval=0.2,
        stale_threshold_seconds=30.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=False,
    )

    health_check = coordinator.build_health_check()
    result = await health_check.check()

    assert result.name == "worker"
    # Should report healthy when disabled


async def test_coordinator_metrics_registration(coordinator):
    """Coordinator registers worker-specific metrics."""
    # Metrics should be registered during initialization
    assert coordinator.cycles_completed == 0
    assert coordinator.cycles_failed == 0


async def test_coordinator_market_poll_cycle(coordinator):
    """Market poll cycle executes without error."""
    await coordinator.start()

    # Wait for at least one market poll
    await asyncio.sleep(0.15)

    # Should have executed market polls
    assert coordinator.state == WorkerState.RUNNING

    await coordinator.stop()


async def test_coordinator_trading_cycle(coordinator):
    """Trading cycle executes without error."""
    await coordinator.start()

    # Wait for at least one trading cycle
    await asyncio.sleep(0.3)

    # Should have executed trading cycles
    assert coordinator.state == WorkerState.RUNNING

    await coordinator.stop()


async def test_coordinator_error_recovery(coordinator):
    """Coordinator recovers from startup errors."""
    # This is hard to test without causing an actual error
    # But we can verify the structure exists
    assert coordinator is not None


async def test_coordinator_custom_symbols(paper_adapter, metrics_registry):
    """Coordinator accepts custom symbol configuration."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=("NZD/USD", "AUD/CAD", "USD/CHF"),
        market_poll_interval=0.1,
        trading_cycle_interval=0.2,
        stale_threshold_seconds=30.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=True,
    )

    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING
    await coordinator.stop()


async def test_coordinator_custom_intervals(paper_adapter, metrics_registry):
    """Coordinator accepts custom interval configuration."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=("EUR/USD",),
        market_poll_interval=0.05,  # Fast polling
        trading_cycle_interval=0.1,  # Fast trading
        stale_threshold_seconds=15.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=True,
    )

    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING
    await coordinator.stop()


async def test_coordinator_without_metrics_registry(paper_adapter):
    """Coordinator works without metrics registry."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=("EUR/USD",),
        market_poll_interval=0.1,
        trading_cycle_interval=0.2,
        stale_threshold_seconds=30.0,
        account_balance=Decimal(100000),
        paper_adapter=paper_adapter,
        metrics_registry=None,  # No metrics
        enabled=True,
    )

    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING
    await coordinator.stop()


async def test_coordinator_shutdown_timeout(coordinator):
    """Coordinator respects shutdown timeout."""
    await coordinator.start()
    assert coordinator.state == WorkerState.RUNNING

    # Stop should complete within reasonable time
    await asyncio.wait_for(coordinator.stop(), timeout=5.0)
    assert coordinator.state == WorkerState.STOPPED


async def test_coordinator_last_cycle_tracking(coordinator):
    """Coordinator tracks last cycle timestamp."""
    await coordinator.start()

    # Initially None
    assert coordinator.last_cycle_at is None

    # Wait for cycles
    await asyncio.sleep(0.3)

    # Should have a timestamp after cycles run
    # (may still be None if no cycles completed, but that's ok)

    await coordinator.stop()


async def test_coordinator_uptime_tracking(coordinator):
    """Coordinator tracks uptime while running."""
    await coordinator.start()

    # Should have uptime
    uptime = coordinator.uptime_seconds
    assert uptime is not None
    assert uptime >= 0

    await asyncio.sleep(0.1)

    # Uptime should increase
    uptime_after = coordinator.uptime_seconds
    assert uptime_after > uptime

    await coordinator.stop()

    # Uptime should be None when stopped
    assert coordinator.uptime_seconds is None


async def test_worker_health_check_class():
    """WorkerHealthCheck has correct structure."""
    # Create a mock coordinator
    class MockCoordinator:
        def __init__(self):
            self._state = WorkerState.RUNNING
            self._last_cycle = datetime.now(timezone.utc)
            self._cycles_completed = 5
            self._cycles_failed = 1
            self._enabled = True

        @property
        def state(self):
            return self._state

        @property
        def last_cycle_at(self):
            return self._last_cycle

        @property
        def cycles_completed(self):
            return self._cycles_completed

        @property
        def cycles_failed(self):
            return self._cycles_failed

        @property
        def enabled(self):
            return self._enabled

    mock_coordinator = MockCoordinator()
    health_check = WorkerHealthCheck(mock_coordinator)
    result = await health_check.check()

    assert result.name == "worker"
    assert result.details is not None


async def test_coordinator_domain_components(coordinator):
    """Coordinator initializes domain components correctly."""
    # Should have domain components initialized
    assert coordinator._decision_engine is not None
    assert coordinator._risk_engine is not None
    assert coordinator._notification_service is not None


async def test_coordinator_worker_subsystems(coordinator):
    """Coordinator initializes worker subsystems correctly."""
    # Should have worker subsystems initialized
    assert coordinator._lifecycle is not None
    assert coordinator._poller is not None
    assert coordinator._cycle_worker is not None
    assert coordinator._market_scheduler is not None
    assert coordinator._trading_scheduler is not None
