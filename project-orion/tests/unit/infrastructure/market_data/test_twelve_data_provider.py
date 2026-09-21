"""Unit tests for TwelveDataMarketDataProvider using mock HTTP transport."""

from __future__ import annotations

import json
from decimal import Decimal
import httpx
import pytest

from libraries.domain.market_data.exceptions import (
    ProviderConnectionError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.models import BarType
from libraries.infrastructure.market_data.config import MarketDataConfig
from libraries.infrastructure.market_data.twelve_data_provider import TwelveDataMarketDataProvider


@pytest.mark.asyncio
class TestTwelveDataMarketDataProvider:
    """Test TwelveDataMarketDataProvider request mapping, responses, and error handling."""

    async def test_get_quote_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/quote"
            assert "symbol=EUR%2FUSD" in str(request.url) or "symbol=EUR/USD" in str(request.url)
            assert "apikey=test_secret" in str(request.url)
            payload = {
                "symbol": "EUR/USD",
                "name": "Euro / US Dollar",
                "exchange": "Forex",
                "datetime": "2026-09-21 10:00:00",
                "bid": "1.08520",
                "ask": "1.08535",
                "close": "1.08525",
                "previous_close": "1.08500",
            }
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            quote = await provider.get_quote("EUR/USD")
            assert quote.symbol == "EUR/USD"
            assert quote.bid == Decimal("1.08520")
            assert quote.ask == Decimal("1.08535")
            assert quote.mid == Decimal("1.085275")
            assert quote.provider == "twelvedata"

    async def test_get_quote_rate_limit_429(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"code": 429, "message": "You have exceeded your API rate limit"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
                max_retries=1,
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            with pytest.raises(RateLimitExceededError):
                await provider.get_quote("EUR/USD")

    async def test_get_quote_symbol_not_found(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"code": 400, "message": "Symbol not found"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            with pytest.raises(SymbolNotFoundError):
                await provider.get_quote("EUR/USD")

    async def test_get_candles_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/time_series"
            payload = {
                "meta": {"symbol": "EUR/USD", "interval": "1h"},
                "values": [
                    {
                        "datetime": "2026-09-21 10:00:00",
                        "open": "1.08500",
                        "high": "1.08700",
                        "low": "1.08450",
                        "close": "1.08650",
                        "volume": "1200",
                    },
                    {
                        "datetime": "2026-09-21 09:00:00",
                        "open": "1.08400",
                        "high": "1.08550",
                        "low": "1.08350",
                        "close": "1.08500",
                        "volume": "1100",
                    },
                ],
                "status": "ok",
            }
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            candles = await provider.get_candles("EUR/USD", BarType.H1, limit=2)
            assert len(candles) == 2
            assert candles[0].open == Decimal("1.08400")  # Ordered chronologically
            assert candles[1].close == Decimal("1.08650")
