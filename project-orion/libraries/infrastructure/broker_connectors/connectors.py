"""Broker connector implementations.

These connectors use injected transports and parsers to produce domain RawTick
and feed it into MarketDataManager.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Callable

from libraries.domain.market import MarketDataManager, RawTick
from libraries.infrastructure.broker_connectors.base import BaseConnector, ConnectorConfig
from libraries.infrastructure.broker_connectors.metrics import MetricsCollector
from libraries.infrastructure.broker_connectors.parsers import parse_provider_dict_tick
from libraries.infrastructure.broker_connectors.retry import RetryPolicy
from libraries.infrastructure.broker_connectors.transports import AbstractTransport


class _InjectedTickConnector(BaseConnector):
    """Concrete connector that relies on injected transport + provider parser."""

    def __init__(
        self,
        *,
        config: ConnectorConfig,
        provider: str,
        transport: AbstractTransport,
        manager: MarketDataManager,
        metrics: MetricsCollector | None = None,
        logger: object | None = None,
    ) -> None:
        super().__init__(config=config, metrics=metrics, logger=logger)
        self._provider = provider
        self._transport = transport
        self._manager = manager

    async def _transport_messages(self) -> AsyncIterator[object]:
        async for msg in self._transport.messages():
            yield msg

    def _parse_tick(self, transport_message: object) -> RawTick:
        # TransportMessage payload may already embed provider.
        provider = self._provider
        payload = transport_message
        if hasattr(transport_message, "payload"):
            provider = getattr(transport_message, "provider")
            payload = getattr(transport_message, "payload")
        return parse_provider_dict_tick(str(provider), payload)

    async def _on_tick(self, raw_tick: object) -> None:
        assert isinstance(raw_tick, RawTick)
        await self._manager.process_tick(raw_tick)

    async def _on_connect(self) -> None:
        await self._transport.connect()

    async def _on_disconnect(self) -> None:
        await self._transport.disconnect()


class MT5Connector(_InjectedTickConnector):
    def __init__(
        self,
        *,
        transport: AbstractTransport,
        manager: MarketDataManager,
        metrics: MetricsCollector | None = None,
        logger: object | None = None,
        name: str = "mt5",
    ) -> None:
        super().__init__(
            config=ConnectorConfig(name=name, auto_reconnect=True),
            provider="mt5",
            transport=transport,
            manager=manager,
            metrics=metrics,
            logger=logger,
        )


class OANDAConnector(_InjectedTickConnector):
    def __init__(
        self,
        *,
        transport: AbstractTransport,
        manager: MarketDataManager,
        metrics: MetricsCollector | None = None,
        logger: object | None = None,
        name: str = "oanda",
    ) -> None:
        super().__init__(
            config=ConnectorConfig(name=name, auto_reconnect=True),
            provider="oanda",
            transport=transport,
            manager=manager,
            metrics=metrics,
            logger=logger,
        )


class BinanceConnector(_InjectedTickConnector):
    def __init__(
        self,
        *,
        transport: AbstractTransport,
        manager: MarketDataManager,
        metrics: MetricsCollector | None = None,
        logger: object | None = None,
        name: str = "binance",
    ) -> None:
        super().__init__(
            config=ConnectorConfig(name=name, auto_reconnect=True),
            provider="binance",
            transport=transport,
            manager=manager,
            metrics=metrics,
            logger=logger,
        )
