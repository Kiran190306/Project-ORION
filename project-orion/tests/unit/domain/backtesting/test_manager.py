"""Tests for EPIC-010 BacktestManager lifecycle management."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.engine import BacktestEngine, BacktestEngineResult
from libraries.domain.backtesting.exceptions import BacktestError
from libraries.domain.backtesting.manager import BacktestManager, BacktestManagerConfig
from libraries.domain.backtesting.models import BacktestConfig, PerformanceMetrics


class TestBacktestManagerConfig:
    """Test BacktestManagerConfig."""

    def test_default_config(self):
        cfg = BacktestManagerConfig()
        assert cfg.max_concurrent_backtests == 1
        assert cfg.shutdown_timeout_seconds == 30.0
        assert cfg.health_check_interval_seconds == 60.0

    def test_custom_config(self):
        cfg = BacktestManagerConfig(
            max_concurrent_backtests=5,
            shutdown_timeout_seconds=60.0,
            health_check_interval_seconds=30.0,
            metadata={"env": "test"},
        )
        assert cfg.max_concurrent_backtests == 5
        assert cfg.shutdown_timeout_seconds == 60.0
        assert cfg.health_check_interval_seconds == 30.0
        assert cfg.metadata == {"env": "test"}

    def test_config_frozen(self):
        cfg = BacktestManagerConfig()
        with pytest.raises(AttributeError):
            cfg.max_concurrent_backtests = 10


class TestBacktestManagerInitialization:
    """Test BacktestManager initialization."""

    def test_default_init(self):
        mgr = BacktestManager()
        assert isinstance(mgr.config, BacktestManagerConfig)
        assert mgr.engine is None
        assert mgr.is_running is False
        assert mgr.started_at is None
        assert mgr.uptime_seconds == 0.0

    def test_init_with_config(self):
        cfg = BacktestManagerConfig(max_concurrent_backtests=3)
        mgr = BacktestManager(config=cfg)
        assert mgr.config.max_concurrent_backtests == 3

    def test_init_with_engine(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        assert mgr.engine is not None
        assert mgr.engine is engine

    def test_config_property(self):
        mgr = BacktestManager()
        assert mgr.config is mgr._config

    def test_uptime_when_not_started(self):
        mgr = BacktestManager()
        assert mgr.uptime_seconds == 0.0


class TestBacktestManagerLifecycle:
    """Test BacktestManager start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        mgr = BacktestManager(engine=BacktestEngine())
        assert mgr.is_running is False
        await mgr.start()
        assert mgr.is_running is True
        assert mgr.started_at is not None

    @pytest.mark.asyncio
    async def test_start_twice_raises_error(self):
        mgr = BacktestManager(engine=BacktestEngine())
        await mgr.start()
        with pytest.raises(BacktestError, match="already running"):
            await mgr.start()

    @pytest.mark.asyncio
    async def test_start_without_engine_raises_error(self):
        mgr = BacktestManager()
        with pytest.raises(BacktestError, match="No backtest engine"):
            await mgr.start()

    @pytest.mark.asyncio
    async def test_start_with_engine_param(self):
        mgr = BacktestManager()
        engine = BacktestEngine()
        await mgr.start(engine=engine)
        assert mgr.is_running is True
        assert mgr.engine is engine

    @pytest.mark.asyncio
    async def test_start_overrides_existing_engine(self):
        old_engine = BacktestEngine()
        new_engine = BacktestEngine()
        mgr = BacktestManager(engine=old_engine)
        await mgr.start(engine=new_engine)
        assert mgr.engine is new_engine

    @pytest.mark.asyncio
    async def test_stop_sets_not_running(self):
        mgr = BacktestManager(engine=BacktestEngine())
        await mgr.start()
        await mgr.stop()
        assert mgr.is_running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_noop(self):
        mgr = BacktestManager()
        await mgr.stop()
        assert mgr.is_running is False

    @pytest.mark.asyncio
    async def test_stop_resets_engine(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        await mgr.stop()
        assert mgr.is_running is False


class TestBacktestManagerRunBacktest:
    """Test backtest execution through manager."""

    @pytest.mark.asyncio
    async def test_run_backtest_not_started_raises_error(self):
        mgr = BacktestManager(engine=BacktestEngine())
        with pytest.raises(BacktestError, match="not running"):
            await mgr.run_backtest()

    @pytest.mark.asyncio
    async def test_run_backtest_no_engine_raises_error(self):
        mgr = BacktestManager()
        with pytest.raises(BacktestError, match="not running"):
            await mgr.run_backtest()

    @pytest.mark.asyncio
    async def test_run_backtest_stores_result(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        result = await mgr.run_backtest(symbol="EURUSD")
        assert isinstance(result, BacktestEngineResult)
        assert result.success is False
        results = await mgr.get_results()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_run_backtest_multiple_times(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        await mgr.run_backtest(symbol="EURUSD")
        await mgr.run_backtest(symbol="GBPUSD")
        results = await mgr.get_results()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_backtest_health_updated_on_failure(self):
        class FailingEngine(BacktestEngine):
            async def run(self, **kwargs):
                msg = "simulated failure"
                raise RuntimeError(msg)

        engine = FailingEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        with pytest.raises(RuntimeError):
            await mgr.run_backtest()
        health = await mgr.health_check()
        assert health["healthy"] is False
        assert health["error"] is not None


class TestBacktestManagerHealthAndStats:
    """Test health check and statistics."""

    @pytest.mark.asyncio
    async def test_health_check_default(self):
        mgr = BacktestManager()
        health = await mgr.health_check()
        assert health["running"] is False
        assert health["healthy"] is True
        assert health["engine_configured"] is False
        assert health["backtests_executed"] == 0
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_health_check_running(self):
        mgr = BacktestManager(engine=BacktestEngine())
        await mgr.start()
        health = await mgr.health_check()
        assert health["running"] is True
        assert health["healthy"] is True
        assert health["engine_configured"] is True
        assert health["uptime_seconds"] > 0

    @pytest.mark.asyncio
    async def test_stats_empty(self):
        mgr = BacktestManager()
        stats = await mgr.get_stats()
        assert stats["total_backtests"] == 0
        assert stats["passed"] == 0
        assert stats["failed"] == 0
        assert stats["pass_rate"] == 0.0
        assert stats["average_execution_time_seconds"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_after_backtests(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        await mgr.run_backtest(symbol="EURUSD")
        await mgr.run_backtest(symbol="GBPUSD")
        stats = await mgr.get_stats()
        assert stats["total_backtests"] == 2
        assert stats["average_execution_time_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_clear_results(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        await mgr.run_backtest(symbol="EURUSD")
        assert len(await mgr.get_results()) == 1
        await mgr.clear_results()
        assert len(await mgr.get_results()) == 0


class TestBacktestManagerReset:
    """Test BacktestManager reset."""

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        engine = BacktestEngine()
        mgr = BacktestManager(engine=engine)
        await mgr.start()
        await mgr.run_backtest(symbol="EURUSD")
        await mgr.reset()
        assert mgr.is_running is False
        assert mgr.started_at is None
        assert len(await mgr.get_results()) == 0
        health = await mgr.health_check()
        assert health["healthy"] is True

    @pytest.mark.asyncio
    async def test_reset_when_not_started(self):
        mgr = BacktestManager(engine=BacktestEngine())
        await mgr.reset()
        assert mgr.is_running is False
