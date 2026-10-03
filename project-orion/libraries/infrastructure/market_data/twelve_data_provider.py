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
    InvalidBarError,
    ProviderConnectionError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from libraries.domain.market_data.models import (
    OHLCV,
    BarType,
    Quote,
)
from libraries.domain.market_data.normalization import normalize_symbol
from libraries.domain.market_data.validation import validate_ohlc
from libraries.infrastructure.market_data.circuit_breaker import CircuitBreaker
from libraries.infrastructure.market_data.config import MarketDataConfig
from libraries.infrastructure.market_data.rate_limiter import (
    AsyncTokenBucketRateLimiter,
)

logger = logging.getLogger("orion.market_data.twelve_data")

_MAX_CANDLES_PER_REQUEST: int = 1000
_MAX_PAGINATION_CALLS: int = 100

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

    def _parse_candles_page(
        self,
        raw_values: list[dict[str, Any]],
        symbol: str,
        timeframe: BarType,
        start_utc: datetime | None,
        end_utc: datetime | None,
    ) -> list[OHLCV]:
        """Parse raw Twelve Data candle dicts into validated, UTC-normalized OHLCV domain instances."""
        candles: list[OHLCV] = []
        for v in raw_values:
            try:
                raw_dt = v["datetime"]
                dt = datetime.fromisoformat(raw_dt)
                ts = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

                if start_utc is not None and ts < start_utc:
                    continue
                if end_utc is not None and ts > end_utc:
                    continue

                open_p = Decimal(str(v["open"]))
                high_p = Decimal(str(v["high"]))
                low_p = Decimal(str(v["low"]))
                close_p = Decimal(str(v["close"]))
                volume_p = Decimal(str(v.get("volume", "0")))

                validate_ohlc(open_p, high_p, low_p, close_p, volume_p)

                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=ts,
                        open=open_p,
                        high=high_p,
                        low=low_p,
                        close=close_p,
                        volume=volume_p,
                        bar_type=timeframe,
                    )
                )
            except (KeyError, ValueError, TypeError, InvalidBarError) as exc:
                logger.warning(
                    "Skipping malformed Twelve Data candle record for %s (%s): %s",
                    symbol,
                    v,
                    exc,
                )
                continue

        return candles

    async def get_candles(
        self,
        symbol: str,
        timeframe: BarType,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        page_size: int | None = None,
    ) -> list[OHLCV]:
        """Fetch historical time series candles from Twelve Data /time_series endpoint with deterministic range pagination."""
        canonical = normalize_symbol(symbol)
        interval = _TIMEFRAME_TO_TWELVE_DATA.get(timeframe, "1h")
        url = f"{self._base_url}/time_series"

        # 1. UTC Normalization of Boundaries
        start_utc: datetime | None = None
        if start is not None:
            start_utc = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start.astimezone(timezone.utc)

        end_utc: datetime | None = None
        if end is not None:
            end_utc = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end.astimezone(timezone.utc)

        if start_utc is not None and end_utc is not None and start_utc > end_utc:
            raise ValueError(f"Start datetime ({start_utc}) must precede end datetime ({end_utc})")

        # 2. Determine per-request chunk limit
        if page_size is not None:
            chunk_limit = max(1, min(page_size, _MAX_CANDLES_PER_REQUEST))
        elif start_utc is not None and end_utc is not None:
            if limit < _MAX_CANDLES_PER_REQUEST and limit != 100:
                chunk_limit = max(1, min(limit, _MAX_CANDLES_PER_REQUEST))
            else:
                chunk_limit = _MAX_CANDLES_PER_REQUEST
        else:
            chunk_limit = max(1, min(limit, _MAX_CANDLES_PER_REQUEST))

        # 3. Path A: Unbounded date range (retrieve latest `limit` candles)
        if start_utc is None and end_utc is None:
            return await self._get_latest_candles(
                url=url,
                canonical=canonical,
                interval=interval,
                timeframe=timeframe,
                limit=limit,
                chunk_limit=chunk_limit,
            )

        # 4. Path B: Single boundary or full historical date range pagination
        if start_utc is None and end_utc is not None:
            return await self._get_latest_candles(
                url=url,
                canonical=canonical,
                interval=interval,
                timeframe=timeframe,
                limit=limit,
                chunk_limit=chunk_limit,
                initial_end_dt=end_utc,
            )

        effective_end_utc = end_utc or datetime.now(timezone.utc)
        return await self._get_range_candles(
            url=url,
            canonical=canonical,
            interval=interval,
            timeframe=timeframe,
            start_utc=start_utc,
            end_utc=effective_end_utc,
            chunk_limit=chunk_limit,
        )

    async def _get_latest_candles(
        self,
        url: str,
        canonical: str,
        interval: str,
        timeframe: BarType,
        limit: int,
        chunk_limit: int,
        initial_end_dt: datetime | None = None,
    ) -> list[OHLCV]:
        """Retrieve the latest `limit` candles, paginating backwards if limit exceeds chunk_limit."""
        target_limit = max(1, limit)
        all_candles_by_ts: dict[datetime, OHLCV] = {}
        current_end_dt: datetime | None = initial_end_dt
        calls = 0
        last_oldest_ts: datetime | None = None

        while len(all_candles_by_ts) < target_limit:
            calls += 1
            if calls > _MAX_PAGINATION_CALLS:
                raise DataUnavailableError(
                    f"Twelve Data pagination limit exceeded ({_MAX_PAGINATION_CALLS} calls) for {canonical}"
                )

            needed = target_limit - len(all_candles_by_ts)
            req_size = max(1, min(needed, chunk_limit))

            params: dict[str, Any] = {
                "symbol": canonical,
                "interval": interval,
                "outputsize": req_size,
                "apikey": self._api_key,
                "timezone": "UTC",
            }
            if current_end_dt is not None:
                params["end_date"] = current_end_dt.strftime("%Y-%m-%d %H:%M:%S")

            data = await self._execute_request_with_retry(url, params)
            if "code" in data and data.get("code") != 200:
                msg = data.get("message", "Unknown error")
                if data.get("code") == 429:
                    raise RateLimitExceededError(f"Twelve Data rate limit exceeded: {msg}")
                if data.get("code") in (400, 404):
                    raise SymbolNotFoundError(f"Symbol '{canonical}' not found: {msg}")
                raise ProviderConnectionError(f"Twelve Data error: {msg}")

            raw_values = data.get("values", [])
            if not raw_values:
                if calls == 1:
                    raise DataUnavailableError(f"No historical candles returned for {canonical} ({interval})")
                break

            page_candles = self._parse_candles_page(raw_values, canonical, timeframe, None, initial_end_dt)
            if not page_candles:
                if calls == 1:
                    raise DataUnavailableError(f"No valid historical candles returned for {canonical} ({interval})")
                break

            page_oldest_ts = min(c.timestamp for c in page_candles)
            if last_oldest_ts is not None and page_oldest_ts >= last_oldest_ts:
                raise DataUnavailableError(
                    f"Twelve Data pagination progress guard triggered: oldest timestamp ({page_oldest_ts}) did not precede previous ({last_oldest_ts}) for {canonical}"
                )

            new_count = 0
            for c in page_candles:
                if c.timestamp not in all_candles_by_ts:
                    all_candles_by_ts[c.timestamp] = c
                    new_count += 1

            if calls > 1 and new_count == 0:
                raise DataUnavailableError(
                    f"Twelve Data pagination progress guard triggered: 0 new candles returned for {canonical}"
                )

            last_oldest_ts = page_oldest_ts

            if len(raw_values) < req_size:
                break

            current_end_dt = page_oldest_ts

        sorted_candles = sorted(all_candles_by_ts.values(), key=lambda c: c.timestamp)
        if len(sorted_candles) > target_limit:
            sorted_candles = sorted_candles[-target_limit:]

        return sorted_candles

    async def _get_range_candles(
        self,
        url: str,
        canonical: str,
        interval: str,
        timeframe: BarType,
        start_utc: datetime,
        end_utc: datetime,
        chunk_limit: int,
    ) -> list[OHLCV]:
        """Retrieve bounded historical candles across date range [start_utc, end_utc] in distinct chunks."""
        current_end_dt = end_utc
        all_candles_by_ts: dict[datetime, OHLCV] = {}
        seen_request_ranges: set[tuple[str, str]] = set()
        calls = 0
        last_oldest_ts: datetime | None = None
        req_start_str = start_utc.strftime("%Y-%m-%d %H:%M:%S")

        while True:
            calls += 1
            if calls > _MAX_PAGINATION_CALLS:
                raise DataUnavailableError(
                    f"Twelve Data pagination limit exceeded ({_MAX_PAGINATION_CALLS} requests) for {canonical}"
                )

            req_end_str = current_end_dt.strftime("%Y-%m-%d %H:%M:%S")
            range_key = (req_start_str, req_end_str)
            if range_key in seen_request_ranges:
                raise DataUnavailableError(
                    f"Twelve Data pagination loop detected: range [{req_start_str}, {req_end_str}] requested repeatedly for {canonical}"
                )
            seen_request_ranges.add(range_key)

            params: dict[str, Any] = {
                "symbol": canonical,
                "interval": interval,
                "outputsize": chunk_limit,
                "apikey": self._api_key,
                "start_date": req_start_str,
                "end_date": req_end_str,
                "timezone": "UTC",
            }

            data = await self._execute_request_with_retry(url, params)
            if "code" in data and data.get("code") != 200:
                msg = data.get("message", "Unknown error")
                if data.get("code") == 429:
                    raise RateLimitExceededError(f"Twelve Data rate limit exceeded: {msg}")
                if data.get("code") in (400, 404):
                    raise SymbolNotFoundError(f"Symbol '{canonical}' not found: {msg}")
                raise ProviderConnectionError(f"Twelve Data error: {msg}")

            raw_values = data.get("values", [])
            if not raw_values:
                if calls == 1:
                    raise DataUnavailableError(f"No historical candles returned for {canonical} ({interval})")
                raise DataUnavailableError(
                    f"Twelve Data returned empty page when querying range [{req_start_str}, {req_end_str}] for {canonical}; cannot verify complete range"
                )

            page_candles = self._parse_candles_page(
                raw_values=raw_values,
                symbol=canonical,
                timeframe=timeframe,
                start_utc=start_utc,
                end_utc=end_utc,
            )

            if not page_candles:
                if calls == 1:
                    raise DataUnavailableError(
                        f"No valid candles within requested range for {canonical} ({interval})"
                    )
                raise DataUnavailableError(
                    f"Twelve Data returned no valid candles within bounds for {canonical} in range [{req_start_str}, {req_end_str}]"
                )

            page_oldest_ts = min(c.timestamp for c in page_candles)

            if last_oldest_ts is not None and page_oldest_ts >= last_oldest_ts:
                raise DataUnavailableError(
                    f"Twelve Data pagination progress guard triggered: oldest timestamp ({page_oldest_ts}) did not precede previous oldest ({last_oldest_ts}) for {canonical}"
                )

            new_count = 0
            for c in page_candles:
                if c.timestamp not in all_candles_by_ts:
                    all_candles_by_ts[c.timestamp] = c
                    new_count += 1

            if calls > 1 and new_count == 0:
                raise DataUnavailableError(
                    f"Twelve Data pagination progress guard triggered: 0 new candles returned in range [{req_start_str}, {req_end_str}] for {canonical}"
                )

            last_oldest_ts = page_oldest_ts

            # Termination conditions
            reached_start = page_oldest_ts <= start_utc
            exhausted_history = len(raw_values) < chunk_limit

            if reached_start or exhausted_history:
                break

            current_end_dt = page_oldest_ts

        sorted_candles = sorted(all_candles_by_ts.values(), key=lambda c: c.timestamp)
        if not sorted_candles:
            raise DataUnavailableError(f"No historical candles returned for {canonical} ({interval})")

        return sorted_candles

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
