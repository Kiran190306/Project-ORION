"""OANDA broker execution adapter.

Translates domain execution requests into OANDA REST API calls and
converts OANDA responses back into domain models. No business logic
exists here — this is a pure infrastructure translator.

NOTE: This adapter requires the v20 Python package or direct REST calls.
The adapter gracefully handles the case where the package is not available.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

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

# Try to import httpx or aiohttp for async HTTP
try:
    import httpx  # type: ignore[import-untyped]

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


@dataclass(frozen=True, slots=True)
class OANDAExecutionConfig(BrokerAdapterConfig):
    """Configuration for OANDA execution adapter."""

    broker_name: str = "oanda"
    api_endpoint: str = "https://api-fxpractice.oanda.com"
    account_id: str = ""
    api_key: str = ""
    api_secret: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 3


class OANDAExecutionAdapter(BrokerAdapter):
    """OANDA broker execution adapter.

    Translates domain Order objects to OANDA REST API calls and
    OANDA responses back into domain models.
    """

    def __init__(self, config: OANDAExecutionConfig | None = None) -> None:
        super().__init__(config or OANDAExecutionConfig())
        self._oanda_config: OANDAExecutionConfig = self._config  # type: ignore[assignment]
        self._client: Any = None

    async def connect(self) -> bool:
        """Connect to OANDA API.

        Validates credentials by making a test API call.
        """
        if not HAS_HTTPX:
            raise AdapterConnectionError(
                "httpx package is required for OANDA connectivity. "
                "Install with: pip install httpx",
                broker_name=self.broker_name,
            )

        if not self._oanda_config.api_key:
            raise AdapterAuthenticationError(
                "OANDA API key is required",
                broker_name=self.broker_name,
            )

        self._client = httpx.AsyncClient(
            base_url=self._oanda_config.api_endpoint,
            headers={
                "Authorization": f"Bearer {self._oanda_config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self._oanda_config.timeout_seconds,
        )

        # Validate connection by fetching account info
        try:
            response = await self._client.get(f"/v3/accounts/{self._oanda_config.account_id}")
            if response.status_code == 401:
                raise AdapterAuthenticationError(
                    "OANDA authentication failed: invalid API key",
                    broker_name=self.broker_name,
                )
            if response.status_code == 404:
                raise AdapterAuthenticationError(
                    f"OANDA account {self._oanda_config.account_id} not found",
                    broker_name=self.broker_name,
                )
            response.raise_for_status()
        except AdapterAuthenticationError:
            raise
        except Exception as e:
            raise AdapterConnectionError(
                f"OANDA connection failed: {e}",
                broker_name=self.broker_name,
            )

        self._connected = True
        self._connection_attempts += 1
        return True

    async def disconnect(self) -> bool:
        """Disconnect from OANDA API."""
        if self._client is not None:
            await self._client.aclose()
        self._connected = False
        return True

    async def health_check(self) -> dict[str, Any]:
        """Check OANDA API health."""
        self._validate_connected()
        try:
            response = await self._client.get(
                f"/v3/accounts/{self._oanda_config.account_id}/summary"
            )
            return {
                "connected": self._connected and response.status_code == 200,
                "latency_ms": (
                    response.elapsed.total_seconds() * 1000 if hasattr(response, "elapsed") else 0.0
                ),
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "details": {
                    "status_code": response.status_code,
                    "account_id": self._oanda_config.account_id,
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
        """Submit an order to OANDA."""
        self._validate_connected()
        oanda_order = self._build_order_request(order)

        try:
            response = await self._client.post(
                f"/v3/accounts/{self._oanda_config.account_id}/orders",
                json=oanda_order,
            )

            if response.status_code == 401:
                raise AdapterAuthenticationError(
                    "OANDA authentication failed",
                    broker_name=self.broker_name,
                )

            if response.status_code != 201:
                error_body = response.text
                try:
                    error_data = response.json()
                    error_body = json.dumps(error_data.get("errorMessage", error_data))
                except Exception:
                    pass
                raise AdapterOrderRejectedError(
                    f"OANDA order rejected: {error_body}",
                    broker_name=self.broker_name,
                )

            data = response.json()
            order_create = data.get("orderCreateTransaction", {})
            order_fill = data.get("orderFillTransaction", data.get("orderCancelTransaction", {}))

            broker_order_id = BrokerOrderId(
                str(order_create.get("id", order_create.get("orderID", "")))
            )

            fills: list[Fill] = []
            fills_data = order_fill.get("tradesClosed", [])
            for trade in fills_data:
                fill = Fill(
                    fill_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=Decimal(str(trade.get("units", "0"))),
                    price=Decimal(str(trade.get("price", "0"))),
                    commission=Decimal("0"),
                    broker_fill_id=str(trade.get("tradeID", "")),
                )
                fills.append(fill)

            filled_qty = Decimal(str(order_fill.get("units", "0")))
            if filled_qty < 0:
                filled_qty = abs(filled_qty)

            status = (
                OrderStatus.FILLED if filled_qty >= order.quantity else OrderStatus.PARTIALLY_FILLED
            )

            return OrderExecutionInfo(
                broker_order_id=broker_order_id,
                status=status,
                filled_quantity=filled_qty,
                average_fill_price=(
                    Decimal(str(order_fill.get("price", "0"))) if order_fill.get("price") else None
                ),
                fills=tuple(fills),
            )

        except AdapterOrderRejectedError:
            raise
        except AdapterAuthenticationError:
            raise
        except Exception as e:
            raise AdapterTimeoutError(
                f"OANDA submit order failed: {e}",
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
        """Modify an existing OANDA order."""
        self._validate_connected()
        try:
            patch_data: dict[str, Any] = {}
            if quantity is not None:
                patch_data["units"] = str(quantity)
            if price is not None:
                patch_data["price"] = str(price)
            if stop_loss is not None:
                patch_data["stopLossOnFill"] = {"price": str(stop_loss)}
            if take_profit is not None:
                patch_data["takeProfitOnFill"] = {"price": str(take_profit)}

            response = await self._client.patch(
                f"/v3/accounts/{self._oanda_config.account_id}/orders/{str(broker_order_id)}",
                json={"order": patch_data},
            )

            if response.status_code != 200:
                raise AdapterOrderRejectedError(
                    f"OANDA modify order failed: {response.text}",
                    broker_name=self.broker_name,
                )

            return OrderExecutionInfo(
                broker_order_id=broker_order_id,
                status=OrderStatus.SUBMITTED,
            )

        except AdapterOrderRejectedError:
            raise
        except Exception as e:
            raise AdapterTimeoutError(
                f"OANDA modify order failed: {e}",
                broker_name=self.broker_name,
            )

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel an OANDA order."""
        self._validate_connected()
        try:
            response = await self._client.delete(
                f"/v3/accounts/{self._oanda_config.account_id}/orders/{str(broker_order_id)}"
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        """Close an OANDA position."""
        self._validate_connected()
        try:
            # Parse symbol from position_id (format: "symbol|side")
            parts = position_id.split("|")
            symbol = parts[0] if len(parts) > 1 else position_id

            response = await self._client.put(
                f"/v3/accounts/{self._oanda_config.account_id}/positions/{symbol}/close",
                json={"longUnits": "ALL", "shortUnits": "ALL"},
            )

            if response.status_code != 200:
                raise AdapterOrderRejectedError(
                    f"OANDA close position failed: {response.text}",
                    broker_name=self.broker_name,
                )

            data = response.json()
            fill = Fill(
                fill_id=str(uuid.uuid4()),
                order_id=OrderId(f"close_{position_id}"),
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=Decimal("0"),
                price=Decimal("0"),
                timestamp=datetime.now(timezone.utc),
            )

            return OrderExecutionInfo(
                broker_order_id=BrokerOrderId(f"close_{position_id}"),
                status=OrderStatus.FILLED,
                fills=(fill,),
            )

        except AdapterOrderRejectedError:
            raise
        except Exception as e:
            raise AdapterTimeoutError(
                f"OANDA close position failed: {e}",
                broker_name=self.broker_name,
            )

    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all open OANDA positions."""
        self._validate_connected()
        try:
            response = await self._client.get(
                f"/v3/accounts/{self._oanda_config.account_id}/openPositions"
            )
            if response.status_code != 200:
                return []

            data = response.json()
            positions = []
            for pos in data.get("positions", []):
                symbol = pos.get("instrument", "")
                long = pos.get("long", {})
                short = pos.get("short", {})

                if long and long.get("units", "0") != "0":
                    positions.append(
                        PositionInfo(
                            position_id=f"{symbol}|long",
                            symbol=symbol,
                            side=OrderSide.BUY,
                            quantity=Decimal(str(long["units"])),
                            open_price=Decimal(str(long.get("averagePrice", "0"))),
                            current_price=Decimal(str(long.get("currentPrice", "0"))),
                            profit=Decimal(str(long.get("unrealizedPL", "0"))),
                        )
                    )
                if short and short.get("units", "0") != "0":
                    positions.append(
                        PositionInfo(
                            position_id=f"{symbol}|short",
                            symbol=symbol,
                            side=OrderSide.SELL,
                            quantity=Decimal(str(short["units"])),
                            open_price=Decimal(str(short.get("averagePrice", "0"))),
                            current_price=Decimal(str(short.get("currentPrice", "0"))),
                            profit=Decimal(str(short.get("unrealizedPL", "0"))),
                        )
                    )

            return positions
        except Exception:
            return []

    async def get_account(self) -> AccountInfo:
        """Get OANDA account information."""
        self._validate_connected()
        try:
            response = await self._client.get(
                f"/v3/accounts/{self._oanda_config.account_id}/summary"
            )
            response.raise_for_status()
            data = response.json()
            account = data.get("account", {})

            return AccountInfo(
                account_id=account.get("id", self._oanda_config.account_id),
                broker_name=self.broker_name,
                balance=Decimal(str(account.get("balance", "0"))),
                equity=Decimal(str(account.get("NAV", "0"))),
                margin=Decimal(str(account.get("marginUsed", "0"))),
                margin_free=Decimal(str(account.get("marginAvailable", "0"))),
                margin_level=float(account.get("marginRate", "0")) * 100,
                currency=account.get("currency", "USD"),
                leverage=int(account.get("leverage", "0")),
                is_live="practice" not in self._oanda_config.api_endpoint,
            )
        except Exception as e:
            raise AdapterConnectionError(
                f"Failed to get OANDA account info: {e}",
                broker_name=self.broker_name,
            )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        """Get OANDA symbol information."""
        self._validate_connected()
        try:
            response = await self._client.get(
                f"/v3/accounts/{self._oanda_config.account_id}/instruments/{symbol}"
            )
            response.raise_for_status()
            data = response.json()
            instrument = data.get("instrument", {})

            return ExecutionSymbolInfo(
                symbol=instrument.get("name", symbol),
                description=instrument.get("displayName", ""),
                digits=int(instrument.get("displayPrecision", 5)),
                pip_size=Decimal(str(10 ** -int(instrument.get("displayPrecision", 5)))),
                min_volume=Decimal(str(instrument.get("minimumTradeSize", "0.01"))),
                max_volume=Decimal(str(instrument.get("maximumTradeSize", "100"))),
                volume_step=Decimal(str(instrument.get("tradeQuantityIncrement", "0.01"))),
                spread=float(instrument.get("spread", "0")),
                margin_rate=float(instrument.get("marginRate", "0")),
            )
        except Exception:
            return ExecutionSymbolInfo(symbol=symbol)

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        """Get OANDA execution history."""
        self._validate_connected()
        try:
            params: dict[str, Any] = {
                "count": min(limit, 500),
                "type": "ORDER_FILL",
            }
            if since:
                params["from"] = since.isoformat()

            response = await self._client.get(
                f"/v3/accounts/{self._oanda_config.account_id}/transactions",
                params=params,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            results = []
            for txn in data.get("transactions", [])[:limit]:
                if symbol and txn.get("instrument") != symbol:
                    continue
                results.append(
                    OrderExecutionInfo(
                        broker_order_id=BrokerOrderId(str(txn.get("id", ""))),
                        status=OrderStatus.FILLED,
                        filled_quantity=Decimal(str(txn.get("units", "0"))),
                        average_fill_price=Decimal(str(txn.get("price", "0"))),
                        commission=Decimal("0"),
                    )
                )
            return results
        except Exception:
            return []

    # ── Private Helpers ─────────────────────────────────────────────

    def _build_order_request(self, order: Order) -> dict[str, Any]:
        """Build OANDA order request from domain Order."""
        units = int(order.quantity)
        if order.side == OrderSide.SELL:
            units = -units

        order_data: dict[str, Any] = {
            "order": {
                "type": "MARKET",
                "instrument": order.symbol,
                "units": str(units),
            }
        }

        if order.order_type == OrderType.LIMIT and order.price:
            order_data["order"]["type"] = "LIMIT"
            order_data["order"]["price"] = str(order.price)

        if order.order_type == OrderType.STOP and order.stop_price:
            order_data["order"]["type"] = "STOP"
            order_data["order"]["price"] = str(order.stop_price)

        return order_data
