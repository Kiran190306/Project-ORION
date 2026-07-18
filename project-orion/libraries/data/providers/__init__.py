"""
Providers Module

Module Description:
This module provides provider abstraction for data platform.
It defines the interface for data providers and provider configuration.

Implementation Checklist:
- [ ] Provider interface
- [ ] Provider configuration
- [ ] Provider registry
- [ ] Provider factory
- [ ] Provider metadata

Dependency Notes:
- Depends on: shared/ (errors), libraries/data/schemas/
- Used by: adapters/, normalizers/, pipelines/
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional

from libraries.data.schemas import OHLC, SymbolMetadata, Tick
from shared.errors import OrionError


class ProviderError(OrionError):
    """Provider error."""

    pass


class ProviderConfig:
    """Provider configuration."""

    def __init__(
        self,
        provider_id: str,
        provider_type: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        rate_limit: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize provider configuration.

        Args:
            provider_id: Unique provider identifier
            provider_type: Provider type (e.g., "broker", "third_party")
            api_key: API key for authentication
            api_secret: API secret for authentication
            base_url: Base URL for API
            timeout: Request timeout in seconds
            rate_limit: Rate limit in requests per minute
            **kwargs: Additional provider-specific configuration
        """
        self.provider_id = provider_id
        self.provider_type = provider_type
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.extra_config = kwargs


class ProviderMetadata:
    """Provider metadata."""

    def __init__(
        self,
        provider_id: str,
        name: str,
        description: str,
        supported_symbols: list[str],
        supported_data_types: list[str],
        supported_timeframes: list[str],
        capabilities: dict[str, bool],
    ) -> None:
        """Initialize provider metadata.

        Args:
            provider_id: Unique provider identifier
            name: Provider name
            description: Provider description
            supported_symbols: List of supported symbols
            supported_data_types: List of supported data types (tick, ohlc)
            supported_timeframes: List of supported timeframes
            capabilities: Dictionary of provider capabilities
        """
        self.provider_id = provider_id
        self.name = name
        self.description = description
        self.supported_symbols = supported_symbols
        self.supported_data_types = supported_data_types
        self.supported_timeframes = supported_timeframes
        self.capabilities = capabilities


class DataProvider(ABC):
    """Abstract data provider interface."""

    def __init__(self, config: ProviderConfig):
        """Initialize data provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self._metadata: Optional[ProviderMetadata] = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to provider."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from provider."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to provider."""
        pass

    @abstractmethod
    def get_metadata(self) -> Optional[ProviderMetadata]:
        """Get provider metadata."""
        pass

    @abstractmethod
    def fetch_ticks(self, symbol: str, start_time: datetime, end_time: datetime) -> list[Tick]:
        """Fetch tick data for symbol and time range."""
        pass

    @abstractmethod
    def fetch_ohlc(
        self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime
    ) -> list[OHLC]:
        """Fetch OHLC data for symbol, timeframe, and time range."""
        pass

    @abstractmethod
    def fetch_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Fetch symbol metadata."""
        pass

    @abstractmethod
    def list_symbols(self) -> list[str]:
        """List available symbols."""
        pass


class ProviderRegistry:
    """Registry for data providers."""

    def __init__(self) -> None:
        """Initialize provider registry."""
        self._providers: dict[str, DataProvider] = {}
        self._provider_classes: dict[str, type[DataProvider]] = {}

    def register_provider_class(
        self, provider_type: str, provider_class: type[DataProvider]
    ) -> None:
        """Register a provider class."""
        self._provider_classes[provider_type] = provider_class

    def create_provider(self, config: ProviderConfig) -> DataProvider:
        """Create provider instance from configuration."""
        provider_class = self._provider_classes.get(config.provider_type)
        if not provider_class:
            raise ProviderError(f"No provider class registered for type: {config.provider_type}")
        return provider_class(config)

    def register_provider(self, provider_id: str, provider: DataProvider) -> None:
        """Register a provider instance."""
        self._providers[provider_id] = provider

    def get_provider(self, provider_id: str) -> Optional[DataProvider]:
        """Get provider by ID."""
        return self._providers.get(provider_id)

    def list_providers(self) -> list[str]:
        """List registered provider IDs."""
        return list(self._providers.keys())

    def remove_provider(self, provider_id: str) -> bool:
        """Remove provider from registry."""
        if provider_id in self._providers:
            del self._providers[provider_id]
            return True
        return False


# Global provider registry instance
_registry = ProviderRegistry()


def get_provider_registry() -> ProviderRegistry:
    """Get global provider registry instance."""
    return _registry


def register_provider_class(provider_type: str, provider_class: type[DataProvider]) -> None:
    """Register a provider class."""
    _registry.register_provider_class(provider_type, provider_class)
