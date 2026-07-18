"""Ports defining the Market Data Engine's dependency boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from .models import MarketDataSnapshot, RawTick, Symbol, Tick, TradingSession, ValidationReport


@runtime_checkable
class MarketDataPublisher(Protocol):
    """Receives accepted and normalized market-data snapshots."""

    async def publish(self, snapshot: MarketDataSnapshot) -> None:
        """Publish an accepted market-data snapshot."""
        ...


@runtime_checkable
class SymbolRegistryPort(Protocol):
    """Resolves provider symbols to registered instruments."""

    async def get(self, symbol_or_alias: str) -> Symbol:
        """Return the symbol identified by a canonical code or alias."""
        ...


@runtime_checkable
class SessionManagerPort(Protocol):
    """Determines active sessions for a UTC instant."""

    async def active_sessions(self, instant: datetime) -> tuple[TradingSession, ...]:
        """Return sessions trading at the supplied instant."""

        ...


@runtime_checkable
class ValidationEnginePort(Protocol):
    """Validates raw and canonical market-data records."""

    def validate_raw_tick(self, tick: RawTick) -> ValidationReport:
        """Validate a provider-originated tick."""
        ...

    def validate_tick(self, tick: Tick) -> ValidationReport:
        """Validate a canonical tick."""
        ...
