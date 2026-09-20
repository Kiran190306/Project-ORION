"""Market data polling for the autonomous worker.

Provides simulated tick data for paper-trading cycles when no real market
data provider is available. In production, swap out ``SimulatedTickProvider``
for a real ``TickDataProviderPort`` implementation injected at lifespan.

All prices are Decimal to preserve financial arithmetic precision.
All timestamps are UTC-aware.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

logger = logging.getLogger("trading_engine.worker.market_data")

# Default mid-prices used in simulated mode (paper-trading only)
_DEFAULT_PRICES: dict[str, Decimal] = {
    "EUR/USD": Decimal("1.08500"),
    "GBP/USD": Decimal("1.26300"),
    "USD/JPY": Decimal("149.500"),
    "AUD/USD": Decimal("0.64200"),
    "USD/CAD": Decimal("1.36000"),
    "USD/CHF": Decimal("0.89500"),
    "NZD/USD": Decimal("0.59500"),
}

_DEFAULT_SPREAD_PIPS: dict[str, Decimal] = {
    "EUR/USD": Decimal("0.00010"),
    "GBP/USD": Decimal("0.00012"),
    "USD/JPY": Decimal("0.010"),
}


@dataclass(frozen=True, slots=True)
class MarketTick:
    """Lightweight market tick produced by the poller.

    Carries the minimum information needed to build a ``MarketIntelligenceInput``
    for the ``DecisionEngine``.
    """

    symbol: str
    bid: Decimal
    ask: Decimal
    mid: Decimal
    spread_pips: float
    timestamp: datetime
    source: str
    is_simulated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Return True if the tick contains positive bid and ask prices."""
        return self.bid > Decimal(0) and self.ask > Decimal(0) and self.ask >= self.bid


@dataclass
class PollerStats:
    """Running statistics for the market data poller."""

    polls_attempted: int = 0
    polls_succeeded: int = 0
    polls_failed: int = 0
    stale_ticks: int = 0
    last_poll_at: datetime | None = None


class MarketDataPoller:
    """Polls market data for a configured set of symbols.

    In isolated paper-trading mode (no real provider), produces
    deterministic simulated ticks that satisfy all domain contracts:
    - Decimal bid/ask prices
    - UTC-aware timestamps
    - positive spread

    Args:
        symbols: Sequence of canonical symbols to poll.
        stale_threshold_seconds: Maximum age of a tick before it is considered stale.
    """

    def __init__(
        self,
        symbols: tuple[str, ...],
        stale_threshold_seconds: float = 30.0,
    ) -> None:
        self._symbols = symbols
        self._stale_threshold = stale_threshold_seconds
        self._latest: dict[str, MarketTick] = {}
        self._lock = asyncio.Lock()
        self._stats = PollerStats()

    @property
    def symbols(self) -> tuple[str, ...]:
        return self._symbols

    @property
    def stats(self) -> PollerStats:
        return self._stats

    async def poll(self) -> dict[str, MarketTick]:
        """Fetch the latest tick for all configured symbols.

        Returns a dict of ``{symbol: MarketTick}`` for every symbol that
        returned valid, fresh data. Symbols that fail are excluded silently
        (error is logged) so one bad symbol cannot block others.
        """
        results: dict[str, MarketTick] = {}
        for symbol in self._symbols:
            try:
                tick = await self._fetch_tick(symbol)
                if tick is None:
                    continue
                if not tick.is_valid:
                    logger.warning("Invalid tick for %s – skipping.", symbol)
                    continue
                async with self._lock:
                    self._latest[symbol] = tick
                results[symbol] = tick
                self._stats.polls_succeeded += 1
            except Exception as exc:  # noqa: BLE001
                self._stats.polls_failed += 1
                logger.error("Failed to poll market data for %s: %s", symbol, exc)
            finally:
                self._stats.polls_attempted += 1

        self._stats.last_poll_at = datetime.now(timezone.utc)
        return results

    async def latest(self, symbol: str) -> MarketTick | None:
        """Return the most recently polled tick for ``symbol``, or None if stale/missing."""
        async with self._lock:
            tick = self._latest.get(symbol)
        if tick is None:
            return None
        age = (datetime.now(timezone.utc) - tick.timestamp).total_seconds()
        if age > self._stale_threshold:
            self._stats.stale_ticks += 1
            logger.warning(
                "Stale tick for %s (age=%.1fs > threshold=%.1fs).",
                symbol,
                age,
                self._stale_threshold,
            )
            return None
        return tick

    async def _fetch_tick(self, symbol: str) -> MarketTick | None:
        """Produce a simulated paper-trading tick for the given symbol.

        In a production setup, this method would be replaced by injection
        of a real ``TickDataProviderPort`` implementation. For Sprint-4,
        simulated ticks guarantee deterministic, framework-free paper trading.
        """
        mid = _DEFAULT_PRICES.get(symbol)
        if mid is None:
            # Symbol not in our simulated universe; produce a generic mid
            mid = Decimal("1.00000")

        half_spread = _DEFAULT_SPREAD_PIPS.get(symbol, Decimal("0.00010"))
        bid = mid - half_spread
        ask = mid + half_spread
        spread_pips_val = float(half_spread * 2 * Decimal(10000))

        return MarketTick(
            symbol=symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            spread_pips=spread_pips_val,
            timestamp=datetime.now(timezone.utc),
            source="simulated",
            is_simulated=True,
        )
