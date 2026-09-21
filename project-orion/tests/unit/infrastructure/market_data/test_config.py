"""Unit tests for MarketDataConfig."""

import os
import pytest

from libraries.infrastructure.market_data.config import (
    MarketDataConfig,
    MarketDataConfigError,
)


class TestMarketDataConfig:
    """Test MarketDataConfig validation and environment loading."""

    def test_default_config(self) -> None:
        cfg = MarketDataConfig()
        assert cfg.provider_name == "mock"
        assert cfg.timeout_seconds == 10.0
        assert cfg.rate_limit_per_minute == 60
        assert cfg.stale_threshold_seconds == 30.0

    def test_ssrf_protection_rejects_unallowlisted_host(self) -> None:
        with pytest.raises(MarketDataConfigError, match="not in allowlisted"):
            MarketDataConfig(
                provider_name="custom",
                base_url="https://malicious-external-site.com/api",
            )

    def test_invalid_scheme_raises_error(self) -> None:
        with pytest.raises(MarketDataConfigError, match="Invalid URL scheme"):
            MarketDataConfig(
                provider_name="custom",
                base_url="ftp://api.twelvedata.com",
            )

    def test_invalid_timeout_raises_error(self) -> None:
        with pytest.raises(MarketDataConfigError, match="timeout_seconds must be positive"):
            MarketDataConfig(timeout_seconds=-1.0)

    def test_invalid_retries_raises_error(self) -> None:
        with pytest.raises(MarketDataConfigError, match="max_retries must be between"):
            MarketDataConfig(max_retries=20)

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ORION_MARKET_DATA_PROVIDER", "twelvedata")
        monkeypatch.setenv("ORION_MARKET_DATA_API_KEY", "test_key_123")
        monkeypatch.setenv("ORION_MARKET_DATA_TIMEOUT", "5.0")
        monkeypatch.setenv("ORION_MARKET_DATA_RATE_LIMIT", "30")

        cfg = MarketDataConfig.from_env()
        assert cfg.provider_name == "twelvedata"
        assert cfg.api_key == "test_key_123"
        assert cfg.timeout_seconds == 5.0
        assert cfg.rate_limit_per_minute == 30
