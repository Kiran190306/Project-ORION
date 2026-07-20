"""Tests for transport implementations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from libraries.infrastructure.broker_connectors.retry import RetryPolicy
from libraries.infrastructure.broker_connectors.transports import (
    RESTPollingTransport,
    TransportConnectionError,
    TransportMessage,
    WebSocketTransport,
)


@dataclass
class FakeWebSocket:
    messages: list[object]
    connect_called: bool = False
    close_called: bool = False

    async def connect(self) -> None:
        self.connect_called = True

    def recv(self) -> object:
        if self.messages:
            return self.messages.pop(0)
        raise StopAsyncIteration

    async def close(self) -> None:
        self.close_called = True


@dataclass
class FakeSyncWebSocket:
    messages: list[object]
    connect_called: bool = False
    close_called: bool = False

    def connect(self) -> None:
        self.connect_called = True

    def recv(self) -> object:
        if self.messages:
            return self.messages.pop(0)
        raise StopAsyncIteration

    def close(self) -> None:
        self.close_called = True


@dataclass
class FakeWebSocketNoClose:
    messages: list[object]
    connect_called: bool = False

    async def connect(self) -> None:
        self.connect_called = True

    def recv(self) -> object:
        if self.messages:
            return self.messages.pop(0)
        raise StopAsyncIteration


class TestWebSocketTransport:
    def test_connect(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeWebSocket(messages=[])
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            await transport.connect()
            assert ws.connect_called

        asyncio.run(exercise())

    def test_disconnect_with_close(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeWebSocket(messages=[])
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            await transport.connect()
            await transport.disconnect()
            assert ws.close_called

        asyncio.run(exercise())

    def test_disconnect_without_close_attr(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeWebSocketNoClose(messages=[])
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            await transport.connect()
            # Should not raise
            await transport.disconnect()

        asyncio.run(exercise())

    def test_messages_yields_transport_message(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeWebSocket(messages=[{"price": 1.1}, {"price": 1.2}])
            transport = WebSocketTransport(
                provider="oanda",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            await transport.connect()
            messages: list[TransportMessage] = []
            async for msg in transport.messages():
                messages.append(msg)
                if len(messages) >= 2:
                    break
            assert len(messages) == 2
            assert all(m.provider == "oanda" for m in messages)
            assert messages[0].payload == {"price": 1.1}
            assert messages[1].payload == {"price": 1.2}

        asyncio.run(exercise())

    def test_messages_raises_when_not_connected(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeWebSocket(messages=[])
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            with pytest.raises(TransportConnectionError, match="not connected"):
                async for _ in transport.messages():
                    pass

        asyncio.run(exercise())

    def test_connect_retry_on_failure(self) -> None:
        connect_attempts = 0

        class FlakyWebSocket:
            async def connect(self) -> None:
                nonlocal connect_attempts
                connect_attempts += 1
                if connect_attempts < 2:
                    raise ConnectionError("fail")
                self._connected = True

            async def close(self) -> None:
                self._connected = False

        retry = RetryPolicy(max_attempts=3, initial_delay_seconds=0.001)

        async def exercise() -> None:
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: FlakyWebSocket(),
                retry_policy=retry,
            )
            await transport.connect()
            assert connect_attempts == 2

        asyncio.run(exercise())

    def test_messages_raises_when_no_websocket(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: None,
                retry_policy=retry,
            )
            # connect would fail, so manually set connected
            transport._connected = True
            with pytest.raises(TransportConnectionError, match="no websocket"):
                async for _ in transport.messages():
                    pass

        asyncio.run(exercise())

    def test_sync_websocket_connect(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            ws = FakeSyncWebSocket(messages=[])
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: ws,
                retry_policy=retry,
            )
            await transport.connect()
            assert ws.connect_called

        asyncio.run(exercise())

    def test_disconnect_noop_when_no_ws(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            transport = WebSocketTransport(
                provider="mt5",
                websocket_factory=lambda: None,
                retry_policy=retry,
            )
            # Should not raise
            await transport.disconnect()

        asyncio.run(exercise())


class TestRESTPollingTransport:
    def test_connect_and_disconnect(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            transport = RESTPollingTransport(
                provider="oanda",
                poll_fn=lambda: asyncio.sleep(0) or [],
                interval_seconds=0.01,
                retry_policy=retry,
            )
            await transport.connect()
            assert transport._connected
            await transport.disconnect()
            assert not transport._connected

        asyncio.run(exercise())

    def test_messages_yields_polled_data(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            poll_count = 0

            async def poll() -> list[object]:
                nonlocal poll_count
                poll_count += 1
                return [{"bid": 1.1}]

            transport = RESTPollingTransport(
                provider="oanda",
                poll_fn=poll,
                interval_seconds=0.005,
                retry_policy=retry,
            )
            await transport.connect()
            messages: list[TransportMessage] = []
            async for msg in transport.messages():
                messages.append(msg)
                if len(messages) >= 2:
                    await transport.disconnect()
                    break
            assert len(messages) == 2
            assert all(m.provider == "oanda" for m in messages)

        asyncio.run(exercise())

    def test_messages_raises_when_not_connected(self) -> None:
        retry = RetryPolicy(max_attempts=1, initial_delay_seconds=0.001)

        async def exercise() -> None:
            transport = RESTPollingTransport(
                provider="oanda",
                poll_fn=lambda: asyncio.sleep(0) or [],
                interval_seconds=0.01,
                retry_policy=retry,
            )
            with pytest.raises(TransportConnectionError, match="not connected"):
                async for _ in transport.messages():
                    pass

        asyncio.run(exercise())

    def test_poll_retry_on_failure(self) -> None:
        retry = RetryPolicy(max_attempts=2, initial_delay_seconds=0.001)
        poll_attempts = 0

        async def flaky_poll() -> list[object]:
            nonlocal poll_attempts
            poll_attempts += 1
            if poll_attempts < 2:
                raise ConnectionError("fail")
            return [{"bid": 1.1}]

        async def exercise() -> None:
            transport = RESTPollingTransport(
                provider="mt5",
                poll_fn=flaky_poll,
                interval_seconds=0.005,
                retry_policy=retry,
            )
            await transport.connect()
            messages: list[TransportMessage] = []
            async for msg in transport.messages():
                messages.append(msg)
                if len(messages) >= 1:
                    await transport.disconnect()
                    break
            assert len(messages) == 1
            assert poll_attempts >= 1

        asyncio.run(exercise())
