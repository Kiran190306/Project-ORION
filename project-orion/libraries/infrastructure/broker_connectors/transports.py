"""Connector transports: WebSocket and REST polling.

These transports are infrastructure-only concerns. Domain remains broker-agnostic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, Awaitable, Callable, Protocol

from libraries.infrastructure.broker_connectors.retry import RetryPolicy, retry_async


class TransportConnectionError(Exception):
    """Raised when a transport cannot connect."""


@dataclass(frozen=True, slots=True)
class TransportMessage:
    """Raw transport message (provider-specific payload).

    The connector is responsible for parsing/normalizing into RawTick.
    """

    provider: str
    payload: object


class AbstractTransport(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def messages(self) -> AsyncIterator[TransportMessage]: ...


class WebSocketTransport:
    """Async WebSocket transport abstraction.

    This implementation is intentionally transport-agnostic: it requires
    a user-supplied websocket client factory (DI) to avoid hard dependencies.
    """

    def __init__(
        self,
        *,
        provider: str,
        websocket_factory: Callable[[], object],
        retry_policy: RetryPolicy,
        logger: object | None = None,
    ) -> None:
        self._provider = provider
        self._websocket_factory = websocket_factory
        self._retry_policy = retry_policy
        self._logger = logger
        self._ws: object | None = None
        self._connected = False
        self._stop_event = asyncio.Event()

    async def connect(self) -> None:
        async def _do_connect() -> None:
            self._ws = self._websocket_factory()
            # Minimal expected interface: .connect() and .recv()
            connect_coro = getattr(self._ws, "connect")
            if asyncio.iscoroutinefunction(connect_coro):
                await connect_coro()  # type: ignore[misc]
            else:
                result = connect_coro()
                if asyncio.isfuture(result) or asyncio.iscoroutine(result):
                    await result
            self._connected = True

        await retry_async(
            lambda: _do_connect(),
            self._retry_policy,
            retry_on=lambda exc: True,
        )

    async def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False
        if self._ws is None:
            return
        close = getattr(self._ws, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result

    async def messages(self) -> AsyncIterator[TransportMessage]:
        if not self._connected:
            raise TransportConnectionError("WebSocketTransport is not connected")
        if self._ws is None:
            raise TransportConnectionError("WebSocketTransport has no websocket")

        recv = getattr(self._ws, "recv")
        while not self._stop_event.is_set():
            result = recv()
            if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                payload = await result
            else:
                payload = result
            yield TransportMessage(provider=self._provider, payload=payload)


class RESTPollingTransport:
    """Async REST polling transport.

    Provider-specific HTTP calls are injected via a callable to keep this
    package dependency-free.
    """

    def __init__(
        self,
        *,
        provider: str,
        poll_fn: Callable[[], Awaitable[list[object]]],
        interval_seconds: float,
        retry_policy: RetryPolicy,
    ) -> None:
        self._provider = provider
        self._poll_fn = poll_fn
        self._interval_seconds = interval_seconds
        self._retry_policy = retry_policy
        self._stop_event = asyncio.Event()
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._stop_event.set()
        self._connected = False

    async def messages(self) -> AsyncIterator[TransportMessage]:
        if not self._connected:
            raise TransportConnectionError("RESTPollingTransport is not connected")

        while not self._stop_event.is_set():

            async def _poll() -> list[object]:
                return await self._poll_fn()

            messages = await retry_async(lambda: _poll(), self._retry_policy)
            for msg in messages:
                yield TransportMessage(provider=self._provider, payload=msg)

            await asyncio.sleep(self._interval_seconds)
