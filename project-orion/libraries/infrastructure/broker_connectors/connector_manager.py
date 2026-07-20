"""Connector lifecycle management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Sequence

from libraries.infrastructure.broker_connectors.base import BaseConnector


@dataclass(frozen=True, slots=True)
class ConnectorManagerResult:
    started: tuple[str, ...]
    stopped: tuple[str, ...]


class ConnectorManager:
    """Start/stop and coordinate a set of connectors."""

    def __init__(self, connectors: Sequence[BaseConnector]) -> None:
        self._connectors = list(connectors)

    async def start_all(self) -> ConnectorManagerResult:
        started: list[str] = []
        for connector in self._connectors:
            await connector.start()
            started.append(connector.name)
        return ConnectorManagerResult(started=tuple(started), stopped=tuple())

    async def stop_all(self) -> ConnectorManagerResult:
        stopped: list[str] = []
        for connector in self._connectors:
            await connector.stop()
            stopped.append(connector.name)
        return ConnectorManagerResult(started=tuple(), stopped=tuple(stopped))

    async def health_all(self) -> dict[str, dict[str, object]]:
        results: dict[str, dict[str, object]] = {}
        for connector in self._connectors:
            h = await connector.health()
            results[connector.name] = h.to_dict()
        return results
