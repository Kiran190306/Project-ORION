"""Factory for creating MarketDataProviderPort instances."""

from __future__ import annotations

import logging

from libraries.domain.market_data.interfaces import MarketDataProviderPort
from libraries.infrastructure.market_data.config import MarketDataConfig
from libraries.infrastructure.market_data.mock_provider import MockMarketDataProvider
from libraries.infrastructure.market_data.twelve_data_provider import TwelveDataMarketDataProvider

logger = logging.getLogger("orion.market_data.factory")


def create_market_data_provider(
    config: MarketDataConfig | None = None,
    provider_type: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> MarketDataProviderPort:
    """Create appropriate market data provider adapter based on configuration.

    If external provider API key is not configured or provider_name is 'mock',
    safely defaults to deterministic MockMarketDataProvider.
    """
    if config is None:
        if provider_type is not None:
            config = MarketDataConfig(
                provider_name=provider_type,
                api_key=api_key or "",
                base_url=base_url or "https://api.twelvedata.com",
            )
        else:
            config = MarketDataConfig.from_env()

    if config.provider_name.lower() == "twelvedata" and config.api_key:
        logger.info("Initializing TwelveDataMarketDataProvider with base_url=%s", config.base_url)
        return TwelveDataMarketDataProvider(config=config)

    logger.info("Initializing deterministic MockMarketDataProvider (offline/test mode)")
    return MockMarketDataProvider()

