"""Connector factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from libraries.domain.market import MarketDataManager
from libraries.infrastructure.broker_connectors.connectors import (
    BinanceConnector,
    MT5Connector,
    OANDAConnector,
)
from libraries.infrastructure.broker_connectors.metrics import MetricsCollector
from libraries.infrastructure.broker_connectors.retry import RetryPolicy
from libraries.infrastructure.broker_connectors.transports import AbstractTransport


@dataclass(frozen=True, slots=True)
class ConnectorSpec:
    provider: str
    transport: AbstractTransport
    name: str


class ConnectorFactory:
    """Create broker connectors from a provider spec."""

    def __init__(
        self, *, manager: MarketDataManager, metrics: MetricsCollector | None = None
    ) -> None:
        self._manager = manager
        self._metrics = metrics

    def create(self, spec: ConnectorSpec) -> object:
        provider = spec.provider.lower()
        if provider == "mt5":
            return MT5Connector(
                transport=spec.transport,
                manager=self._manager,
                metrics=self._metrics,
                name=spec.name,
            )
        if provider == "oanda":
            return OANDAConnector(
                transport=spec.transport,
                manager=self._manager,
                metrics=self._metrics,
                name=spec.name,
            )
        if provider == "binance":
            return BinanceConnector(
                transport=spec.transport,
                manager=self._manager,
                metrics=self._metrics,
                name=spec.name,
            )
        raise ValueError(f"Unsupported provider: {spec.provider}")
