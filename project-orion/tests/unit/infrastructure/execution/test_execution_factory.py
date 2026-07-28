"""Tests for the execution adapter factory."""

from __future__ import annotations

import pytest

from libraries.infrastructure.execution.binance_execution import BinanceExecutionAdapter
from libraries.infrastructure.execution.execution_factory import (
    ExecutionAdapterFactory,
    ExecutionAdapterSpec,
)
from libraries.infrastructure.execution.mt5_execution import MT5ExecutionAdapter
from libraries.infrastructure.execution.oanda_execution import OANDAExecutionAdapter
from libraries.infrastructure.execution.paper_execution import PaperExecutionAdapter


class TestExecutionAdapterFactory:
    """Test suite for ExecutionAdapterFactory."""

    def test_create_paper_adapter(self):
        spec = ExecutionAdapterSpec(provider="paper", name="paper1")
        adapter = ExecutionAdapterFactory.create_adapter(spec)
        assert isinstance(adapter, PaperExecutionAdapter)
        assert adapter.broker_name == "paper1"

    def test_create_mt5_adapter(self):
        spec = ExecutionAdapterSpec(provider="mt5", name="mt5_live")
        adapter = ExecutionAdapterFactory.create_adapter(spec)
        assert isinstance(adapter, MT5ExecutionAdapter)
        assert adapter.broker_name == "mt5_live"

    def test_create_oanda_adapter(self):
        spec = ExecutionAdapterSpec(
            provider="oanda",
            name="oanda_demo",
            api_endpoint="https://api-fxpractice.oanda.com",
        )
        adapter = ExecutionAdapterFactory.create_adapter(spec)
        assert isinstance(adapter, OANDAExecutionAdapter)
        assert adapter.broker_name == "oanda_demo"

    def test_create_binance_adapter(self):
        spec = ExecutionAdapterSpec(provider="binance", name="binance_spot")
        adapter = ExecutionAdapterFactory.create_adapter(spec)
        assert isinstance(adapter, BinanceExecutionAdapter)
        assert adapter.broker_name == "binance_spot"

    def test_create_unsupported_provider(self):
        spec = ExecutionAdapterSpec(provider="unsupported")
        with pytest.raises(ValueError) as exc:
            ExecutionAdapterFactory.create_adapter(spec)
        assert "Unsupported broker provider" in str(exc.value)

    def test_create_routing_target(self):
        spec = ExecutionAdapterSpec(
            provider="paper",
            name="paper1",
            priority=50,
        )
        target = ExecutionAdapterFactory.create_routing_target(spec)
        assert target.broker_name == "paper1"
        assert target.priority == 50

    def test_create_adapter_with_target(self):
        spec = ExecutionAdapterSpec(provider="paper", name="paper1")
        adapter, target = ExecutionAdapterFactory.create_adapter_with_target(spec)
        assert isinstance(adapter, PaperExecutionAdapter)
        assert target.broker_name == "paper1"

    def test_is_provider_supported(self):
        assert ExecutionAdapterFactory.is_provider_supported("paper")
        assert ExecutionAdapterFactory.is_provider_supported("mt5")
        assert ExecutionAdapterFactory.is_provider_supported("oanda")
        assert ExecutionAdapterFactory.is_provider_supported("binance")
        assert not ExecutionAdapterFactory.is_provider_supported("unknown")

    def test_is_provider_supported_case_insensitive(self):
        assert ExecutionAdapterFactory.is_provider_supported("PAPER")
        assert ExecutionAdapterFactory.is_provider_supported("MT5")
