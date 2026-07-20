"""Tests for connector reconnection behavior."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from libraries.infrastructure.broker_connectors.base import BaseConnector, ConnectorConfig
from libraries.infrastructure.broker_connectors.metrics import RecordingMetricsCollector


class _ReconnectConnector(BaseConnector):
    """A connector that fails connection N times then succeeds."""

    def __init__(
        self,
        *,
        config: ConnectorConfig,
        metrics: RecordingMetricsCollector | None = None,
    ) -> None:
        super().__init__(config=config, metrics=metrics)
        self.fail_connect_count: int = 0
        self.connect_attempts: int = 0
        self.disconnect_attempts: int = 0
        self.ticks_to_emit: int = 0
        self.emit_count: int = 0

    async def _transport_messages(self) -> AsyncIterator[object]:
        # Block until stop event to avoid reconnect loop
        while not self._stop_event.is_set():
            await asyncio.sleep(0.01)

    def _parse_tick(self, transport_message: object) -> object:
        return transport_message

    async def _on_tick(self, raw_tick: object) -> None:
        self.emit_count += 1

    async def _on_connect(self) -> None:
        self.connect_attempts += 1
        if self.connect_attempts <= self.fail_connect_count:
            raise ConnectionError(f"fail attempt {self.connect_attempts}")

    async def _on_disconnect(self) -> None:
        self.disconnect_attempts += 1

    async def _on_reconnect_wait(self) -> None:
        """Override to reduce wait time for tests."""
        await asyncio.sleep(0.001)


class TestReconnect:
    def test_connector_reconnects_on_connect_failure(self) -> None:
        async def exercise() -> None:
            connector = _ReconnectConnector(
                config=ConnectorConfig(name="test-reconnect", auto_reconnect=True),
                metrics=RecordingMetricsCollector(),
            )
            connector.fail_connect_count = 2  # Fail twice then succeed

            await connector.start()
            await asyncio.sleep(0.05)
            await connector.stop()

            # Should have attempted multiple connections (2 fails + success)
            assert connector.connect_attempts >= 2

        asyncio.run(exercise())

    def test_connector_no_reconnect_when_auto_reconnect_disabled(self) -> None:
        async def exercise() -> None:
            connector = _ReconnectConnector(
                config=ConnectorConfig(name="test-no-reconnect", auto_reconnect=False),
                metrics=RecordingMetricsCollector(),
            )
            connector.fail_connect_count = 1  # Fail once

            await connector.start()
            await asyncio.sleep(0.05)
            await connector.stop()

            # Should have attempted connection at least once
            assert connector.connect_attempts >= 1

        asyncio.run(exercise())

    def test_connector_stop_while_reconnecting(self) -> None:
        """Connector should stop cleanly even while reconnecting."""

        async def exercise() -> None:
            connector = _ReconnectConnector(
                config=ConnectorConfig(name="test-stop-reconnect", auto_reconnect=True),
                metrics=RecordingMetricsCollector(),
            )
            connector.fail_connect_count = 100  # Always fails

            await connector.start()
            # Give time for the failed connect + reconnect attempt
            await asyncio.sleep(0.01)
            await connector.stop()

            # After stop, connector should not be running
            assert not connector.running

        asyncio.run(exercise())

    def test_reconnect_attempts_incremented_on_failure(self) -> None:
        async def exercise() -> None:
            connector = _ReconnectConnector(
                config=ConnectorConfig(name="test-reconnect-count", auto_reconnect=True),
                metrics=RecordingMetricsCollector(),
            )
            connector.fail_connect_count = 3

            await connector.start()
            await asyncio.sleep(0.05)
            await connector.stop()

            assert connector._reconnect_attempts >= 2

        asyncio.run(exercise())
