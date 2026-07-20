"""Base connector abstraction and lifecycle management."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Protocol, TypeVar

from libraries.infrastructure.broker_connectors.health import ConnectorHealth
from libraries.infrastructure.broker_connectors.metrics import (
    MetricsCollector,
    NullMetricsCollector,
)


class ConnectorError(Exception):
    """Connector-level error."""


class LoggerLike(Protocol):
    def debug(self, msg: str, **kwargs: object) -> None: ...

    def info(self, msg: str, **kwargs: object) -> None: ...

    def warning(self, msg: str, **kwargs: object) -> None: ...

    def error(self, msg: str, **kwargs: object) -> None: ...


@dataclass(frozen=True, slots=True)
class ConnectorConfig:
    name: str
    auto_reconnect: bool = True


class BaseConnector(ABC):
    """Base broker connector abstraction."""

    def __init__(
        self,
        *,
        config: ConnectorConfig,
        metrics: MetricsCollector | None = None,
        logger: LoggerLike | None = None,
    ) -> None:
        self._config = config
        self._metrics = metrics or NullMetricsCollector()
        self._logger = logger
        self._running = False
        self._transport_connected = False
        self._last_error: str | None = None
        self._last_tick_timestamp: str | None = None
        self._reconnect_attempts = 0
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name=f"connector:{self._config.name}")
        if self._logger is not None:
            self._logger.info("Connector started", connector=self._config.name)

    async def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        await self._on_stop()
        if self._logger is not None:
            self._logger.info("Connector stopped", connector=self._config.name)

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(
            connector_name=self._config.name,
            running=self._running,
            transport_connected=self._transport_connected,
            last_error=self._last_error,
            last_tick_timestamp=self._last_tick_timestamp,
            reconnect_attempts=self._reconnect_attempts,
        )

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_process()
                # If processing returns normally, stop loop unless reconnect enabled.
                if not self._config.auto_reconnect:
                    break
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                self._reconnect_attempts += 1
                self._metrics.increment(
                    "connector.reconnect_attempts", tags={"connector": self._config.name}
                )
                if self._logger is not None:
                    self._logger.error(
                        "Connector run loop error", connector=self._config.name, error=exc
                    )

                if not self._config.auto_reconnect or self._stop_event.is_set():
                    break

                await self._on_reconnect_wait()

    async def _on_reconnect_wait(self) -> None:
        await asyncio.sleep(0.5)

    async def _connect_and_process(self) -> None:
        await self._on_connect()
        self._transport_connected = True
        async for tick in self._tick_stream():
            await self._on_tick(tick)
            self._last_tick_timestamp = tick.timestamp.isoformat()
        await self._on_disconnect()
        self._transport_connected = False

    async def _tick_stream(self) -> AsyncIterator[object]:
        async for msg in self._transport_messages():
            tick = self._parse_tick(msg)
            yield tick

    @abstractmethod
    async def _transport_messages(self) -> AsyncIterator[object]: ...

    @abstractmethod
    def _parse_tick(self, transport_message: object) -> object:
        """Parse transport message into domain RawTick."""

    @abstractmethod
    async def _on_tick(self, raw_tick: object) -> None:
        """Deliver raw tick to MarketDataManager."""

    @abstractmethod
    async def _on_connect(self) -> None: ...

    @abstractmethod
    async def _on_disconnect(self) -> None: ...

    async def _on_stop(self) -> None:
        await self._on_disconnect()
