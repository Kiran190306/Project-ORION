"""Factory for creating broker adapter instances.

Provides a centralized factory for creating adapter instances and
routing targets based on broker specifications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
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
from libraries.infrastructure.execution.mock_broker import (
    MockBrokerAdapter,
    MockBrokerConfig,
)
from libraries.infrastructure.execution.paper_execution import (
    PaperExecutionAdapter,
    PaperExecutionConfig,
)
from libraries.infrastructure.security.endpoint_validator import (
    BrokerEndpointValidator,
    SecurityViolationError,
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
    environment: str = "SANDBOX"
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

    SUPPORTED_PROVIDERS = frozenset(
        {"paper", "mt5", "oanda", "binance", "mock", "sandbox_mock", "sandbox_oanda"}
    )

    @classmethod
    def create_adapter(cls, spec: ExecutionAdapterSpec) -> BrokerAdapter:
        """Create a broker adapter from a specification.

        Args:
            spec: Adapter specification.

        Returns:
            Configured BrokerAdapter instance.

        Raises:
            SecurityViolationError: If LIVE environment or forbidden production endpoints are supplied.
            ValueError: If the provider is not supported or environment is invalid.
        """
        env_upper = (spec.environment or "SANDBOX").upper()
        if env_upper == "LIVE":
            raise SecurityViolationError(
                "LIVE execution environment is strictly prohibited in Project ORION ($0.00 Capital at Risk)."
            )
        if env_upper not in ("SANDBOX", "LOCAL", "TEST"):
            raise ValueError(
                f"Invalid broker environment: '{spec.environment}'. Supported: LOCAL, SANDBOX."
            )

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

        elif provider in ("mock", "sandbox_mock"):
            endpoint = spec.api_endpoint or "http://mock-broker.internal"
            validated_endpoint = BrokerEndpointValidator.validate_endpoint(
                endpoint, provider="mock", allow_internal_mock=True, resolve_dns=False
            )
            mock_config = MockBrokerConfig(
                broker_name=spec.name or "mock_broker",
                api_endpoint=validated_endpoint,
                account_id=spec.account_id or "mock_acc_001",
                seed=spec.metadata.get("seed", 42),
                initial_balance=spec.metadata.get("initial_balance", Decimal("100000.00")),
                mode=spec.metadata.get("mode", "IMMEDIATE_FILL"),
                metadata=spec.metadata,
            )
            return MockBrokerAdapter(mock_config)

        elif provider in ("oanda", "sandbox_oanda"):
            endpoint = spec.api_endpoint or "https://api-fxpractice.oanda.com"
            validated_endpoint = BrokerEndpointValidator.validate_endpoint(
                endpoint, provider="oanda", resolve_dns=False
            )
            oanda_config = OANDAExecutionConfig(
                broker_name=spec.name or "oanda",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=validated_endpoint,
                account_id=spec.account_id or "",
                metadata=spec.metadata,
            )
            return OANDAExecutionAdapter(oanda_config)

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

        elif provider == "binance":
            endpoint = spec.api_endpoint or "https://testnet.binance.vision"
            validated_endpoint = BrokerEndpointValidator.validate_endpoint(
                endpoint, provider="binance", resolve_dns=False
            )
            binance_config = BinanceExecutionConfig(
                broker_name=spec.name or "binance",
                api_key=spec.api_key,
                api_secret=spec.api_secret,
                api_endpoint=validated_endpoint,
                account_id=spec.account_id or "",
                metadata=spec.metadata,
            )
            return BinanceExecutionAdapter(binance_config)

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
