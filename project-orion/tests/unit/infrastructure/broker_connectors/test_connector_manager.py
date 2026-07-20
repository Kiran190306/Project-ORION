"""Tests for connector lifecycle management."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from libraries.infrastructure.broker_connectors.base import BaseConnector, ConnectorConfig
from libraries.infrastructure.broker_connectors.connector_manager import ConnectorManager


class FakeConnector(BaseConnector):
    """Minimal connector for testing lifecycle."""

    def __init__(self, *, config: ConnectorConfig) -> None:
        super().__init__(config=config)
        self.connect_called = False
        self.disconnect_called = False
        self._tick_count = 0

    async def _transport_messages(self) -> AsyncIterator[object]:
        # Block until stop event is set to avoid tight reconnect loop
        while not self._stop_event.is_set():
            await asyncio.sleep(0.01)

    def _parse_tick(self, transport_message: object) -> object:
        return transport_message

    async def _on_tick(self, raw_tick: object) -> None:
        self._tick_count += 1

    async def _on_connect(self) -> None:
        self.connect_called = True

    async def _on_disconnect(self) -> None:
        self.disconnect_called = True


class TestConnectorManager:
    def test_start_all_starts_connectors(self) -> None:
        async def exercise() -> None:
            c1 = FakeConnector(config=ConnectorConfig(name="mt5-1"))
            c2 = FakeConnector(config=ConnectorConfig(name="oanda-1"))
            manager = ConnectorManager([c1, c2])
            result = await manager.start_all()
            assert len(result.started) == 2
            assert "mt5-1" in result.started
            assert "oanda-1" in result.started
            assert c1.running
            assert c2.running
            await manager.stop_all()

        asyncio.run(exercise())

    def test_stop_all_stops_connectors(self) -> None:
        async def exercise() -> None:
            c1 = FakeConnector(config=ConnectorConfig(name="mt5-1"))
            c2 = FakeConnector(config=ConnectorConfig(name="oanda-1"))
            manager = ConnectorManager([c1, c2])
            await manager.start_all()
            result = await manager.stop_all()
            assert len(result.stopped) == 2
            assert "mt5-1" in result.stopped
            assert "oanda-1" in result.stopped
            assert not c1.running
            assert not c2.running

        asyncio.run(exercise())

    def test_health_all_returns_health_dicts(self) -> None:
        async def exercise() -> None:
            c1 = FakeConnector(config=ConnectorConfig(name="mt5-1"))
            c2 = FakeConnector(config=ConnectorConfig(name="oanda-1"))
            manager = ConnectorManager([c1, c2])
            await manager.start_all()
            health_map = await manager.health_all()
            assert "mt5-1" in health_map
            assert "oanda-1" in health_map
            assert health_map["mt5-1"]["running"] is True
            assert health_map["oanda-1"]["running"] is True
            await manager.stop_all()

        asyncio.run(exercise())

    def test_empty_connectors(self) -> None:
        async def exercise() -> None:
            manager = ConnectorManager([])
            result = await manager.start_all()
            assert result.started == ()
            result2 = await manager.stop_all()
            assert result2.stopped == ()
            health = await manager.health_all()
            assert health == {}

        asyncio.run(exercise())

    def test_connector_manager_double_start(self) -> None:
        async def exercise() -> None:
            c1 = FakeConnector(config=ConnectorConfig(name="mt5-1"))
            manager = ConnectorManager([c1])
            await manager.start_all()
            await manager.start_all()  # Should be idempotent
            await manager.stop_all()

        asyncio.run(exercise())
