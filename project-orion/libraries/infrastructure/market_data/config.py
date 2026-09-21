"""Configuration for Market Data infrastructure adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


class MarketDataConfigError(Exception):
    """Raised when market data configuration is invalid."""


_DEFAULT_ALLOWLISTED_HOSTS = frozenset({
    "api.twelvedata.com",
    "api.polygon.io",
    "finnhub.io",
    "www.alphavantage.co",
})


@dataclass(frozen=True, slots=True)
class MarketDataConfig:
    """Strongly-typed market data infrastructure configuration."""

    provider_name: str = "mock"
    api_key: str = ""
    base_url: str = "https://api.twelvedata.com"
    timeout_seconds: float = 10.0
    max_retries: int = 3
    backoff_factor: float = 1.5
    rate_limit_per_minute: int = 60
    stale_threshold_seconds: float = 30.0
    allowlisted_hosts: frozenset[str] = field(default_factory=lambda: _DEFAULT_ALLOWLISTED_HOSTS)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise MarketDataConfigError("timeout_seconds must be positive")
        if self.max_retries < 0 or self.max_retries > 10:
            raise MarketDataConfigError("max_retries must be between 0 and 10")
        if self.rate_limit_per_minute <= 0:
            raise MarketDataConfigError("rate_limit_per_minute must be positive")

        # SSRF Protection: Validate base_url against allowlisted hosts when not mock
        if self.provider_name.lower() != "mock":
            parsed = urlparse(self.base_url)
            if parsed.scheme not in ("https", "http"):
                raise MarketDataConfigError(f"Invalid URL scheme: {parsed.scheme}")
            host = parsed.netloc.split(":")[0].lower()
            if host not in self.allowlisted_hosts:
                raise MarketDataConfigError(
                    f"Host '{host}' is not in allowlisted market data providers: {sorted(self.allowlisted_hosts)}"
                )

    @classmethod
    def from_env(cls) -> MarketDataConfig:
        """Load market data configuration from environment variables."""
        provider = os.environ.get("ORION_MARKET_DATA_PROVIDER", "mock").strip().lower()
        api_key = os.environ.get("ORION_MARKET_DATA_API_KEY", "").strip()
        base_url = os.environ.get("ORION_MARKET_DATA_BASE_URL", "https://api.twelvedata.com").strip()

        try:
            timeout = float(os.environ.get("ORION_MARKET_DATA_TIMEOUT", "10.0"))
        except ValueError:
            timeout = 10.0

        try:
            rate_limit = int(os.environ.get("ORION_MARKET_DATA_RATE_LIMIT", "60"))
        except ValueError:
            rate_limit = 60

        try:
            stale_threshold = float(os.environ.get("ORION_MARKET_DATA_STALE_THRESHOLD", "30.0"))
        except ValueError:
            stale_threshold = 30.0

        return cls(
            provider_name=provider,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            rate_limit_per_minute=rate_limit,
            stale_threshold_seconds=stale_threshold,
        )
