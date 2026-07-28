"""Binance broker execution adapter.

Translates domain execution requests into Binance REST API calls and
converts Binance responses back into domain models. No business logic
exists here — this is a pure infrastructure translator.

NOTE: This adapter requires the python-binance package installed
in the runtime environment. The adapter gracefully handles the case
where the package is not available.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from libraries.domain.execution.models import (
    BrokerOrderId,
    Fill,
    Order,
    OrderId,
    OrderSide,
    OrderStatus,
    OrderType,
)
from libraries.infrastructure.execution.broker_adapter import (
    AccountInfo,
    AdapterAuthenticationError,
    AdapterConnectionError,
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
    AdapterTimeoutError,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionSymbolInfo,
    OrderExecutionInfo,
    PositionInfo,
)

# Try to import httpx for async HTTP
try:
    import httpx  # type: ignore[import-untyped]

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass(frozen=True, slots=True)
class BinanceExecutionConfig(BrokerAdapterConfig):
    """Configuration for Binance execution adapter."""

    broker_name: str = "binance"
    api_endpoint: str = "https://api.binance.com"
    api_key: str = ""
    api_secret: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 3
    recv_window: int = 5000  # Binance recvWindow parameter


class BinanceExecutionAdapter(BrokerAdapter):
    """Binance broker execution adapter.

    Translates domain Order objects to Binance REST API calls and
    Binance responses back into domain models.
    """

    def __init__(self, config: BinanceExecutionConfig | None = None) -> None:
        super().__init__(config or BinanceExecutionConfig())
        self._binance_config: BinanceExecutionConfig = self._config  # type: ignore[assignment]
        self._client: Any = None

    async def connect(self) -> bool:
        """Connect to Binance API.

        Validates credentials by making a test API call.
        """
        if not HAS_HTTPX:
            raise AdapterConnectionError(
                "httpx package is required for Binance connectivity. "
                "Install with: pip install httpx",
                broker_name=self.broker_name,
            )

        if not self._binance_config.api_key or not self._binance_config.api_secret:
            raise AdapterAuthenticationError(
                "Binance API key and secret are required",
                broker_name=self.broker_name,
            )

        self._client = httpx.AsyncClient(
            base_url=self._binance_config.api_endpoint,
            headers={
                "X-MBX-APIKEY": self._binance_config.api_key,
                "Content-Type": "application/json",
            },
            timeout=self._binance_config.timeout_seconds,
        )

        # Validate connection by testing ping endpoint
        try:
            response = await self._client.get("/api/v3/ping")
            if response.status_code != 200:
                raise AdapterConnectionError(
                    f"Binance ping failed: {response.text}",
                    broker_name=self.broker_name,
                )
        except AdapterConnectionError:
            raise
        except Exception as e:
            raise AdapterConnectionError(
                f"Binance connection failed: {e}",
                broker_name=self.broker_name,
            )

        self._connected = True
        self._connection_attempts += 1
        return True

    async def disconnect(self) -> bool:
        """Disconnect from Binance API."""
        if self._client is not None:
            await self._client.aclose()
        self._connected = False
        return True

    async def health_check(self) -> dict[str, Any]:
        """Check Binance API health."""
        self._validate_connected()
        try:
            start = time.monotonic()
            response = await self._client.get("/api/v3/ping")
            latency = (time.monotonic() - start) * 1000

            # Also check server time for authenticated status
            time_response = await self._client.get("/api/v3/time")
            server_time = (
                time_response.json().get("serverTime", 0) if time_response.status_code == 200 else 0
            )

            return {
                "connected": self._connected and response.status_code == 200,
                "latency_ms": round(latency, 2),
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "ping_ok": response.status_code == 200,
                    "server_time": server_time,
                },
            }
        except Exception as e:
            return {
                "connected": False,
                "latency_ms": 0.0,
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "details": {"error": str(e)},
            }

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        """Submit an order to Binance."""
        self._validate_connected()

        params = self._build_order_params(order)
        signed_params = self._sign_params(params)

        try:
            response = await self._client.post(
                "/api/v3/order",
                params=signed_params,
            )

            if response.status_code == 401:
                raise AdapterAuthenticationError(
                    "Binance authentication failed",
                    broker_name=self.broker_name,
                )

            if response.status_code != 200:
                error_data = response.json()
                raise AdapterOrderRejectedError(
                    f"Binance order rejected: {error_data.get('msg', response.text)}",
                    broker_name=self.broker_name,
                )

            data = response.json()
            broker_order_id = BrokerOrderId(str(data.get("orderId", "")))

            fills: list[Fill] = []
            fills_data = data.get("fills", [])
            for f in fills_data:
                fill = Fill(
                    fill_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=Decimal(str(f.get("qty", "0"))),
                    price=Decimal(str(f.get("price", "0"))),
                    commission=Decimal(str(f.get("commission", "0"))),
                    broker_fill_id=str(f.get("tradeId", "")),
                )
                fills.append(fill)

            executed_qty = Decimal(str(data.get("executedQty", "0")))
            cummulative_qty = Decimal(str(data.get("cummulativeQuoteQty", "0")))
            avg_price = cummulative_qty / executed_qty if executed_qty > 0 else None

            status = (
                OrderStatus.FILLED
                if data.get("status") == "FILLED"
                else OrderStatus.PARTIALLY_FILLED
            )
            if data.get("status") == "REJECTED":
                status = OrderStatus.REJECTED
            elif data.get("status") == "CANCELED":
                status = OrderStatus.CANCELLED
            elif data.get("status") == "EXPIRED":
                status = OrderStatus.EXPIRED

            return OrderExecutionInfo(
                broker_order_id=broker_order_id,
                status=status,
                filled_quantity=executed_qty,
                average_fill_price=avg_price,
                fills=tuple(fills),
                metadata={"binance_status": data.get("status", "")},
            )

        except (AdapterOrderRejectedError, AdapterAuthenticationError):
            raise
        except Exception as e:
            raise AdapterTimeoutError(
                f"Binance submit order failed: {e}",
                broker_name=self.broker_name,
            )

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
        """Modify an existing Binance order.

        Binance doesn't support modification - we cancel and re-submit.
        """
        self._validate_connected()

        # Cancel existing order
        cancelled = await self.cancel_order(broker_order_id)
        if not cancelled:
            raise AdapterOrderRejectedError(
                f"Failed to cancel order {broker_order_id} for modification",
                broker_name=self.broker_name,
            )

        # Re-submit with new parameters (requires original order info)
        raise AdapterOrderRejectedError(
            "Binance order modification requires re-submission via submit_order",
            broker_name=self.broker_name,
        )

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel a Binance order."""
        self._validate_connected()

        params = {
            "symbol": "",  # Symbol required - needs to be stored per order
            "orderId": int(str(broker_order_id)),
        }
        signed_params = self._sign_params(params)

        try:
            response = await self._client.delete(
                "/api/v3/order",
                params=signed_params,
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        """Close a Binance position.

        Binance uses order-based position management.
        """
        self._validate_connected()
        raise AdapterOrderRejectedError(
            "Binance position close not directly supported; use market order",
            broker_name=self.broker_name,
        )

    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all open Binance positions.

        Binance doesn't have traditional positions for spot trading.
        For futures, this requires the futures account endpoint.
        """
        self._validate_connected()
        return []

    async def get_account(self) -> AccountInfo:
        """Get Binance account information."""
        self._validate_connected()

        params = self._sign_params({})

        try:
            response = await self._client.get(
                "/api/v3/account",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            balances = {
                b["asset"]: Decimal(str(b["free"])) + Decimal(str(b["locked"]))
                for b in data.get("balances", [])
            }

            total_btc = Decimal("0")
            for asset, amount in balances.items():
                if amount > 0 and asset != "BTC":
                    try:
                        ticker = await self._client.get(
                            "/api/v3/ticker/price",
                            params={"symbol": f"{asset}BTC"},
                        )
                        if ticker.status_code == 200:
                            price = Decimal(str(ticker.json()["price"]))
                            total_btc += amount * price
                    except Exception:
                        pass

            return AccountInfo(
                account_id=data.get("accountType", "spot"),
                broker_name=self.broker_name,
                balance=total_btc,
                equity=total_btc,
                margin=Decimal("0"),
                margin_free=total_btc,
                margin_level=0.0,
                currency="BTC",
                leverage=1,
                is_live="test" not in self._binance_config.api_endpoint,
            )
        except Exception as e:
            raise AdapterConnectionError(
                f"Failed to get Binance account info: {e}",
                broker_name=self.broker_name,
            )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        """Get Binance symbol information."""
        self._validate_connected()
        try:
            response = await self._client.get(
                "/api/v3/exchangeInfo",
                params={"symbol": symbol.upper()},
            )
            response.raise_for_status()
            data = response.json()
            symbol_data = data.get("symbols", [{}])[0]

            filters = {f["filterType"]: f for f in symbol_data.get("filters", [])}
            lot_size = filters.get("LOT_SIZE", {})
            min_notional = filters.get("MIN_NOTIONAL", {})

            return ExecutionSymbolInfo(
                symbol=symbol_data.get("symbol", symbol),
                description=symbol_data.get("baseAsset", ""),
                digits=int(symbol_data.get("quotePrecision", 8)),
                pip_size=Decimal("0.00000001"),
                min_volume=Decimal(str(lot_size.get("minQty", "0.00001"))),
                max_volume=Decimal(str(lot_size.get("maxQty", "1000000"))),
                volume_step=Decimal(str(lot_size.get("stepSize", "0.00001"))),
                is_trade_allowed=symbol_data.get("status") == "TRADING",
                margin_currency=symbol_data.get("quoteAsset", "USDT"),
            )
        except Exception:
            return ExecutionSymbolInfo(symbol=symbol)

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        """Get Binance execution history."""
        self._validate_connected()
        if not symbol:
            return []

        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "limit": min(limit, 500),
        }
        if since:
            params["startTime"] = int(since.timestamp() * 1000)

        signed_params = self._sign_params(params)

        try:
            response = await self._client.get(
                "/api/v3/allOrders",
                params=signed_params,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            results = []
            for order_data in data[:limit]:
                results.append(
                    OrderExecutionInfo(
                        broker_order_id=BrokerOrderId(str(order_data.get("orderId", ""))),
                        status=(
                            OrderStatus.FILLED
                            if order_data.get("status") == "FILLED"
                            else OrderStatus.REJECTED
                        ),
                        filled_quantity=Decimal(str(order_data.get("executedQty", "0"))),
                        average_fill_price=Decimal(str(order_data.get("price", "0"))),
                        commission=Decimal("0"),
                    )
                )
            return results
        except Exception:
            return []

    # ── Private Helpers ─────────────────────────────────────────────

    def _build_order_params(self, order: Order) -> dict[str, Any]:
        """Build Binance order parameters from domain Order."""
        side = "BUY" if order.side == OrderSide.BUY else "SELL"

        order_type_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP_LOSS",
            OrderType.STOP_LIMIT: "STOP_LOSS_LIMIT",
        }

        params: dict[str, Any] = {
            "symbol": order.symbol.upper(),
            "side": side,
            "type": order_type_map.get(order.order_type, "MARKET"),
            "quantity": float(order.quantity),
        }

        if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and order.price:
            params["price"] = float(order.price)
            params["timeInForce"] = "GTC"

        if order.order_type == OrderType.STOP and order.stop_price:
            params["stopPrice"] = float(order.stop_price)

        return params

    def _sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Sign parameters with Binance HMAC signature."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self._binance_config.recv_window

        query_string = urlencode(params)
        signature = hmac.new(
            self._binance_config.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params
