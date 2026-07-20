"""Tests for connector factory."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

import pytest

from libraries.domain.market import (
    MarketDataManager,
    NormalizationEngine,
    SessionManager,
    Symbol,
    ValidationEngine,
)
from libraries.infrastructure.broker_connectors.base import BaseConnector, ConnectorConfig
from libraries.infrastructure.broker_connectors.connectors import (
    BinanceConnector,
    MT5Connector,
    OANDAConnector,
)
from libraries.infrastructure.broker_connectors.factory import ConnectorFactory, ConnectorSpec
from libraries.infrastructure.broker_connectors.metrics import RecordingMetricsCollector
from libraries.infrastructure.broker_connectors.transports import (
    AbstractTransport,
    TransportMessage,
)


@dataclass
class FakeTransport(AbstractTransport):
    provider: str
    messages_list: list[TransportMessage] | None = None
    connected: bool = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def messages(self) -> AsyncIterator[TransportMessage]:
        if self.messages_list:
            for msg in self.messages_list:
                yield msg
        return


class TestConnectorFactory:
    def test_create_mt5_connector(self) -> None:
        async def exercise() -> None:
            transport = FakeTransport(provider="mt5")
            spec = ConnectorSpec(provider="mt5", transport=transport, name="mt5-1")
            factory = ConnectorFactory(
                manager=_create_manager(),
                metrics=RecordingMetricsCollector(),
            )
            connector = factory.create(spec)
            assert isinstance(connector, MT5Connector)
            assert connector.name == "mt5-1"

        asyncio.run(exercise())

    def test_create_oanda_connector(self) -> None:
        async def exercise() -> None:
            transport = FakeTransport(provider="oanda")
            spec = ConnectorSpec(provider="oanda", transport=transport, name="oanda-1")
            factory = ConnectorFactory(
                manager=_create_manager(),
                metrics=RecordingMetricsCollector(),
            )
            connector = factory.create(spec)
            assert isinstance(connector, OANDAConnector)
            assert connector.name == "oanda-1"

        asyncio.run(exercise())

    def test_create_binance_connector(self) -> None:
        async def exercise() -> None:
            transport = FakeTransport(provider="binance")
            spec = ConnectorSpec(provider="binance", transport=transport, name="binance-1")
            factory = ConnectorFactory(
                manager=_create_manager(),
                metrics=RecordingMetricsCollector(),
            )
            connector = factory.create(spec)
            assert isinstance(connector, BinanceConnector)
            assert connector.name == "binance-1"

        asyncio.run(exercise())

    def test_create_unsupported_provider_raises(self) -> None:
        factory = ConnectorFactory(manager=_create_manager())
        transport = FakeTransport(provider="unknown")
        spec = ConnectorSpec(provider="unknown", transport=transport, name="unknown")
        with pytest.raises(ValueError, match="Unsupported provider"):
            factory.create(spec)

    def test_create_factory_with_logger(self) -> None:
        async def exercise() -> None:
            transport = FakeTransport(provider="mt5")
            spec = ConnectorSpec(provider="mt5", transport=transport, name="mt5-1")
            factory = ConnectorFactory(
                manager=_create_manager(),
                metrics=RecordingMetricsCollector(),
            )
            connector = factory.create(spec)
            assert connector is not None

        asyncio.run(exercise())


def _create_manager() -> MarketDataManager:
    return MarketDataManager(
        symbol_registry=_create_simple_registry(),
        session_manager=SessionManager(),
        validation_engine=ValidationEngine(),
        normalization_engine=NormalizationEngine(),
    )


def _create_simple_registry() -> object:
    """Minimal registry that always returns a symbol."""

    class SimpleRegistry:
        async def get(self, symbol_or_alias: str) -> Symbol:
            return Symbol(
                code=symbol_or_alias.upper().replace("-", "/"),
                base_currency=symbol_or_alias[:3].upper(),
                quote_currency=symbol_or_alias[3:].upper(),
                tick_size=0.0001,
                pip_size=0.0001,
            )

    return SimpleRegistry()
