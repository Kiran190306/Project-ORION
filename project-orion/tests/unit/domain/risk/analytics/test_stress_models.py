"""Tests for the Stress Analysis models (EPIC-014 Sprint-4)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.risk.analytics.models import (
    Scenario,
    StressTestResult,
    StressTestSummary,
    StressTestType,
)


class TestStressTestType:
    """Test the StressTestType enum values."""

    def test_enum_values(self) -> None:
        assert StressTestType.SCENARIO == "scenario"
        assert StressTestType.HISTORICAL == "historical"
        assert StressTestType.PORTFOLIO_SHOCK == "portfolio_shock"
        assert StressTestType.MARKET_CRASH == "market_crash"
        assert StressTestType.VOLATILITY_SHOCK == "volatility_shock"


class TestScenario:
    """Test the Scenario model."""

    def test_construction(self) -> None:
        scenario = Scenario(
            name="crisis",
            shock_factors={"EURUSD": -0.15, "GBPUSD": -0.10},
            description="stress",
        )
        assert scenario.name == "crisis"
        assert scenario.shock_factors["EURUSD"] == -0.15
        assert scenario.description == "stress"
        assert scenario.volatility_multiplier == 1.0

    def test_symbols_property(self) -> None:
        scenario = Scenario(name="s", shock_factors={"EURUSD": -0.1, "USDJPY": -0.2})
        assert scenario.symbols == ("EURUSD", "USDJPY")

    def test_frozen_and_slots(self) -> None:
        scenario = Scenario(name="s", shock_factors={"EURUSD": -0.1})
        assert dataclasses.is_dataclass(scenario)
        assert hasattr(scenario, "__slots__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            scenario.name = "changed"


class TestStressTestResult:
    """Test the StressTestResult model."""

    def test_construction(self) -> None:
        result = StressTestResult(
            test_type=StressTestType.SCENARIO,
            name="crash",
            portfolio_value=Decimal("90000"),
            portfolio_return=-0.10,
            symbol_returns={"EURUSD": -0.10},
        )
        assert result.name == "crash"
        assert result.portfolio_value == Decimal("90000")
        assert result.portfolio_return == -0.10
        assert result.symbol_returns["EURUSD"] == -0.10

    def test_portfolio_loss_pct(self) -> None:
        result = StressTestResult(
            test_type=StressTestType.MARKET_CRASH,
            name="crash",
            portfolio_value=Decimal("70000"),
            portfolio_return=-0.30,
        )
        assert result.portfolio_loss_pct == 30.0

    def test_no_loss_pct(self) -> None:
        result = StressTestResult(
            test_type=StressTestType.SCENARIO,
            name="gain",
            portfolio_value=Decimal("110000"),
            portfolio_return=0.10,
        )
        assert result.portfolio_loss_pct == 0.0

    def test_frozen_and_slots(self) -> None:
        result = StressTestResult(
            test_type=StressTestType.SCENARIO,
            name="s",
            portfolio_value=Decimal("100000"),
            portfolio_return=0.0,
        )
        assert dataclasses.is_dataclass(result)
        assert hasattr(result, "__slots__")


class TestStressTestSummary:
    """Test the StressTestSummary model."""

    def test_construction(self) -> None:
        summary = StressTestSummary(
            test_type=StressTestType.HISTORICAL,
            name="historical",
            worst_case_return=-0.25,
            best_case_return=-0.05,
            average_return=-0.15,
            portfolio_shock_pct=25.0,
        )
        assert summary.worst_case_return == -0.25
        assert summary.best_case_return == -0.05
        assert summary.average_return == -0.15
        assert summary.portfolio_shock_pct == 25.0

    def test_frozen_and_slots(self) -> None:
        summary = StressTestSummary(
            test_type=StressTestType.HISTORICAL,
            name="historical",
            worst_case_return=-0.1,
            best_case_return=-0.05,
            average_return=-0.075,
            portfolio_shock_pct=10.0,
        )
        assert dataclasses.is_dataclass(summary)
        assert hasattr(summary, "__slots__")
        assert summary.timestamp.tzinfo is not None
        assert isinstance(summary.timestamp, datetime)


class TestTimestampAwareness:
    """Test that models use timezone-aware timestamps."""

    def test_timestamps_are_utc(self) -> None:
        result = StressTestResult(
            test_type=StressTestType.SCENARIO,
            name="s",
            portfolio_value=Decimal("1"),
            portfolio_return=0.0,
        )
        assert result.timestamp.tzinfo is not None
        assert result.timestamp.tzinfo == timezone.utc
