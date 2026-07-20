from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from libraries.domain.market import (
    MarketDataManager,
    MarketDataSnapshot,
    NormalizationEngine,
    SessionManager,
    Symbol,
    SymbolRegistry,
    ValidationEngine,
)
from libraries.infrastructure.broker_connectors.connectors import MT5Connector
from libraries.infrastructure.broker_connectors.factory import ConnectorFactory, ConnectorSpec
from libraries.infrastructure.broker_connectors.metrics import RecordingMetricsCollector
from libraries.infrastructure.broker_connectors.transports import (
    AbstractTransport,
    TransportMessage,
)


class RecordingPublisher:
    def __init__(self) -> None:
        self.snapshots: list[MarketDataSnapshot] = []

    async def publish(self, snapshot: MarketDataSnapshot) -> None:
        self.snapshots.append(snapshot)


@dataclass
class FakeTransport(AbstractTransport):
    provider: str
    messages_list: list[TransportMessage]
    connected: bool = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def messages(self):
        for msg in self.messages_list:
            yield msg


def eur_usd_symbol() -> Symbol:
    return Symbol(
        code="EUR/USD",
        base_currency="EUR",
        quote_currency="USD",
        tick_size=Decimal("0.0001"),
        pip_size=Decimal("0.0001"),
    )


def test_mt5_connector_feeds_market_data_manager() -> None:
    async def exercise() -> None:
        symbol_registry = SymbolRegistry(NormalizationEngine())
        await symbol_registry.register(eur_usd_symbol(), aliases=("EURUSD",))
        session_manager = SessionManager()

        manager = MarketDataManager(
            symbol_registry=symbol_registry,
            session_manager=session_manager,
            validation_engine=ValidationEngine(),
            normalization_engine=NormalizationEngine(),
        )

        await manager.start()
        publisher = RecordingPublisher()
        await manager.subscribe("p", publisher)

        ts = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
        transport_messages = [
            TransportMessage(
                provider="mt5",
                payload={
                    "symbol": "EURUSD",
                    "timestamp": ts.isoformat(),
                    "bid": "1.10004",
                    "ask": "1.10016",
                    "sequence": 7,
                },
            )
        ]

        metrics = RecordingMetricsCollector()
        transport = FakeTransport(provider="mt5", messages_list=transport_messages)

        factory = ConnectorFactory(manager=manager, metrics=metrics)
        connector = factory.create(ConnectorSpec(provider="mt5", transport=transport, name="mt5-1"))
        assert hasattr(connector, "start")

        await connector.start()  # type: ignore[union-attr]
        await asyncio.sleep(0.01)
        await connector.stop()  # type: ignore[union-attr]

        assert len(publisher.snapshots) == 1
        snapshot = publisher.snapshots[0]
        assert snapshot.tick.symbol == "EUR/USD"

        await manager.stop()

    asyncio.run(exercise())
