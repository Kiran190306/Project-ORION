"""Tests for the Stress Analysis protocol (EPIC-014 Sprint-4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from libraries.domain.risk.analytics.interfaces import StressTestPort
from libraries.domain.risk.analytics.models import (
    Scenario,
    StressTestResult,
    StressTestSummary,
)
from libraries.domain.risk.analytics.stress import StressTestEngine


class TestStressTestPortStructural:
    """Verify StressTestEngine satisfies the StressTestPort protocol."""

    def test_engine_is_instance_of_protocol(self) -> None:
        engine: StressTestPort = StressTestEngine()
        assert isinstance(engine, StressTestPort)

    def test_engine_implements_all_methods(self) -> None:
        engine = StressTestEngine()
        assert hasattr(engine, "apply_scenario")
        assert hasattr(engine, "run_historical_stress")
        assert hasattr(engine, "apply_portfolio_shock")
        assert hasattr(engine, "simulate_market_crash")
        assert hasattr(engine, "apply_volatility_shock")

    @pytest.mark.asyncio
    async def test_apply_scenario_async(self) -> None:
        engine = StressTestEngine()
        result = await engine.apply_scenario(
            returns_by_symbol={"EURUSD": [0.01, -0.02, 0.03]},
            scenario=Scenario(name="crisis", shock_factors={"EURUSD": -0.15}),
            portfolio_value=Decimal("100000"),
        )
        assert isinstance(result, StressTestResult)

    @pytest.mark.asyncio
    async def test_run_historical_stress_async(self) -> None:
        engine = StressTestEngine()
        summary = await engine.run_historical_stress(
            returns_by_symbol={
                "gfc": {"EURUSD": [-0.1, -0.2, -0.05]},
            },
            portfolio_weights={"EURUSD": 1.0},
            portfolio_value=Decimal("100000"),
        )
        assert isinstance(summary, StressTestSummary)


class TestStressTestPortRuntimeCheckable:
    """Verify the protocol is runtime-checkable."""

    def test_runtime_checkable(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(Scenario)
        assert not dataclasses.is_dataclass(StressTestPort)
