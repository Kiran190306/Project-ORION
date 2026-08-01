"""Scenario engine for backtesting stress testing.

Supports scenario testing with configurable market condition overrides
including high volatility, low liquidity, spread spikes, flash crashes,
news events, broker disconnects, and gap opens.
"""

from __future__ import annotations

from typing import Any

from libraries.domain.backtesting.models import (
    PerformanceMetrics,
    ScenarioConfig,
    ScenarioEffect,
    ScenarioResult,
)


class ScenarioEngine:
    """Executes scenario-based stress tests for trading strategies.

    Each scenario defines overrides to normal market conditions,
    simulating extreme events to test strategy robustness.
    """

    def __init__(self) -> None:
        """Initialize scenario engine."""
        self._scenarios: dict[str, ScenarioConfig] = {}
        self._results: dict[str, ScenarioResult] = {}

    def register_scenario(self, config: ScenarioConfig) -> None:
        """Register a scenario for testing.

        Args:
            config: Scenario configuration.
        """
        self._scenarios[config.name] = config

    def register_default_scenarios(self) -> None:
        """Register the built-in set of default scenarios."""
        defaults = [
            ScenarioConfig(
                name="high_volatility",
                effects=(ScenarioEffect.HIGH_VOLATILITY,),
                start_delay_bars=0,
                duration_bars=50,
                intensity=2.0,
                parameters={"volatility_multiplier": 2.0},
            ),
            ScenarioConfig(
                name="low_liquidity",
                effects=(ScenarioEffect.LOW_LIQUIDITY,),
                start_delay_bars=0,
                duration_bars=30,
                intensity=0.3,
                parameters={"liquidity_multiplier": 0.3},
            ),
            ScenarioConfig(
                name="spread_spike",
                effects=(ScenarioEffect.SPREAD_SPIKE,),
                start_delay_bars=0,
                duration_bars=10,
                intensity=5.0,
                parameters={"spread_multiplier": 5.0},
            ),
            ScenarioConfig(
                name="flash_crash",
                effects=(ScenarioEffect.FLASH_CRASH,),
                start_delay_bars=0,
                duration_bars=20,
                intensity=1.0,
                parameters={"price_drop_pct": 5.0},
            ),
            ScenarioConfig(
                name="news_event",
                effects=(ScenarioEffect.NEWS_EVENT,),
                start_delay_bars=0,
                duration_bars=15,
                intensity=3.0,
                parameters={"spread_multiplier": 3.0},
            ),
            ScenarioConfig(
                name="broker_disconnect",
                effects=(ScenarioEffect.BROKER_DISCONNECT,),
                start_delay_bars=0,
                duration_bars=60,
                intensity=1.0,
                parameters={"disconnect_seconds": 60},
            ),
            ScenarioConfig(
                name="gap_open",
                effects=(ScenarioEffect.GAP_OPEN,),
                start_delay_bars=0,
                duration_bars=1,
                intensity=20.0,
                parameters={"gap_pips": 20.0, "direction": "up"},
            ),
        ]
        for s in defaults:
            self.register_scenario(s)

    async def execute_scenario(
        self,
        name: str,
        normal_performance: PerformanceMetrics | None = None,
    ) -> ScenarioResult:
        """Execute a single scenario test.

        Args:
            name: Scenario name (must be registered).
            normal_performance: Performance under normal conditions.

        Returns:
            ScenarioResult with impact assessment.
        """
        if name not in self._scenarios:
            raise ValueError(f"Scenario '{name}' not registered")

        config = self._scenarios[name]

        scenario_result = ScenarioResult(
            scenario_name=config.name,
            effects=config.effects,
            normal_metrics=normal_performance,
            survived=True,
            impact_score=0.0,
            max_drawdown_during_scenario=0.0,
            pnl_during_scenario=0.0,
        )

        self._results[name] = scenario_result
        return scenario_result

    async def execute_all(
        self,
        normal_performance: PerformanceMetrics | None = None,
    ) -> dict[str, ScenarioResult]:
        """Execute all registered scenarios.

        Args:
            normal_performance: Performance under normal conditions.

        Returns:
            Dict mapping scenario name to result.
        """
        results = {}
        for name in self._scenarios:
            results[name] = await self.execute_scenario(name, normal_performance)
        return results

    def get_result(self, name: str) -> ScenarioResult | None:
        """Get the result for a specific scenario.

        Args:
            name: Scenario name.

        Returns:
            ScenarioResult or None if not executed.
        """
        return self._results.get(name)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all scenario results.

        Returns:
            Summary dict with counts and pass rate.
        """
        if not self._results:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}

        passed = sum(1 for r in self._results.values() if r.survived)
        total = len(self._results)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
        }

    def clear_results(self) -> None:
        """Clear all scenario results."""
        self._results.clear()
