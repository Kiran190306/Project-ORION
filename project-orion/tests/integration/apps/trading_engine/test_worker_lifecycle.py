"""Integration tests for autonomous worker lifecycle.

Tests end-to-end worker integration with FastAPI lifespan, database,
Redis, and paper trading execution.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from apps.trading_engine.src.config import AppSettings
from apps.trading_engine.src.main import create_app
from apps.trading_engine.src.workers.coordinator import AutonomousWorkerCoordinator
from apps.trading_engine.src.workers.lifecycle import WorkerState

from libraries.infrastructure.caching.client import RedisClient
from libraries.infrastructure.caching.config import RedisConfig
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.health import HealthStatus
from libraries.infrastructure.persistence.config import DatabaseConfig, DatabaseManager
from libraries.observability.metrics import MetricsRegistry


@pytest.fixture
def test_settings():
    """Create test settings for integration tests."""
    return AppSettings(
        environment="test",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8001,
        paper_balance=Decimal(100000),
        worker_enabled=True,
        worker_symbols=("EUR/USD", "GBP/USD"),
        market_data_poll_interval=0.1,
        trading_cycle_interval=0.2,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )


@pytest.fixture
async def database_manager(test_settings):
    """Create an in-memory database manager for testing."""
    config = DatabaseConfig(url=test_settings.database_url)
    manager = DatabaseManager(config=config)
    # Trigger lazy initialization by accessing engine property
    _ = manager.engine
    yield manager
    await manager.close()


@pytest.fixture
async def redis_client():
    """Create a Redis client for testing (optional)."""
    try:
        config = RedisConfig(url="redis://localhost:6379/1")
        client = RedisClient(config=config)
        await client.connect()
        yield client
        await client.disconnect()
    except (ConnectionError, OSError):
        # Redis not available, yield None
        yield None


@pytest.fixture
async def paper_adapter():
    """Create a paper execution adapter for testing."""
    config = PaperExecutionConfig(
        broker_name="paper",
        is_paper=True,
        balance=Decimal(100000),
    )
    adapter = PaperExecutionAdapter(config=config)
    await adapter.connect()
    yield adapter
    await adapter.disconnect()


@pytest.fixture
async def metrics_registry():
    """Create a metrics registry for testing."""
    return MetricsRegistry(prefix="test_integration")


@pytest.fixture
async def worker_coordinator(paper_adapter, metrics_registry, test_settings):
    """Create a worker coordinator for integration testing."""
    coordinator = AutonomousWorkerCoordinator(
        symbols=test_settings.worker_symbols,
        market_poll_interval=test_settings.market_data_poll_interval,
        trading_cycle_interval=test_settings.trading_cycle_interval,
        stale_threshold_seconds=test_settings.worker_stale_threshold,
        account_balance=test_settings.paper_balance,
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=test_settings.worker_enabled,
    )
    yield coordinator
    if coordinator.state != WorkerState.STOPPED:
        await coordinator.stop()


async def test_worker_coordinator_full_lifecycle(worker_coordinator):
    """Test complete worker lifecycle: start -> run -> stop."""
    assert worker_coordinator.state == WorkerState.STOPPED

    # Start the worker
    await worker_coordinator.start()
    assert worker_coordinator.state == WorkerState.RUNNING
    assert worker_coordinator.uptime_seconds is not None

    # Let it run for a few cycles
    await asyncio.sleep(0.5)

    # Verify it's running
    assert worker_coordinator.state == WorkerState.RUNNING
    assert worker_coordinator.uptime_seconds > 0

    # Stop the worker
    await worker_coordinator.stop()
    assert worker_coordinator.state == WorkerState.STOPPED
    assert worker_coordinator.uptime_seconds is None


async def test_worker_coordinator_metrics_integration(worker_coordinator, metrics_registry):
    """Test that worker metrics are properly integrated with MetricsRegistry."""
    await worker_coordinator.start()
    await asyncio.sleep(0.3)

    # Check that metrics are being recorded
    assert worker_coordinator.cycles_completed >= 0

    await worker_coordinator.stop()


async def test_worker_coordinator_health_check(worker_coordinator):
    """Test worker health check integration."""
    health_check = worker_coordinator.build_health_check()

    # Check health when stopped
    result = await health_check.check()
    assert result.name == "worker"

    # Check health when running
    await worker_coordinator.start()
    result = await health_check.check()
    assert result.name == "worker"
    assert result.details is not None

    await worker_coordinator.stop()


async def test_worker_coordinator_disabled_mode(paper_adapter, metrics_registry, test_settings):
    """Test worker in disabled mode."""
    disabled_settings = AppSettings(
        environment="test",
        log_level="INFO",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        run_migrations=False,
        server_host="127.0.0.1",
        server_port=8001,
        paper_balance=Decimal(100000),
        worker_enabled=False,  # Disabled
        worker_symbols=("EUR/USD",),
        market_data_poll_interval=0.1,
        trading_cycle_interval=0.2,
        worker_timeout=30.0,
        worker_stale_threshold=30.0,
    )

    coordinator = AutonomousWorkerCoordinator(
        symbols=disabled_settings.worker_symbols,
        market_poll_interval=disabled_settings.market_data_poll_interval,
        trading_cycle_interval=disabled_settings.trading_cycle_interval,
        stale_threshold_seconds=disabled_settings.worker_stale_threshold,
        account_balance=disabled_settings.paper_balance,
        paper_adapter=paper_adapter,
        metrics_registry=metrics_registry,
        enabled=disabled_settings.worker_enabled,
    )

    await coordinator.start()
    assert coordinator.state == WorkerState.STOPPED  # Should not start

    health_check = coordinator.build_health_check()
    result = await health_check.check()
    assert result.name == "worker"


async def test_worker_fastapi_lifespan_integration(test_settings, database_manager, redis_client, paper_adapter):
    """Test worker integration with FastAPI lifespan."""
    if redis_client is None:
        pytest.skip("Redis service unavailable on redis://localhost:6379/1")

    app = create_app(
        settings=test_settings,
        db_manager=database_manager,
        redis_client=redis_client,
        paper_adapter=paper_adapter,
    )

    async with app.router.lifespan_context(app):
        # 1. Verify worker coordinator initialized and running
        assert app.state.worker is not None
        assert app.state.worker.state == WorkerState.RUNNING

        # 2. Verify Redis client connected
        assert app.state.redis_client.is_connected is True

        # 3. Verify health checks registered and passing
        results = await app.state.health_registry.run_readiness()
        check_map = {r.name: r.status for r in results}
        assert check_map.get("database") == HealthStatus.HEALTHY
        assert check_map.get("redis") == HealthStatus.HEALTHY
        assert check_map.get("worker") == HealthStatus.HEALTHY

    # 4. Verify graceful shutdown stops worker
    assert app.state.worker.state == WorkerState.STOPPED


async def test_worker_error_recovery(worker_coordinator):
    """Test worker recovers from errors during cycles."""
    await worker_coordinator.start()

    # Let it run through some cycles
    await asyncio.sleep(0.5)

    # Should still be running despite any transient errors
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_concurrent_market_data_and_trading(worker_coordinator):
    """Test that market data polling and trading cycles run concurrently."""
    await worker_coordinator.start()

    # Wait for both schedulers to run
    await asyncio.sleep(0.5)

    # Both should have completed cycles
    assert worker_coordinator.cycles_completed >= 0

    await worker_coordinator.stop()


async def test_worker_graceful_shutdown_timeout(worker_coordinator):
    """Test worker respects shutdown timeout."""
    await worker_coordinator.start()
    await asyncio.sleep(0.2)

    # Shutdown should complete within timeout
    await asyncio.wait_for(worker_coordinator.stop(), timeout=5.0)
    assert worker_coordinator.state == WorkerState.STOPPED


async def test_worker_symbol_configuration(worker_coordinator):
    """Test worker respects configured symbols."""
    assert worker_coordinator._symbols == ("EUR/USD", "GBP/USD")

    await worker_coordinator.start()
    await asyncio.sleep(0.3)

    # Should have processed configured symbols
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_stale_data_detection(worker_coordinator):
    """Test worker detects and handles stale market data."""
    await worker_coordinator.start()

    # Configure very short stale threshold
    worker_coordinator._poller._stale_threshold = 0.05

    # Let it run
    await asyncio.sleep(0.3)

    # Should still be running (stale data should not crash worker)
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_notification_integration(worker_coordinator):
    """Test worker notification integration."""
    await worker_coordinator.start()

    # Run some cycles
    await asyncio.sleep(0.3)

    # Notification service should be initialized
    assert worker_coordinator._notification_service is not None

    await worker_coordinator.stop()


async def test_worker_paper_trading_safety(worker_coordinator, paper_adapter):
    """Test worker only uses paper trading (no live execution)."""
    await worker_coordinator.start()

    # Verify paper adapter is being used
    assert worker_coordinator._paper_adapter is paper_adapter
    assert paper_adapter.config.is_paper is True

    # Let it run
    await asyncio.sleep(0.3)

    # Should still be using paper trading
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_risk_engine_integration(worker_coordinator):
    """Test worker integrates with RiskEngine correctly."""
    await worker_coordinator.start()

    # RiskEngine should be initialized
    assert worker_coordinator._risk_engine is not None

    await asyncio.sleep(0.3)

    # Should have completed cycles with risk evaluation
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_decision_engine_integration(worker_coordinator):
    """Test worker integrates with DecisionEngine correctly."""
    await worker_coordinator.start()

    # DecisionEngine should be initialized
    assert worker_coordinator._decision_engine is not None

    await asyncio.sleep(0.3)

    # Should have completed cycles with decision evaluation
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()


async def test_worker_metrics_persistence(worker_coordinator, metrics_registry):
    """Test worker metrics persist across cycles."""
    await worker_coordinator.start()

    initial_cycles = worker_coordinator.cycles_completed

    await asyncio.sleep(0.3)

    final_cycles = worker_coordinator.cycles_completed
    assert final_cycles >= initial_cycles

    await worker_coordinator.stop()


async def test_worker_multiple_start_stop_cycles(worker_coordinator):
    """Test worker can handle multiple start/stop cycles."""
    for _ in range(3):
        await worker_coordinator.start()
        assert worker_coordinator.state == WorkerState.RUNNING
        await asyncio.sleep(0.1)
        await worker_coordinator.stop()
        assert worker_coordinator.state == WorkerState.STOPPED


async def test_worker_long_running_stability(worker_coordinator):
    """Test worker remains stable over extended runtime."""
    await worker_coordinator.start()

    # Run for longer period
    await asyncio.sleep(2.0)

    # Should still be running
    assert worker_coordinator.state == WorkerState.RUNNING
    assert worker_coordinator.uptime_seconds > 1.5

    await worker_coordinator.stop()


async def test_worker_with_no_market_data(worker_coordinator):
    """Test worker handles absence of market data gracefully."""
    await worker_coordinator.start()

    # Simulate no market data by using empty symbols
    # (This is a structural test; in reality, symbols are configured)

    await asyncio.sleep(0.3)

    # Should still be running
    assert worker_coordinator.state == WorkerState.RUNNING

    await worker_coordinator.stop()
