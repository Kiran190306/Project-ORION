"""Unit tests for TwelveDataMarketDataProvider using mock HTTP transport."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import httpx
import pytest

from libraries.domain.market_data.exceptions import (
    CircuitBreakerOpenError,
    DataUnavailableError,
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

    async def test_two_page_historical_range_with_boundary_dedup(self) -> None:
        """Test two-page historical range with overlapping boundary candle deduplication."""
        call_count = 0
        calls_params: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            import urllib.parse
            parsed = urllib.parse.urlparse(str(request.url))
            params = urllib.parse.parse_qs(parsed.query)
            end_date = params.get("end_date", [""])[0]

            if end_date == "2026-09-21 10:00:00":
                # Page 1 (newest first)
                return httpx.Response(200, json={
                    "status": "ok",
                    "values": [
                        {"datetime": "2026-09-21 10:00:00", "open": "1.0860", "high": "1.0870", "low": "1.0850", "close": "1.0865", "volume": "100"},
                        {"datetime": "2026-09-21 09:00:00", "open": "1.0850", "high": "1.0865", "low": "1.0845", "close": "1.0860", "volume": "100"},
                    ],
                })
            elif end_date == "2026-09-21 09:00:00":
                # Page 2 (older segment down to 08:00:00, includes 09:00:00 boundary)
                return httpx.Response(200, json={
                    "status": "ok",
                    "values": [
                        {"datetime": "2026-09-21 09:00:00", "open": "1.0850", "high": "1.0865", "low": "1.0845", "close": "1.0860", "volume": "100"},
                        {"datetime": "2026-09-21 08:00:00", "open": "1.0840", "high": "1.0855", "low": "1.0835", "close": "1.0850", "volume": "100"},
                    ],
                })
            return httpx.Response(400, json={"message": f"Unexpected end_date in query: {end_date}"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            start = datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)
            assert len(candles) == 3
            assert call_count == 2
            # Chronologically sorted
            assert candles[0].timestamp == datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            assert candles[1].timestamp == datetime(2026, 9, 21, 9, 0, 0, tzinfo=timezone.utc)
            assert candles[2].timestamp == datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
            # Boundary candle 09:00:00 appears exactly once
            timestamps = [c.timestamp for c in candles]
            assert len(timestamps) == len(set(timestamps))

    async def test_multi_page_historical_range(self) -> None:
        """Test multi-page (3+ pages) historical range retrieval and merging."""
        hours = [
            datetime(2026, 9, 21, h, 0, 0, tzinfo=timezone.utc)
            for h in range(5, 11)  # 05:00, 06:00, 07:00, 08:00, 09:00, 10:00 (6 candles)
        ]
        candles_by_hour = {
            dt.strftime("%Y-%m-%d %H:%M:%S"): {
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "open": "1.0850",
                "high": "1.0860",
                "low": "1.0840",
                "close": "1.0855",
                "volume": "100",
            }
            for dt in hours
        }

        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            query = str(request.url)
            # Find end_date from query
            import urllib.parse
            parsed = urllib.parse.urlparse(query)
            params = urllib.parse.parse_qs(parsed.query)
            end_date_str = params.get("end_date", [""])[0]

            # Return at most 2 candles ending at end_date_str (newest first)
            available = [c for dt_str, c in candles_by_hour.items() if dt_str <= end_date_str]
            available_sorted = sorted(available, key=lambda x: x["datetime"], reverse=True)
            chunk = available_sorted[:2]
            return httpx.Response(200, json={"status": "ok", "values": chunk})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            start = datetime(2026, 9, 21, 5, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)
            assert len(candles) == 6
            assert call_count >= 3
            assert candles[0].timestamp == start
            assert candles[-1].timestamp == end
            # Monotonic order check
            for i in range(len(candles) - 1):
                assert candles[i].timestamp < candles[i + 1].timestamp

    async def test_provider_returning_empty_page_fails_explicitly(self) -> None:
        """Test that an empty page during active pagination raises DataUnavailableError."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={
                    "status": "ok",
                    "values": [
                        {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                        {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                    ],
                })
            # Page 2 returns empty list unexpectedly
            return httpx.Response(200, json={"status": "ok", "values": []})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            with pytest.raises(DataUnavailableError, match="empty page"):
                await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)

    async def test_provider_returning_repeated_page_fails_explicitly(self) -> None:
        """Test that a repeated page without earlier timestamps triggers the progress guard."""
        def handler(request: httpx.Request) -> httpx.Response:
            # Always return the exact same 2 candles
            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                    {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            with pytest.raises(DataUnavailableError, match="progress guard"):
                await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)

    async def test_provider_ignoring_requested_date_boundary_fails_explicitly(self) -> None:
        """Test that provider returning newer timestamps on subsequent call fails explicitly."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={
                    "status": "ok",
                    "values": [
                        {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                        {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                    ],
                })
            # Page 2 returns candles newer than previous oldest
            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 12:00:00", "open": "1.088", "high": "1.089", "low": "1.087", "close": "1.088", "volume": "100"},
                    {"datetime": "2026-09-21 11:00:00", "open": "1.087", "high": "1.088", "low": "1.086", "close": "1.087", "volume": "100"},
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            with pytest.raises(DataUnavailableError):
                await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)

    async def test_requested_start_and_end_boundaries_enforced(self) -> None:
        """Test that returned candles outside [start, end] range are strictly filtered."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 11:00:00", "open": "1.087", "high": "1.088", "low": "1.086", "close": "1.087", "volume": "100"},  # Beyond end
                    {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},  # In range
                    {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},  # In range
                    {"datetime": "2026-09-21 08:00:00", "open": "1.084", "high": "1.085", "low": "1.083", "close": "1.084", "volume": "100"},  # In range
                    {"datetime": "2026-09-21 07:00:00", "open": "1.083", "high": "1.084", "low": "1.082", "close": "1.083", "volume": "100"},  # Before start
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end)
            assert len(candles) == 3
            assert candles[0].timestamp == start
            assert candles[-1].timestamp == end
            for c in candles:
                assert start <= c.timestamp <= end

    async def test_utc_timestamp_normalization(self) -> None:
        """Test UTC normalization across naive, offset, and Z datetimes with explicit timezone query."""
        requested_timezone: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import urllib.parse
            parsed = urllib.parse.urlparse(str(request.url))
            params = urllib.parse.parse_qs(parsed.query)
            requested_timezone.extend(params.get("timezone", []))

            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 10:00:00+02:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                    {"datetime": "2026-09-21 07:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            # Query with naive datetimes
            start = datetime(2026, 9, 21, 7, 0, 0)
            end = datetime(2026, 9, 21, 10, 0, 0)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end)
            assert "UTC" in requested_timezone
            assert len(candles) == 2
            # 10:00+02:00 becomes 08:00 UTC
            assert candles[1].timestamp == datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            assert candles[0].timestamp == datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
            for c in candles:
                assert c.timestamp.tzinfo == timezone.utc

    async def test_decimal_preservation_and_invalid_bar_rejection(self) -> None:
        """Test strict Decimal type preservation and rejection of corrupt OHLC bars."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 10:00:00", "open": "1.08650", "high": "1.08750", "low": "1.08550", "close": "1.08700", "volume": "1250"},
                    {"datetime": "2026-09-21 09:00:00", "open": "1.08500", "high": "1.08300", "low": "1.08600", "close": "1.08500", "volume": "1000"},  # Corrupt: high < low
                    {"datetime": "2026-09-21 08:00:00", "open": "1.08400", "high": "1.08500", "low": "1.08300", "close": "1.08450", "volume": "1100"},
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            start = datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end)
            # Corrupt bar at 09:00:00 was skipped
            assert len(candles) == 2
            assert candles[0].timestamp == datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)
            assert candles[1].timestamp == datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
            for c in candles:
                assert isinstance(c.open, Decimal)
                assert isinstance(c.high, Decimal)
                assert isinstance(c.low, Decimal)
                assert isinstance(c.close, Decimal)
                assert isinstance(c.volume, Decimal)

    async def test_provider_error_handling_429_during_pagination(self) -> None:
        """Test RateLimitExceededError propagation during multi-page pagination."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(200, json={
                    "status": "ok",
                    "values": [
                        {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                        {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                    ],
                })
            return httpx.Response(429, json={"code": 429, "message": "Rate limit exceeded"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
                max_retries=1,
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 7, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            with pytest.raises(RateLimitExceededError):
                await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end, page_size=2)

    async def test_invalid_date_range_raises_value_error(self) -> None:
        """Test that start > end raises a ValueError."""
        config = MarketDataConfig(
            provider_name="twelvedata",
            api_key="test_secret",
            base_url="https://api.twelvedata.com",
        )
        provider = TwelveDataMarketDataProvider(config=config)
        start = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 21, 8, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="must precede end datetime"):
            await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end)

    async def test_dataset_completeness_over_1000_candles(self) -> None:
        """REQUIREMENT 9: Test complete retrieval of >1000 candles across pagination boundaries."""
        # Scenario: 1,200 hourly candles for EUR/USD from 2025-01-01 00:00 to 2025-02-19 23:00
        base_start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        total_candles = 1200
        all_hours = [base_start + timedelta(hours=i) for i in range(total_candles)]
        end_dt = all_hours[-1]  # 2025-02-19 23:00:00

        # Pre-build mocked candle dicts
        candle_data_by_ts: dict[str, dict[str, Any]] = {}
        for i, dt in enumerate(all_hours):
            ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            p = Decimal("1.08000") + Decimal(str(i * 0.00005))
            candle_data_by_ts[ts_str] = {
                "datetime": ts_str,
                "open": str(p),
                "high": str(p + Decimal("0.00030")),
                "low": str(p - Decimal("0.00030")),
                "close": str(p + Decimal("0.00010")),
                "volume": "1000",
            }

        call_count = 0
        requested_end_dates: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            import urllib.parse
            parsed = urllib.parse.urlparse(str(request.url))
            params = urllib.parse.parse_qs(parsed.query)
            end_date_str = params.get("end_date", [""])[0]
            outputsize = int(params.get("outputsize", [1000])[0])
            requested_end_dates.append(end_date_str)

            # Return at most outputsize candles <= end_date_str (newest first)
            available = [c for ts_str, c in candle_data_by_ts.items() if ts_str <= end_date_str]
            available_sorted = sorted(available, key=lambda x: x["datetime"], reverse=True)
            chunk = available_sorted[:outputsize]

            return httpx.Response(200, json={
                "status": "ok",
                "values": chunk,
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=base_start, end=end_dt)

            # Verification of complete dataset
            assert len(candles) == 1200, f"Expected 1200 candles, got {len(candles)}"
            assert call_count == 2, f"Expected exactly 2 pagination requests for 1200 candles with chunk_limit=1000, got {call_count}"

            # Verify chunk 1 requested up to end_dt, chunk 2 requested up to boundary candle
            assert requested_end_dates[0] == end_dt.strftime("%Y-%m-%d %H:%M:%S")

            # First and last timestamps strictly match
            assert candles[0].timestamp == base_start
            assert candles[-1].timestamp == end_dt

            # Monotonic chronological ordering
            for i in range(len(candles) - 1):
                assert candles[i].timestamp < candles[i + 1].timestamp
                # Consecutive hours with exactly 1 hour step
                assert candles[i + 1].timestamp - candles[i].timestamp == timedelta(hours=1)

            # Decimal types preserved throughout
            for c in candles:
                assert isinstance(c.open, Decimal)
                assert isinstance(c.high, Decimal)
                assert isinstance(c.low, Decimal)
                assert isinstance(c.close, Decimal)
                assert isinstance(c.volume, Decimal)
                assert c.timestamp.tzinfo == timezone.utc

    async def test_short_range_behavior_single_page(self) -> None:
        """Test that short range fitting in single page makes exactly one HTTP request."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json={
                "status": "ok",
                "values": [
                    {"datetime": "2026-09-21 10:00:00", "open": "1.086", "high": "1.087", "low": "1.085", "close": "1.086", "volume": "100"},
                    {"datetime": "2026-09-21 09:00:00", "open": "1.085", "high": "1.086", "low": "1.084", "close": "1.085", "volume": "100"},
                ],
            })

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)
            start = datetime(2026, 9, 21, 9, 0, 0, tzinfo=timezone.utc)
            end = datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc)

            candles = await provider.get_candles("EUR/USD", BarType.H1, start=start, end=end)
            assert len(candles) == 2
            assert call_count == 1  # Only 1 request needed

    async def test_circuit_breaker_trips_and_blocks_requests(self) -> None:
        """Test that circuit breaker trips to OPEN after 5 failures and blocks subsequent calls."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"message": "Internal Server Error"})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            config = MarketDataConfig(
                provider_name="twelvedata",
                api_key="test_secret",
                base_url="https://api.twelvedata.com",
                max_retries=1,
            )
            provider = TwelveDataMarketDataProvider(config=config, http_client=client)

            # Trigger 5 failures to trip the circuit breaker
            for _ in range(5):
                with pytest.raises(ProviderConnectionError):
                    await provider.get_quote("EUR/USD")

            # 6th call must be blocked immediately by CircuitBreakerOpenError
            with pytest.raises(CircuitBreakerOpenError):
                await provider.get_quote("EUR/USD")
