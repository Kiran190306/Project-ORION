"""Abstract base class defining the broker adapter contract.

Every broker adapter must implement the full contract. Adapters act as
infrastructure translators only — no business logic lives inside them.
Broker-specific SDKs must never leak outside the infrastructure layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.execution.models import (
    BrokerOrderId,
    ExecutionResult,
    Fill,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)


class ExecutionAdapterError(Exception):
    """Base exception for broker adapter errors."""

    def __init__(self, message: str, broker_name: str = "") -> None:
        self.broker_name = broker_name
        super().__init__(message)


class AdapterConnectionError(ExecutionAdapterError):
    """Raised when connection to the broker fails."""


class AdapterAuthenticationError(ExecutionAdapterError):
    """Raised when broker authentication fails."""


class AdapterOrderRejectedError(ExecutionAdapterError):
    """Raised when the broker rejects an order."""


class AdapterTimeoutError(ExecutionAdapterError):
    """Raised when a broker operation times out."""


class AdapterNotConnectedError(ExecutionAdapterError):
    """Raised when an operation is attempted while disconnected."""


@dataclass(frozen=True, slots=True)
class AccountInfo:
    """Broker account information."""

    account_id: str
    broker_name: str
    balance: Decimal
    equity: Decimal
    margin: Decimal
    margin_free: Decimal
    margin_level: float
    currency: str
    leverage: int
    is_live: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PositionInfo:
    """Open position information."""

    position_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    open_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrderExecutionInfo:
    """Order execution information returned by the broker."""

    broker_order_id: BrokerOrderId
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    fills: tuple[Fill, ...] = ()
    rejection_reason: str = ""
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionSymbolInfo:
    """Symbol/trading instrument information from the broker."""

    symbol: str
    description: str = ""
    digits: int = 5
    pip_size: Decimal = Decimal("0.00001")
    pip_value: Decimal = Decimal("0")
    min_volume: Decimal = Decimal("0.01")
    max_volume: Decimal = Decimal("100")
    volume_step: Decimal = Decimal("0.01")
    spread: float = 0.0
    swap_long: float = 0.0
    swap_short: float = 0.0
    is_trade_allowed: bool = True
    margin_currency: str = "USD"
    margin_rate: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class BrokerAdapterConfig:
    """Base configuration for broker adapters."""

    broker_name: str
    api_key: str = ""
    api_secret: str = ""
    api_endpoint: str = ""
    account_id: str = ""
    is_paper: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


class BrokerAdapter(ABC):
    """Abstract base class for all broker execution adapters.

    Every adapter must implement all methods. Adapters are infrastructure
    translators only — they convert domain Order objects to broker-specific
    API calls and convert broker responses back into domain model objects.

    No business logic exists inside adapters.
    """

    def __init__(self, config: BrokerAdapterConfig) -> None:
        self._config = config
        self._connected = False
        self._last_health_check: datetime | None = None
        self._connection_attempts: int = 0

    @property
    def broker_name(self) -> str:
        return self._config.broker_name

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def config(self) -> BrokerAdapterConfig:
        return self._config

    # ── Connection Lifecycle ──────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the broker.

        Returns:
            True if connection was successful.

        Raises:
            AdapterConnectionError: If connection fails.
            AdapterAuthenticationError: If authentication fails.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the broker gracefully.

        Returns:
            True if disconnection was successful.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check broker connection health.

        Returns:
            Dict with keys:
                - connected: bool
                - latency_ms: float
                - last_checked: str (ISO timestamp)
                - details: dict (broker-specific)

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    # ── Order Management ──────────────────────────────────────────────

    @abstractmethod
    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        """Submit an order to the broker.

        Args:
            order: Domain Order model to execute.

        Returns:
            OrderExecutionInfo with broker response.

        Raises:
            AdapterOrderRejectedError: If broker rejects the order.
            AdapterTimeoutError: If submission times out.
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def modify_order(
        self,
        broker_order_id: BrokerOrderId,
        *,
        quantity: Decimal | None = None,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
    ) -> OrderExecutionInfo:
        """Modify an existing order.

        Args:
            broker_order_id: Broker-assigned order ID.
            quantity: New quantity (if changing).
            price: New price (if changing).
            stop_price: New stop price (if changing).
            stop_loss: New stop loss (if applicable).
            take_profit: New take profit (if applicable).

        Returns:
            OrderExecutionInfo with updated status.

        Raises:
            AdapterOrderRejectedError: If broker rejects modification.
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel an order with the broker.

        Args:
            broker_order_id: Broker-assigned order ID.

        Returns:
            True if cancellation was successful.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        """Close an open position.

        Args:
            position_id: Broker position ID.

        Returns:
            OrderExecutionInfo with close details.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    # ── Position & Account Queries ────────────────────────────────────

    @abstractmethod
    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all open positions.

        Returns:
            List of open positions.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get account information.

        Returns:
            AccountInfo with balance, equity, margin, etc.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        """Get symbol/trading instrument information.

        Args:
            symbol: Trading symbol to query.

        Returns:
            ExecutionSymbolInfo with contract specifications.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    @abstractmethod
    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        """Get execution history from the broker.

        Args:
            symbol: Filter by symbol (optional).
            since: Filter by start time (optional).
            limit: Maximum number of records.

        Returns:
            List of historical order executions.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        ...

    # ── Utility Methods ───────────────────────────────────────────────

    def _validate_connected(self) -> None:
        """Validate that the adapter is connected.

        Raises:
            AdapterNotConnectedError: If not connected.
        """
        if not self._connected:
            raise AdapterNotConnectedError(
                f"Broker '{self._config.broker_name}' is not connected",
                broker_name=self._config.broker_name,
            )

