"""Twelve Data external market data provider adapter."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

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
from libraries.infrastructure.market_data.circuit_breaker import CircuitBreaker
from libraries.infrastructure.market_data.config import MarketDataConfig
from libraries.infrastructure.market_data.rate_limiter import AsyncTokenBucketRateLimiter

logger = logging.getLogger("orion.market_data.twelve_data")

_TIMEFRAME_TO_TWELVE_DATA: dict[BarType, str] = {
    BarType.M1: "1min",
    BarType.M5: "5min",
    BarType.M15: "15min",
    BarType.M30: "30min",
    BarType.H1: "1h",
    BarType.H4: "4h",
    BarType.D1: "1day",
    BarType.W1: "1week",
    BarType.MN1: "1month",
}


class TwelveDataMarketDataProvider:
    """Production provider adapter communicating with Twelve Data REST API."""

    def __init__(
        self,
        config: MarketDataConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._provider_name = "twelvedata"
        self._base_url = config.base_url.rstrip("/")
        self._api_key = config.api_key
        self._client = http_client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._owns_client = http_client is None
        self._rate_limiter = AsyncTokenBucketRateLimiter(rate_per_minute=config.rate_limit_per_minute)
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def close(self) -> None:
        """Close underlying HTTP client if owned."""
        if self._owns_client and not self._client.is_closed:
            await self._client.aclose()

    async def is_connected(self) -> bool:
        """Check whether provider endpoint is reachable."""
        return self._circuit_breaker.state != "open"

    async def health_check(self) -> dict[str, Any]:
        """Return connectivity and circuit breaker status."""
        return {
            "status": "healthy" if self._circuit_breaker.state == "closed" else "degraded",
            "provider": self._provider_name,
            "circuit_breaker": self._circuit_breaker.state,
            "failure_count": self._circuit_breaker.failure_count,
            "base_url": self._base_url,
        }

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch real-time quote snapshot from Twelve Data /quote endpoint."""
        canonical = normalize_symbol(symbol)
        url = f"{self._base_url}/quote"
        params = {"symbol": canonical, "apikey": self._api_key}

        data = await self._execute_request_with_retry(url, params)
        if "code" in data and data.get("code") != 200:
            msg = data.get("message", "Unknown provider error")
            if data.get("code") == 429:
                raise RateLimitExceededError(f"Twelve Data rate limit exceeded: {msg}")
            if data.get("code") in (400, 404):
                raise SymbolNotFoundError(f"Symbol '{symbol}' not found: {msg}")
            raise ProviderConnectionError(f"Twelve Data API error: {msg}")

        try:
            bid = Decimal(str(data.get("bid") or data.get("close") or data["previous_close"]))
            ask = Decimal(str(data.get("ask") or (bid + Decimal("0.00010"))))
            ts_str = data.get("datetime")
            ts = datetime.now(timezone.utc)
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    ts = datetime.now(timezone.utc)

            return Quote(
                symbol=canonical,
                bid=bid,
                ask=ask,
                timestamp=ts,
                provider=self._provider_name,
                metadata={"name": data.get("name", "")},
            )
        except (KeyError, ValueError) as err:
            raise ProviderConnectionError(f"Failed to parse Twelve Data quote response: {err}") from err

    async def get_candles(
        self,
        symbol: str,
        timeframe: BarType,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[OHLCV]:
        """Fetch historical time series candles from Twelve Data /time_series endpoint."""
        canonical = normalize_symbol(symbol)
        interval = _TIMEFRAME_TO_TWELVE_DATA.get(timeframe, "1h")
        url = f"{self._base_url}/time_series"
        clamped_limit = max(1, min(limit, 1000))
        params: dict[str, Any] = {
            "symbol": canonical,
            "interval": interval,
            "outputsize": clamped_limit,
            "apikey": self._api_key,
        }
        if start:
            params["start_date"] = start.strftime("%Y-%m-%d %H:%M:%S")
        if end:
            params["end_date"] = end.strftime("%Y-%m-%d %H:%M:%S")

        data = await self._execute_request_with_retry(url, params)
        if "code" in data and data.get("code") != 200:
            msg = data.get("message", "Unknown error")
            if data.get("code") == 429:
                raise RateLimitExceededError(f"Twelve Data rate limit exceeded: {msg}")
            raise ProviderConnectionError(f"Twelve Data error: {msg}")

        raw_values = data.get("values", [])
        if not raw_values:
            raise DataUnavailableError(f"No historical candles returned for {symbol} ({interval})")

        candles: list[OHLCV] = []
        for v in reversed(raw_values):
            try:
                ts = datetime.fromisoformat(v["datetime"]).replace(tzinfo=timezone.utc)
                candles.append(
                    OHLCV(
                        symbol=canonical,
                        timestamp=ts,
                        open=Decimal(str(v["open"])),
                        high=Decimal(str(v["high"])),
                        low=Decimal(str(v["low"])),
                        close=Decimal(str(v["close"])),
                        volume=Decimal(str(v.get("volume", "0"))),
                        bar_type=timeframe,
                    )
                )
            except (KeyError, ValueError):
                continue

        return candles

    async def _execute_request_with_retry(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute HTTP GET through rate limiter, circuit breaker, and bounded backoff."""
        await self._rate_limiter.acquire()

        async def _call() -> dict[str, Any]:
            retries = 0
            backoff = self._config.backoff_factor

            while True:
                try:
                    response = await self._client.get(url, params=params)
                    if response.status_code == 429:
                        raise RateLimitExceededError("HTTP 429 Rate Limit Exceeded")
                    response.raise_for_status()
                    return response.json()
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    retries += 1
                    if retries >= self._config.max_retries:
                        logger.error("Provider request failed after %d retries: %s", retries, exc)
                        raise ProviderConnectionError(f"Twelve Data request failed: {exc}") from exc
                    wait_time = backoff ** retries
                    logger.warning("Provider request error (%s). Retrying in %.1fs...", exc, wait_time)
                    await asyncio.sleep(wait_time)

        return await self._circuit_breaker.execute(_call)
