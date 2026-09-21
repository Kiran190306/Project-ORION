"""Unit tests for MockMarketDataProvider."""

from __future__ import annotations

from decimal import Decimal
import pytest

from libraries.domain.market_data.exceptions import (
    ProviderConnectionError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.models import BarType
from libraries.infrastructure.market_data.mock_provider import MockMarketDataProvider


@pytest.mark.asyncio
class TestMockMarketDataProvider:
    """Test MockMarketDataProvider responses and fault injection."""

    async def test_get_quote_valid_symbol(self) -> None:
        provider = MockMarketDataProvider()
        quote = await provider.get_quote("EUR/USD")
        assert quote.symbol == "EUR/USD"
        assert quote.bid > Decimal("0")
        assert quote.ask > quote.bid
        assert quote.mid == (quote.bid + quote.ask) / Decimal("2")
        assert quote.provider == "mock"

    async def test_get_quote_unsupported_symbol_raises_error(self) -> None:
        provider = MockMarketDataProvider()
        with pytest.raises(SymbolNotFoundError):
            await provider.get_quote("UNSUPPORTED/PAIR")

    async def test_get_candles_returns_valid_bars(self) -> None:
        provider = MockMarketDataProvider()
        candles = await provider.get_candles("EUR/USD", BarType.M1, limit=5)
        assert len(candles) == 5
        for c in candles:
            assert c.symbol == "EUR/USD"
            assert c.low <= c.open <= c.high
            assert c.low <= c.close <= c.high
            assert c.volume >= Decimal("0")

    async def test_health_check(self) -> None:
        provider = MockMarketDataProvider()
        health = await provider.health_check()
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert "EUR/USD" in health["symbols_supported"]

    async def test_fault_injection_timeout(self) -> None:
        provider = MockMarketDataProvider()
        provider.simulate_timeout = True
        with pytest.raises(TimeoutError):
            await provider.get_quote("EUR/USD")

    async def test_fault_injection_disconnect(self) -> None:
        provider = MockMarketDataProvider()
        provider.simulate_disconnect = True
        with pytest.raises(ProviderConnectionError):
            await provider.get_quote("EUR/USD")

    async def test_fault_injection_rate_limit(self) -> None:
        provider = MockMarketDataProvider()
        provider.simulate_rate_limit = True
        with pytest.raises(RateLimitExceededError):
            await provider.get_quote("EUR/USD")
