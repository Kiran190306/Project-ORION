"""Unit tests for the EPIC-005 Sprint-1 Market Data Engine."""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timezone
from decimal import Decimal

import pytest

from libraries.domain.market import (
    DuplicateSymbolError,
    EngineNotRunningError,
    InvalidMarketDataError,
    MarketDataManager,
    MarketDataSnapshot,
    NormalizationEngine,
    RawTick,
    SessionManager,
    Symbol,
    SymbolRegistry,
    TradingSession,
    ValidationEngine,
)


class RecordingPublisher:
    """Collect published snapshots for manager tests."""

    def __init__(self) -> None:
        self.snapshots: list[MarketDataSnapshot] = []

    async def publish(self, snapshot: MarketDataSnapshot) -> None:
        """Record a manager publication."""
        self.snapshots.append(snapshot)


class FailingPublisher:
    """Exercise publication failure isolation."""

    async def publish(self, snapshot: MarketDataSnapshot) -> None:
        """Fail after receiving a snapshot."""
        del snapshot
        raise RuntimeError("unavailable")


def eur_usd() -> Symbol:
    """Return a standard EUR/USD instrument fixture."""
    return Symbol(
        code="EUR/USD",
        base_currency="EUR",
        quote_currency="USD",
        tick_size=Decimal("0.0001"),
        pip_size=Decimal("0.0001"),
    )


def raw_tick(symbol: str = "EURUSD") -> RawTick:
    """Return a valid provider tick fixture."""
    return RawTick(
        symbol=symbol,
        timestamp=datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc),
        bid=Decimal("1.10004"),
        ask=Decimal("1.10016"),
        source="provider-a",
        sequence=7,
    )


def test_symbol_registry_resolves_aliases_and_rejects_duplicates() -> None:
    """Registry operations are normalized, asynchronous, and conflict-safe."""

    async def exercise() -> None:
        registry = SymbolRegistry()
        await registry.register(eur_usd(), aliases=("eurusd", "EUR_USD"))

        assert (await registry.get("eur-usd")).code == "EUR/USD"
        assert await registry.list_symbols() == (eur_usd(),)
        with pytest.raises(DuplicateSymbolError):
            await registry.register(eur_usd())

    asyncio.run(exercise())


def test_session_manager_handles_local_windows_and_overnight_sessions() -> None:
    """Sessions respect IANA timezone conversion and crossing-midnight windows."""

    async def exercise() -> None:
        manager = SessionManager(
            (
                TradingSession(
                    "london",
                    "Europe/London",
                    time(8),
                    time(16),
                    frozenset({0, 1, 2, 3, 4}),
                ),
                TradingSession(
                    "overnight",
                    "UTC",
                    time(22),
                    time(2),
                    frozenset({0}),
                ),
            )
        )

        london = await manager.active_sessions(datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc))
        overnight = await manager.active_sessions(datetime(2026, 1, 6, 1, 0, tzinfo=timezone.utc))

        assert tuple(session.session_id for session in london) == ("london",)
        assert tuple(session.session_id for session in overnight) == ("overnight",)

    asyncio.run(exercise())


def test_validation_engine_reports_all_input_defects() -> None:
    """Validation aggregates provider payload defects without throwing."""
    report = ValidationEngine().validate_raw_tick(
        RawTick(
            symbol=" ",
            timestamp=datetime(2026, 1, 1),
            bid=Decimal("2"),
            ask=Decimal("1"),
            source=" ",
            bid_size=Decimal("-1"),
            sequence=-1,
        )
    )

    assert not report.is_valid
    assert {issue.field for issue in report.issues} == {
        "symbol",
        "source",
        "timestamp",
        "bid",
        "bid_size",
        "sequence",
    }


def test_manager_requires_start_then_normalizes_stores_and_publishes() -> None:
    """Manager coordinates injected dependencies and isolates bad publishers."""

    async def exercise() -> None:
        normalizer = NormalizationEngine()
        registry = SymbolRegistry(normalizer)
        await registry.register(eur_usd(), aliases=("EURUSD",))
        sessions = SessionManager(
            (
                TradingSession(
                    "london",
                    "Europe/London",
                    time(8),
                    time(16),
                    frozenset({0, 1, 2, 3, 4}),
                ),
            )
        )
        manager = MarketDataManager(
            registry,
            sessions,
            ValidationEngine(),
            normalizer,
        )
        receiver = RecordingPublisher()
        await manager.subscribe("receiver", receiver)
        await manager.subscribe("failing", FailingPublisher())

        with pytest.raises(EngineNotRunningError):
            await manager.process_tick(raw_tick())

        await manager.start()
        snapshot = await manager.process_tick(raw_tick())

        assert snapshot.tick.symbol == "EUR/USD"
        assert snapshot.tick.bid == Decimal("1.1000")
        assert snapshot.tick.ask == Decimal("1.1002")
        assert snapshot.active_sessions == ("london",)
        assert receiver.snapshots == [snapshot]
        assert await manager.latest_tick("EURUSD") == snapshot.tick
        assert await manager.health() == {
            "running": True,
            "accepted_ticks": 1,
            "symbols_with_latest_tick": 1,
            "subscribers": 2,
        }

        await manager.stop()

    asyncio.run(exercise())


def test_manager_rejects_invalid_raw_payload_without_mutating_state() -> None:
    """Rejected data cannot alter market state or accepted sequence numbers."""

    async def exercise() -> None:
        normalizer = NormalizationEngine()
        registry = SymbolRegistry(normalizer)
        await registry.register(eur_usd(), aliases=("EURUSD",))
        manager = MarketDataManager(
            registry,
            SessionManager(),
            ValidationEngine(),
            normalizer,
        )
        await manager.start()

        with pytest.raises(InvalidMarketDataError, match="timestamp"):
            await manager.process_tick(
                RawTick(
                    symbol="EURUSD",
                    timestamp=datetime(2026, 1, 1),
                    bid=Decimal("1"),
                    ask=Decimal("1.1"),
                    source="provider-a",
                )
            )

        assert (await manager.health())["accepted_ticks"] == 0
        assert await manager.latest_tick("EURUSD") is None

    asyncio.run(exercise())
