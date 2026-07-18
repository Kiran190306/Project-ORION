"""Async orchestration service for normalized, validated market data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from shared.interfaces import Logger

from .exceptions import EngineNotRunningError, InvalidMarketDataError
from .interfaces import (
    MarketDataPublisher,
    SessionManagerPort,
    SymbolRegistryPort,
    ValidationEnginePort,
)
from .models import MarketDataSnapshot, RawTick, Tick
from .normalization import NormalizationEngine


class MarketDataManager:
    """Coordinate validation, normalization, session state, and publication.

    Dependencies are supplied through the constructor, allowing application
    composition roots to choose registries, policies, loggers, and publishers
    without coupling the domain engine to a concrete runtime framework.
    """

    def __init__(
        self,
        symbol_registry: SymbolRegistryPort,
        session_manager: SessionManagerPort,
        validation_engine: ValidationEnginePort,
        normalization_engine: NormalizationEngine,
        logger: Logger | None = None,
    ) -> None:
        self._symbol_registry = symbol_registry
        self._session_manager = session_manager
        self._validation_engine = validation_engine
        self._normalization_engine = normalization_engine
        self._logger = logger
        self._running = False
        self._accepted_sequence = 0
        self._latest_by_symbol: dict[str, Tick] = {}
        self._publishers: dict[str, MarketDataPublisher] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start accepting market-data records."""
        async with self._lock:
            self._running = True
        self._log("info", "Market Data Manager started")

    async def stop(self) -> None:
        """Stop accepting records while retaining the latest accepted state."""
        async with self._lock:
            self._running = False
        self._log("info", "Market Data Manager stopped")

    async def subscribe(self, subscriber_id: str, publisher: MarketDataPublisher) -> None:
        """Register a named downstream publisher.

        Args:
            subscriber_id: Stable subscription identifier.
            publisher: Asynchronous recipient of accepted snapshots.
        """
        if not subscriber_id.strip():
            raise ValueError("subscriber_id is required")
        async with self._lock:
            self._publishers[subscriber_id] = publisher

    async def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove a publisher and return whether it was registered."""
        async with self._lock:
            return self._publishers.pop(subscriber_id, None) is not None

    async def process_tick(self, raw_tick: RawTick) -> MarketDataSnapshot:
        """Validate, normalize, store, and publish one provider tick.

        A failing publisher is isolated and logged; it does not compromise the
        canonical state or delivery to the other registered publishers.
        """
        async with self._lock:
            if not self._running:
                raise EngineNotRunningError()
        raw_report = self._validation_engine.validate_raw_tick(raw_tick)
        if not raw_report.is_valid:
            raise InvalidMarketDataError(self._format_issues(raw_report.issues))

        symbol = await self._symbol_registry.get(raw_tick.symbol)
        tick = self._normalization_engine.normalize_tick(raw_tick, symbol)
        normalized_report = self._validation_engine.validate_tick(tick)
        if not normalized_report.is_valid:
            raise InvalidMarketDataError(self._format_issues(normalized_report.issues))

        sessions = await self._session_manager.active_sessions(tick.timestamp)
        async with self._lock:
            self._accepted_sequence += 1
            snapshot = MarketDataSnapshot(
                tick=tick,
                active_sessions=tuple(session.session_id for session in sessions),
                received_at=datetime.now(timezone.utc),
                accepted_sequence=self._accepted_sequence,
            )
            self._latest_by_symbol[tick.symbol] = tick
            publishers = tuple(self._publishers.items())

        await self._publish(snapshot, publishers)

        self._log(
            "debug",
            "Accepted market tick",
            symbol=tick.symbol,
            source=tick.source,
            accepted_sequence=snapshot.accepted_sequence,
        )
        return snapshot

    async def latest_tick(self, symbol: str) -> Tick | None:
        """Return the most recently accepted canonical tick for a symbol."""
        registered = await self._symbol_registry.get(symbol)
        async with self._lock:
            return self._latest_by_symbol.get(registered.code)

    async def health(self) -> dict[str, int | bool]:
        """Return a minimal operational health snapshot for service probes."""
        async with self._lock:
            return {
                "running": self._running,
                "accepted_ticks": self._accepted_sequence,
                "symbols_with_latest_tick": len(self._latest_by_symbol),
                "subscribers": len(self._publishers),
            }

    async def _publish(
        self,
        snapshot: MarketDataSnapshot,
        publishers: tuple[tuple[str, MarketDataPublisher], ...],
    ) -> None:
        """Deliver a snapshot to every publisher while isolating failures."""
        for subscriber_id, publisher in publishers:
            try:
                await publisher.publish(snapshot)
            except Exception as error:
                self._log(
                    "error",
                    "Market-data publisher failed",
                    subscriber_id=subscriber_id,
                    error=error,
                )

    def _log(self, level: str, message: str, **context: object) -> None:
        """Log through an optional application-provided logger."""
        if self._logger is not None:
            getattr(self._logger, level)(message, **context)

    @staticmethod
    def _format_issues(issues: tuple[object, ...]) -> str:
        """Create a useful validation exception message."""
        formatted: list[str] = []
        for issue in issues:
            # ValidationIssue is expected, but keep this method defensive
            # against incorrect runtime values while satisfying mypy.
            if hasattr(issue, "field") and hasattr(issue, "message"):
                formatted.append(f"{getattr(issue, 'field')}: {getattr(issue, 'message')}")
            else:
                formatted.append(str(issue))
        return "; ".join(formatted)
