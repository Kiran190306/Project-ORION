"""Deterministic mock market data provider for offline development and testing."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.market_data.exceptions import (
    DataUnavailableError,
    ProviderConnectionError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.models import (
    BarType,
    OHLCV,
    Quote,
)
from libraries.domain.market_data.normalization import normalize_symbol

_MOCK_BASE_PRICES: dict[str, Decimal] = {
    "EUR/USD": Decimal("1.08500"),
    "GBP/USD": Decimal("1.26300"),
    "USD/JPY": Decimal("149.500"),
    "USD/CHF": Decimal("0.89500"),
    "AUD/USD": Decimal("0.64200"),
    "USD/CAD": Decimal("1.36000"),
    "NZD/USD": Decimal("0.59500"),
    "XAU/USD": Decimal("2350.00"),
}

_MOCK_SPREAD_PIPS: dict[str, Decimal] = {
    "EUR/USD": Decimal("0.00010"),
    "GBP/USD": Decimal("0.00015"),
    "USD/JPY": Decimal("0.015"),
    "USD/CHF": Decimal("0.00015"),
    "AUD/USD": Decimal("0.00015"),
    "USD/CAD": Decimal("0.00020"),
    "NZD/USD": Decimal("0.00020"),
    "XAU/USD": Decimal("0.30"),
}


class MockMarketDataProvider:
    """Offline, deterministic market data provider implementation of MarketDataProviderPort."""

    def __init__(
        self,
        base_prices: dict[str, Decimal] | None = None,
        spread_pips: dict[str, Decimal] | None = None,
        latency_ms: float = 2.0,
    ) -> None:
        self._provider_name = "mock"
        self._base_prices = dict(base_prices or _MOCK_BASE_PRICES)
        self._spread_pips = dict(spread_pips or _MOCK_SPREAD_PIPS)
        self._latency_ms = latency_ms
        self._connected = True

        # Fault injection toggles for testing
        self.simulate_timeout = False
        self.simulate_disconnect = False
        self.simulate_stale = False
        self.simulate_rate_limit = False
        self.simulate_error = False
        self.custom_quotes: dict[str, Quote] = {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def is_connected(self) -> bool:
        return self._connected and not self.simulate_disconnect

    async def health_check(self) -> dict[str, Any]:
        connected = await self.is_connected()
        return {
            "status": "healthy" if connected else "disconnected",
            "provider": self._provider_name,
            "connected": connected,
            "latency_ms": self._latency_ms,
            "symbols_supported": list(self._base_prices.keys()),
        }

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch latest deterministic quote for canonical symbol."""
        if self.simulate_timeout:
            raise TimeoutError("Mock provider request timed out")
        if self.simulate_disconnect or not self._connected:
            raise ProviderConnectionError("Mock provider is disconnected")
        if self.simulate_rate_limit:
            raise RateLimitExceededError("Mock provider rate limit exceeded (429)")
        if self.simulate_error:
            raise RuntimeError("Mock provider simulated internal error")

        canonical = normalize_symbol(symbol)

        if canonical in self.custom_quotes:
            return self.custom_quotes[canonical]

        if canonical not in self._base_prices:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not supported by mock provider")

        mid = self._base_prices[canonical]
        half_spread = self._spread_pips.get(canonical, Decimal("0.00010")) / Decimal("2")
        bid = mid - half_spread
        ask = mid + half_spread

        ts = datetime.now(timezone.utc)
        if self.simulate_stale:
            ts = ts - timedelta(minutes=15)

        return Quote(
            symbol=canonical,
            bid=bid,
            ask=ask,
            timestamp=ts,
            provider=self._provider_name,
            metadata={"is_mock": True, "source": "deterministic_test_engine"},
        )

    async def get_candles(
        self,
        symbol: str,
        timeframe: BarType,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[OHLCV]:
        """Generate deterministic historical OHLCV bars satisfying all invariants."""
        if self.simulate_timeout:
            raise TimeoutError("Mock provider request timed out")
        if self.simulate_disconnect or not self._connected:
            raise ProviderConnectionError("Mock provider is disconnected")
        if self.simulate_rate_limit:
            raise RateLimitExceededError("Mock provider rate limit exceeded")
        if self.simulate_error:
            raise RuntimeError("Mock provider simulated error")

        canonical = normalize_symbol(symbol)
        if canonical not in self._base_prices:
            raise SymbolNotFoundError(f"Symbol '{symbol}' not supported")

        limit = max(1, min(limit, 1000))
        ref_time = end or datetime.now(timezone.utc)
        step = timedelta(minutes=5)
        if timeframe in (BarType.H1, BarType.H4):
            step = timedelta(hours=1)
        elif timeframe == BarType.D1:
            step = timedelta(days=1)

        mid = self._base_prices[canonical]
        candles: list[OHLCV] = []

        for i in range(limit):
            candle_time = ref_time - (step * (limit - i))
            offset = Decimal(str((i % 10 - 5) * 0.0002))
            open_p = mid + offset
            close_p = open_p + Decimal("0.0001")
            high_p = max(open_p, close_p) + Decimal("0.0003")
            low_p = min(open_p, close_p) - Decimal("0.0003")
            vol = Decimal(str(500 + (i * 10)))

            candles.append(
                OHLCV(
                    symbol=canonical,
                    timestamp=candle_time,
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    volume=vol,
                    bar_type=timeframe,
                    metadata={"is_mock": True},
                )
            )

        return candles
