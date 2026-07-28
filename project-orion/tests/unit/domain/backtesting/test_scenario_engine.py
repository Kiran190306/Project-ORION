"""Tests for EPIC-010 ScenarioEngine — stress testing scenarios."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    PerformanceMetrics,
    ScenarioConfig,
    ScenarioEffect,
    ScenarioResult,
)
from libraries.domain.backtesting.scenario_engine import ScenarioEngine


class TestScenarioEngineInitialization:
    """Test scenario engine creation."""

    def test_default_init(self):
        engine = ScenarioEngine()
        assert engine._scenarios == {}
        assert engine._results == {}

    def test_get_summary_empty(self):
        engine = ScenarioEngine()
        summary = engine.get_summary()
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["failed"] == 0
        assert summary["pass_rate"] == 0.0


class TestScenarioEngineRegistration:
    """Test scenario registration."""

    def test_register_scenario(self):
        engine = ScenarioEngine()
        config = ScenarioConfig(
            name="test_scenario",
            effects=(ScenarioEffect.HIGH_VOLATILITY,),
            start_delay_bars=0,
            duration_bars=10,
            intensity=1.0,
        )
        engine.register_scenario(config)
        assert "test_scenario" in engine._scenarios
        assert engine._scenarios["test_scenario"].name == "test_scenario"

    def test_register_multiple_scenarios(self):
        engine = ScenarioEngine()
        for name in ["s1", "s2", "s3"]:
            engine.register_scenario(ScenarioConfig(name=name, effects=()))
        assert len(engine._scenarios) == 3

    def test_register_duplicate_overwrites(self):
        engine = ScenarioEngine()
        config1 = ScenarioConfig(
            name="dup", effects=(ScenarioEffect.HIGH_VOLATILITY,), intensity=1.0
        )
        config2 = ScenarioConfig(name="dup", effects=(ScenarioEffect.LOW_LIQUIDITY,), intensity=2.0)
        engine.register_scenario(config1)
        engine.register_scenario(config2)
        assert engine._scenarios["dup"].effects[0] == ScenarioEffect.LOW_LIQUIDITY

    def test_register_default_scenarios(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        expected = [
            "high_volatility",
            "low_liquidity",
            "spread_spike",
            "flash_crash",
            "news_event",
            "broker_disconnect",
            "gap_open",
        ]
        for name in expected:
            assert name in engine._scenarios, f"Missing default scenario: {name}"
        assert len(engine._scenarios) == 7


class TestScenarioEngineTypes:
    """Test all default scenario configurations."""

    def test_high_volatility_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["high_volatility"]
        assert cfg.intensity == 2.0
        assert cfg.duration_bars == 50
        assert cfg.parameters["volatility_multiplier"] == 2.0

    def test_low_liquidity_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["low_liquidity"]
        assert cfg.intensity == 0.3
        assert cfg.duration_bars == 30

    def test_spread_spike_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["spread_spike"]
        assert cfg.intensity == 5.0
        assert cfg.duration_bars == 10
        assert cfg.parameters["spread_multiplier"] == 5.0

    def test_flash_crash_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["flash_crash"]
        assert cfg.intensity == 1.0
        assert cfg.duration_bars == 20
        assert cfg.parameters["price_drop_pct"] == 5.0

    def test_news_event_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["news_event"]
        assert cfg.intensity == 3.0
        assert cfg.duration_bars == 15

    def test_broker_disconnect_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["broker_disconnect"]
        assert cfg.intensity == 1.0
        assert cfg.duration_bars == 60
        assert cfg.parameters["disconnect_seconds"] == 60

    def test_gap_open_scenario(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        cfg = engine._scenarios["gap_open"]
        assert cfg.intensity == 20.0
        assert cfg.duration_bars == 1
        assert cfg.parameters["direction"] == "up"
        assert cfg.parameters["gap_pips"] == 20.0


class TestScenarioEngineExecution:
    """Test scenario execution."""

    @pytest.mark.asyncio
    async def test_execute_registered_scenario(self):
        engine = ScenarioEngine()
        config = ScenarioConfig(name="my_scenario", effects=(ScenarioEffect.HIGH_VOLATILITY,))
        engine.register_scenario(config)
        result = await engine.execute_scenario("my_scenario")
        assert isinstance(result, ScenarioResult)
        assert result.scenario_name == "my_scenario"
        assert result.survived is True

    @pytest.mark.asyncio
    async def test_execute_unregistered_scenario_raises(self):
        engine = ScenarioEngine()
        with pytest.raises(ValueError, match="Scenario 'unknown' not registered"):
            await engine.execute_scenario("unknown")

    @pytest.mark.asyncio
    async def test_execute_with_normal_performance(self):
        engine = ScenarioEngine()
        config = ScenarioConfig(name="test", effects=())
        engine.register_scenario(config)
        normal = PerformanceMetrics()
        result = await engine.execute_scenario("test", normal_performance=normal)
        assert result.normal_metrics is normal

    @pytest.mark.asyncio
    async def test_execute_stores_result(self):
        engine = ScenarioEngine()
        config = ScenarioConfig(name="test", effects=())
        engine.register_scenario(config)
        await engine.execute_scenario("test")
        assert engine.get_result("test") is not None
        assert engine.get_result("test").scenario_name == "test"

    @pytest.mark.asyncio
    async def test_get_result_nonexistent(self):
        engine = ScenarioEngine()
        result = engine.get_result("nonexistent")
        assert result is None


class TestScenarioEngineExecuteAll:
    """Test executing all scenarios."""

    @pytest.mark.asyncio
    async def test_execute_all_with_no_scenarios(self):
        engine = ScenarioEngine()
        results = await engine.execute_all()
        assert results == {}

    @pytest.mark.asyncio
    async def test_execute_all_default_scenarios(self):
        engine = ScenarioEngine()
        engine.register_default_scenarios()
        results = await engine.execute_all()
        assert len(results) == 7
        for name in [
            "high_volatility",
            "low_liquidity",
            "spread_spike",
            "flash_crash",
            "news_event",
            "broker_disconnect",
            "gap_open",
        ]:
            assert name in results, f"Missing result for {name}"
            assert isinstance(results[name], ScenarioResult)

    @pytest.mark.asyncio
    async def test_execute_all_custom_scenarios(self):
        engine = ScenarioEngine()
        for i in range(5):
            engine.register_scenario(ScenarioConfig(name=f"scenario_{i}", effects=()))
        results = await engine.execute_all()
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_execute_all_with_normal_performance(self):
        engine = ScenarioEngine()
        engine.register_scenario(ScenarioConfig(name="test", effects=()))
        normal = PerformanceMetrics()
        results = await engine.execute_all(normal_performance=normal)
        assert results["test"].normal_metrics is normal


class TestScenarioEngineSummary:
    """Test scenario summary generation."""

    @pytest.mark.asyncio
    async def test_summary_all_passed(self):
        engine = ScenarioEngine()
        engine.register_scenario(ScenarioConfig(name="s1", effects=()))
        engine.register_scenario(ScenarioConfig(name="s2", effects=()))
        await engine.execute_all()
        summary = engine.get_summary()
        assert summary["total"] == 2
        assert summary["passed"] == 2
        assert summary["failed"] == 0
        assert summary["pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_summary_no_results(self):
        engine = ScenarioEngine()
        summary = engine.get_summary()
        assert summary["total"] == 0
        assert summary["pass_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_clear_results(self):
        engine = ScenarioEngine()
        engine.register_scenario(ScenarioConfig(name="test", effects=()))
        await engine.execute_scenario("test")
        assert len(engine._results) == 1
        engine.clear_results()
        assert len(engine._results) == 0
        summary = engine.get_summary()
        assert summary["total"] == 0


class TestScenarioEngineEdgeCases:
    """Test edge cases."""

    def test_scenario_config_minimal(self):
        config = ScenarioConfig(name="minimal")
        assert config.name == "minimal"
        assert config.effects == ()
        assert config.intensity == 1.0
        assert config.duration_bars == 0

    def test_scenario_config_with_effects(self):
        effects = (ScenarioEffect.HIGH_VOLATILITY, ScenarioEffect.LOW_LIQUIDITY)
        config = ScenarioConfig(name="combo", effects=effects)
        assert len(config.effects) == 2

    def test_scenario_result_defaults(self):
        result = ScenarioResult(scenario_name="test", effects=())
        assert result.survived is True
        assert result.impact_score == 0.0
        assert result.max_drawdown_during_scenario == 0.0
        assert result.pnl_during_scenario == 0.0

    def test_scenario_result_custom_values(self):
        result = ScenarioResult(
            scenario_name="test",
            effects=(),
            survived=False,
            impact_score=0.8,
            max_drawdown_during_scenario=25.0,
            pnl_during_scenario=-5000.0,
        )
        assert result.survived is False
        assert result.impact_score == 0.8
        assert result.max_drawdown_during_scenario == 25.0
        assert result.pnl_during_scenario == -5000.0

    def test_scenario_effect_enum_values(self):
        assert ScenarioEffect.HIGH_VOLATILITY.value == "high_volatility"
        assert ScenarioEffect.LOW_LIQUIDITY.value == "low_liquidity"
        assert ScenarioEffect.SPREAD_SPIKE.value == "spread_spike"
        assert ScenarioEffect.FLASH_CRASH.value == "flash_crash"
        assert ScenarioEffect.NEWS_EVENT.value == "news_event"
        assert ScenarioEffect.BROKER_DISCONNECT.value == "broker_disconnect"
        assert ScenarioEffect.GAP_OPEN.value == "gap_open"
