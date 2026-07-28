"""Factory for creating broker adapter instances.

Provides a centralized factory for creating adapter instances and
routing targets based on broker specifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from libraries.domain.execution.models import OrderType
from libraries.infrastructure.execution.binance_execution import (
    BinanceExecutionAdapter,
    BinanceExecutionConfig,
)
from libraries.infrastructure.execution.broker_adapter import (
    BrokerAdapter,
    BrokerAdapterConfig,
)
from libraries.infrastructure.execution.execution_router import RoutingTarget
from libraries.infrastructure.execution.mt5_execution import (
    MT5ExecutionAdapter,
    MT5ExecutionConfig,
)
from libraries.infrastructure.execution.oanda_execution import (
    OANDAExecutionAdapter,
    OANDAExecutionConfig,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)


@dataclass(frozen=True, slots=True)
class ExecutionAdapterSpec:
    """Specification for creating a broker adapter."""

    provider: str
    name: str = ""
    api_key: str = ""
    api_secret: str = ""
    api_endpoint: str = ""
    account_id: str = ""
    is_paper: bool = False
    priority: int = 100
    supported_symbols: frozenset[str] = frozenset()
    supported_order_types: frozenset[OrderType] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionAdapterFactory:
    """Factory for creating broker adapter instances.

    Provides centralized creation of adapter instances based on
    provider specifications. Supports creating the adapter and
    its associated routing target.
    """

    SUPPORTED_PROVIDERS = frozenset({"paper", "mt5", "oanda", "binance"})

    @classmethod
    def create_adapter(cls, spec: ExecutionAdapterSpec) -> BrokerAdapter:
        """Create a broker adapter from a specification.

        Args:
            spec: Adapter specification.

        Returns:
            Configured BrokerAdapter instance.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = spec.provider.lower()

        if provider == "paper":
            config = PaperExecutionConfig(
                broker_name=spec.name or "paper",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=spec.api_endpoint or "",
                account_id=spec.account_id or "paper_account_001",
                is_paper=True,
                metadata=spec.metadata,
            )
            return PaperExecutionAdapter(config)

        elif provider == "mt5":
            config = MT5ExecutionConfig(
                broker_name=spec.name or "mt5",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=spec.api_endpoint or "",
                account_id=spec.account_id or "",
                mt5_server=spec.metadata.get("mt5_server", ""),
                mt5_path=spec.metadata.get("mt5_path", ""),
                metadata=spec.metadata,
            )
            return MT5ExecutionAdapter(config)

        elif provider == "oanda":
            config = OANDAExecutionConfig(
                broker_name=spec.name or "oanda",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=spec.api_endpoint or "https://api-fxpractice.oanda.com",
                account_id=spec.account_id or "",
                metadata=spec.metadata,
            )
            return OANDAExecutionAdapter(config)

        elif provider == "binance":
            config = BinanceExecutionConfig(
                broker_name=spec.name or "binance",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=spec.api_endpoint or "https://api.binance.com",
                account_id=spec.account_id or "",
                metadata=spec.metadata,
            )
            return BinanceExecutionAdapter(config)

        else:
            raise ValueError(
                f"Unsupported broker provider: {spec.provider}. "
                f"Supported providers: {', '.join(sorted(cls.SUPPORTED_PROVIDERS))}"
            )

    @classmethod
    def create_routing_target(cls, spec: ExecutionAdapterSpec) -> RoutingTarget:
        """Create a routing target from a specification.

        Args:
            spec: Adapter specification.

        Returns:
            RoutingTarget for use with ExecutionRouter.
        """
        return RoutingTarget(
            broker_name=spec.name or spec.provider,
            priority=spec.priority,
            supported_symbols=spec.supported_symbols,
            supported_order_types=spec.supported_order_types,
            metadata=spec.metadata,
        )

    @classmethod
    def create_adapter_with_target(
        cls,
        spec: ExecutionAdapterSpec,
    ) -> tuple[BrokerAdapter, RoutingTarget]:
        """Create both adapter and routing target from a specification.

        Args:
            spec: Adapter specification.

        Returns:
            Tuple of (BrokerAdapter, RoutingTarget).
        """
        adapter = cls.create_adapter(spec)
        target = cls.create_routing_target(spec)
        return adapter, target

    @classmethod
    def is_provider_supported(cls, provider: str) -> bool:
        """Check if a broker provider is supported.

        Args:
            provider: Provider name to check.

        Returns:
            True if the provider is supported.
        """
        return provider.lower() in cls.SUPPORTED_PROVIDERS
