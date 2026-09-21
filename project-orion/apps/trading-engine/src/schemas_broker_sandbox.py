"""Request and response DTO schemas for Broker Sandbox & Demo Broker Integration (EPIC-026)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrokerSandboxAccountCreateRequest(BaseModel):
    """Request DTO to register a new tenant broker sandbox connection."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=128, description="Display name for this sandbox account")
    provider: str = Field(..., description="Sandbox provider: MOCK or OANDA_PRACTICE")
    environment: str = Field(default="SANDBOX", description="Must be SANDBOX or LOCAL. LIVE is strictly prohibited.")
    account_id_external: str = Field(..., min_length=1, max_length=64, description="External broker account identifier")
    credentials: dict[str, Any] = Field(default_factory=dict, description="Provider credentials (e.g. api_key/token)")
    config: dict[str, Any] = Field(default_factory=dict, description="Additional provider parameters (e.g. leverage, seed)")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm == "LIVE":
            raise ValueError(
                "LIVE environment is strictly prohibited in Project ORION ($0.00 Capital at Risk)."
            )
        if norm not in ("SANDBOX", "LOCAL"):
            raise ValueError(f"Invalid environment '{v}'. Only SANDBOX or LOCAL are permitted.")
        return norm

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in ("MOCK", "OANDA_PRACTICE", "OANDA"):
            raise ValueError(
                f"Unsupported broker sandbox provider '{v}'. Permitted: MOCK, OANDA_PRACTICE."
            )
        return norm


class BrokerSandboxAccountUpdateRequest(BaseModel):
    """Request DTO to update an existing broker sandbox account configuration."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=128)
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class BrokerSandboxAccountResponse(BaseModel):
    """Response DTO presenting a broker sandbox account with masked credentials."""

    model_config = ConfigDict(frozen=True)

    id: str
    organization_id: str
    name: str
    provider: str
    environment: str
    account_id_external: str
    status: str
    last_connected_at: datetime | None = None
    last_reconciled_at: datetime | None = None
    credentials_masked: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class BrokerSandboxConnectResponse(BaseModel):
    """Response DTO for connecting or testing a broker sandbox session."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    status: str
    connected: bool
    latency_ms: float = 0.0
    balance: Decimal | None = None
    equity: Decimal | None = None
    margin: Decimal | None = None
    margin_free: Decimal | None = None
    currency: str = "USD"
    message: str = ""


class BrokerSandboxOrderRequest(BaseModel):
    """Request DTO to submit a manual or automated order to a sandbox broker."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    symbol: str = Field(..., min_length=3, max_length=16, description="Trading instrument, e.g. EUR/USD or EUR_USD")
    side: str = Field(..., description="BUY or SELL")
    order_type: str = Field(default="MARKET", description="MARKET, LIMIT, or STOP")
    quantity: Decimal = Field(..., gt=Decimal("0"), description="Order units / quantity")
    price: Decimal | None = Field(default=None, gt=Decimal("0"), description="Target price for limit/stop orders")
    stop_loss: Decimal | None = Field(default=None, gt=Decimal("0"), description="Optional stop loss price")
    take_profit: Decimal | None = Field(default=None, gt=Decimal("0"), description="Optional take profit price")
    client_order_id: str | None = Field(default=None, description="Optional client idempotency reference")

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in ("BUY", "SELL"):
            raise ValueError(f"Invalid side '{v}'. Must be BUY or SELL.")
        return norm

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in ("MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TRAILING_STOP"):
            raise ValueError(f"Invalid order_type '{v}'. Must be MARKET, LIMIT, or STOP.")
        return norm


class BrokerSandboxOrderResponse(BaseModel):
    """Response DTO for an order executed or rejected on a sandbox broker."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    broker_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    status: str
    filled_quantity: Decimal
    average_fill_price: Decimal | None = None
    latency_ms: float = 0.0
    timestamp: datetime
    rejection_reason: str | None = None


class BrokerSandboxPositionResponse(BaseModel):
    """Response DTO for an open position reported by a sandbox broker."""

    model_config = ConfigDict(frozen=True)

    position_id: str
    symbol: str
    side: str
    quantity: Decimal
    open_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    currency: str = "USD"


class BrokerSandboxReconciliationResponse(BaseModel):
    """Response DTO presenting the audit snapshot of a broker reconciliation sweep."""

    model_config = ConfigDict(frozen=True)

    id: str
    broker_account_id: str
    organization_id: str
    status: str
    has_discrepancies: bool
    order_discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    position_discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    account_discrepancies: list[dict[str, Any]] = Field(default_factory=list)
    balance_delta: Decimal = Decimal("0.0000")
    equity_delta: Decimal = Decimal("0.0000")
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class BrokerProviderInfo(BaseModel):
    """Metadata DTO describing an approved broker sandbox provider."""

    model_config = ConfigDict(frozen=True)

    provider: str
    name: str
    environment: str
    description: str
    status: str
    supported_order_types: list[str]
    supported_symbols: list[str]
    requires_credentials: bool
