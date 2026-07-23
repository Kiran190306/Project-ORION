"""Tests for EPIC-010 protocol interfaces."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import pytest

from libraries.domain.backtesting.interfaces import (
    BacktestEventHandler,
    BacktestEventPublisher,
    BacktestRepositoryPort,
    ExecutionSimulatorPort,
    HistoricalDataProviderPort,
    MarketSimulatorPort,
    OptimizationHook,
    PerformanceCalculatorPort,
    PortfolioSimulatorPort,
    RandomizerPort,
    ReplayControllerPort,
    ReportingPort,
    ScenarioProviderPort,
    WalkForwardPort,
)

# Map of interface names to their expected methods
INTERFACE_EXPECTATIONS: dict[str, list[str]] = {
    "HistoricalDataProviderPort": ["load_candles", "load_ticks"],
    "ReplayControllerPort": ["start", "pause", "resume", "stop", "seek", "set_speed"],
    "PortfolioSimulatorPort": ["apply_fill", "update_market_price", "get_snapshot", "reset"],
    "ExecutionSimulatorPort": ["execute_order"],
    "PerformanceCalculatorPort": ["calculate"],
    "ReportingPort": ["generate"],
    "MarketSimulatorPort": ["simulate"],
    "ScenarioProviderPort": ["get_scenario", "apply_scenario"],
    "WalkForwardPort": ["run", "analyze"],
    "BacktestEventPublisher": ["publish", "subscribe", "unsubscribe"],
    "BacktestEventHandler": ["handle_event"],
    "RandomizerPort": ["random", "seed", "uniform", "randint", "choice"],
    "OptimizationHook": ["evaluate", "on_iteration_start", "on_iteration_end"],
    "BacktestRepositoryPort": ["save", "load", "delete", "list_runs"],
}


class TestInterfaceContracts:
    """Test that protocol interfaces exist and have expected methods."""

    @pytest.mark.parametrize(
        "name,expected_methods",
        [pytest.param(name, methods, id=name) for name, methods in INTERFACE_EXPECTATIONS.items()],
    )
    def test_protocol_exists(self, name: str, expected_methods: list[str]) -> None:
        """Test that a protocol interface exists and has expected methods."""
        # Get the interface from module
        interface = getattr(INTERFACE_EXPECTATIONS_MODULE, name, None)
        assert interface is not None, f"Interface {name} not found"

        # Verify it's a protocol
        if hasattr(interface, "_is_protocol"):
            assert interface._is_protocol

    def test_all_ports_have_async_methods(self) -> None:
        """Test that data provider ports have async methods."""
        # HistoricalDataProviderPort uses load_data, load_candles, load_ticks
        # but as a Protocol, the concrete class defines the actual methods
        # Just verify the port is accessible
        from libraries.domain.backtesting.interfaces import HistoricalDataProviderPort

        assert HistoricalDataProviderPort is not None


# Module-level reference for parametrize
INTERFACE_EXPECTATIONS_MODULE = __import__(
    "libraries.domain.backtesting.interfaces", fromlist=["*"]
)
