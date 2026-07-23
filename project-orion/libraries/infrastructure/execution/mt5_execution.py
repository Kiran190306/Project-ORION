"""MT5 broker execution adapter.

Translates domain execution requests into MT5-specific API calls and
converts MT5 responses back into domain models. No business logic exists
here — this is a pure infrastructure translator.

NOTE: This adapter requires the MetaTrader5 Python package installed
in the runtime environment. The adapter gracefully handles the case
where the package is not available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

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


@dataclass(frozen=True, slots=True)
class MT5ExecutionConfig(BrokerAdapterConfig):
    """Configuration for MT5 execution adapter."""

    broker_name: str = "mt5"
    mt5_server: str = ""
    mt5_path: str = ""
    timeout_seconds: float = 30.0


class MT5ExecutionAdapter(BrokerAdapter):
    """MT5 broker execution adapter.

    Translates domain Order objects to MT5 trade requests and MT5
    responses back into domain models. Requires MetaTrader5 package.
    """

    def __init__(self, config: MT5ExecutionConfig | None = None) -> None:
        super().__init__(config or MT5ExecutionConfig())
        self._mt5_config: MT5ExecutionConfig = self._config  # type: ignore[assignment]
        self._mt5: Any = None  # mt5 module reference
        self._mt5_available: bool = False
        self._login: int = 0

    async def connect(self) -> bool:
        """Connect to MT5 terminal.

        Attempts to import and initialize the MetaTrader5 module.
        """
        try:
            import MetaTrader5 as mt5  # type: ignore[import-untyped]

            self._mt5 = mt5
            self._mt5_available = True
        except ImportError:
            raise AdapterConnectionError(
                "MetaTrader5 package is not installed. "
                "Install with: pip install MetaTrader5",
                broker_name=self.broker_name,
            )

        # Initialize MT5 terminal
        initialized = self._mt5.initialize(
            path=self._mt5_config.mt5_path or None,
        )
        if not initialized:
            error = self._mt5.last_error() if hasattr(self._mt5, "last_error") else "Unknown"
            raise AdapterConnectionError(
                f"Failed to initialize MT5: {error}",
                broker_name=self.broker_name,
            )

        # Login if credentials provided
        if self._mt5_config.api_key:
            authorized = self._mt5.login(
                login=int(self._mt5_config.api_key),
                password=self._mt5_config.api_secret,
                server=self._mt5_config.mt5_server or None,
            )
            if not authorized:
                error = self._mt5.last_error() if hasattr(self._mt5, "last_error") else "Unknown"
                raise AdapterAuthenticationError(
                    f"MT5 login failed: {error}",
                    broker_name=self.broker_name,
                )

        self._connected = True
        self._connection_attempts += 1
        return True

    async def disconnect(self) -> bool:
        """Disconnect from MT5 terminal."""
        if self._mt5_available and self._mt5 is not None:
            self._mt5.shutdown()
        self._connected = False
        return True

    async def health_check(self) -> dict[str, Any]:
        """Check MT5 connection health."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        terminal_info = self._mt5.terminal_info()
        account_info = self._mt5.account_info()

        return {
            "connected": self._connected,
            "latency_ms": 0.0,  # MT5 doesn't provide latency directly
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "details": {
                "mt5_connected": terminal_info.connected if terminal_info else False,
                "mt5_trade_allowed": terminal_info.trade_allowed if terminal_info else False,
                "account_balance": str(account_info.balance) if account_info else "N/A",
                "account_equity": str(account_info.equity) if account_info else "N/A",
            },
        }

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        """Submit an order to MT5."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        trade_request = self._build_trade_request(order)
        result = self._mt5.order_send(trade_request)

        if result is None:
            raise AdapterTimeoutError(
                "MT5 order_send returned None",
                broker_name=self.broker_name,
            )

        if result.retcode != 10009:  # TRADE_RETCODE_DONE
            raise AdapterOrderRejectedError(
                f"MT5 order rejected: {result.comment} (retcode={result.retcode})",
                broker_name=self.broker_name,
            )

        broker_order_id = BrokerOrderId(str(result.order))
        fill_price = Decimal(str(result.price)) if result.price else None

        fills: list[Fill] = []
        if result.price and result.volume:
            fill = Fill(
                fill_id=f"mt5_fill_{result.order}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=Decimal(str(result.volume)),
                price=Decimal(str(result.price)),
                broker_fill_id=str(result.order),
                timestamp=datetime.now(timezone.utc),
            )
            fills.append(fill)

        return OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=OrderStatus.FILLED,
            filled_quantity=Decimal(str(result.volume)) if result.volume else Decimal("0"),
            average_fill_price=fill_price,
            fills=tuple(fills),
            metadata={"mt5_retcode": result.retcode, "mt5_comment": result.comment},
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
        """Modify an existing MT5 order."""
        self._validate_connected()
        raise AdapterOrderRejectedError(
            "MT5 order modification not yet implemented",
            broker_name=self.broker_name,
        )

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel an MT5 order."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        result = self._mt5.order_delete(int(str(broker_order_id)))
        return bool(result)

    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        """Close an MT5 position."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        position = self._mt5.positions_get(ticket=int(position_id))
        if not position:
            raise AdapterOrderRejectedError(
                f"Position {position_id} not found",
                broker_name=self.broker_name,
            )

        pos = position[0]
        trade_request = self._build_close_request(pos)
        result = self._mt5.order_send(trade_request)

        if result is None or result.retcode != 10009:
            raise AdapterOrderRejectedError(
                f"Failed to close position {position_id}: {result.comment if result else 'Unknown'}",
                broker_name=self.broker_name,
            )

        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId(str(result.order)),
            status=OrderStatus.FILLED,
            filled_quantity=Decimal(str(pos.volume)),
            average_fill_price=Decimal(str(result.price)) if result.price else None,
        )

    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all open MT5 positions."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        positions = self._mt5.positions_get()
        if positions is None:
            return []

        return [
            PositionInfo(
                position_id=str(pos.ticket),
                symbol=pos.symbol,
                side=OrderSide.BUY if pos.type == 0 else OrderSide.SELL,
                quantity=Decimal(str(pos.volume)),
                open_price=Decimal(str(pos.price_open)),
                current_price=Decimal(str(pos.price_current)),
                stop_loss=Decimal(str(pos.sl)) if pos.sl else None,
                take_profit=Decimal(str(pos.tp)) if pos.tp else None,
                commission=Decimal(str(pos.commission)),
                swap=Decimal(str(pos.swap)),
                profit=Decimal(str(pos.profit)),
                open_time=datetime.fromtimestamp(pos.time, tz=timezone.utc),
            )
            for pos in positions
        ]

    async def get_account(self) -> AccountInfo:
        """Get MT5 account information."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        info = self._mt5.account_info()
        if info is None:
            raise AdapterConnectionError(
                "Failed to get MT5 account info",
                broker_name=self.broker_name,
            )

        return AccountInfo(
            account_id=str(info.login),
            broker_name=self.broker_name,
            balance=Decimal(str(info.balance)),
            equity=Decimal(str(info.equity)),
            margin=Decimal(str(info.margin)),
            margin_free=Decimal(str(info.margin_free)),
            margin_level=float(info.margin_level),
            currency=info.currency,
            leverage=int(info.leverage),
            is_live=info.trade_mode == 0,  # TRADE_MODE_DEMO or REAL
        )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        """Get MT5 symbol information."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        info = self._mt5.symbol_info(symbol)
        if info is None:
            raise AdapterOrderRejectedError(
                f"Symbol {symbol} not found in MT5",
                broker_name=self.broker_name,
            )

        return ExecutionSymbolInfo(
            symbol=info.name,
            description=info.description or "",
            digits=info.digits,
            pip_size=Decimal(str(info.point)) if info.point else Decimal("0.00001"),
            min_volume=Decimal(str(info.volume_min)) if info.volume_min else Decimal("0.01"),
            max_volume=Decimal(str(info.volume_max)) if info.volume_max else Decimal("100"),
            volume_step=Decimal(str(info.volume_step)) if info.volume_step else Decimal("0.01"),
            spread=float(info.spread),
            swap_long=float(info.swap_long),
            swap_short=float(info.swap_short),
            is_trade_allowed=bool(info.trade_mode > 0),
        )

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        """Get MT5 execution history."""
        self._validate_connected()
        if not self._mt5_available or self._mt5 is None:
            raise AdapterNotConnectedError(
                "MT5 not available",
                broker_name=self.broker_name,
            )

        from_date = since or datetime.now(timezone.utc) - timedelta(days=30)
        to_date = datetime.now(timezone.utc)
        orders = self._mt5.history_deals_get(
            from_date,
            to_date,
            group=symbol or None,
        )

        if orders is None:
            return []

        results = []
        for deal in orders[:limit]:
            results.append(OrderExecutionInfo(
                broker_order_id=BrokerOrderId(str(deal.order)),
                status=OrderStatus.FILLED,
                filled_quantity=Decimal(str(deal.volume)),
                average_fill_price=Decimal(str(deal.price)),
                commission=Decimal(str(deal.commission)) if hasattr(deal, "commission") else Decimal("0"),
                timestamp=datetime.fromtimestamp(deal.time, tz=timezone.utc),
            ))

        return results

    # ── Private Helpers ─────────────────────────────────────────────

    def _build_trade_request(self, order: Order) -> dict[str, Any]:
        """Build MT5 trade request from domain Order."""
        trade_type = 0 if order.side == OrderSide.BUY else 1  # OP_BUY=0, OP_SELL=1

        request = {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": order.symbol,
            "volume": float(order.quantity),
            "type": trade_type,
            "price": 0.0,  # Market price
            "deviation": 10,
            "magic": 234000,
            "comment": f"ORION_{order.decision_id[:8]}",
            "type_time": 0,  # ORDER_TIME_GTC
            "type_filling": 0,  # ORDER_FILLING_IOC
        }

        if order.order_type == OrderType.LIMIT and order.price:
            request["action"] = 2  # TRADE_ACTION_PENDING
            request["type"] = 2 if order.side == OrderSide.BUY else 3  # OP_BUYLIMIT/OP_SELLLIMIT
            request["price"] = float(order.price)

        if order.order_type == OrderType.STOP and order.stop_price:
            request["action"] = 2  # TRADE_ACTION_PENDING
            request["type"] = 4 if order.side == OrderSide.BUY else 5  # OP_BUYSTOP/OP_SELLSTOP
            request["price"] = float(order.stop_price)

        return request

    def _build_close_request(self, position: Any) -> dict[str, Any]:
        """Build MT5 close position request."""
        close_type = 1 if position.type == 0 else 0  # Reverse order type
        return {
            "action": 1,  # TRADE_ACTION_DEAL
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": close_type,
            "position": position.ticket,
            "price": 0.0,
            "deviation": 10,
            "magic": 234000,
            "comment": "ORION_CLOSE",
            "type_time": 0,
            "type_filling": 0,
        }


# Helper for timedelta import
from datetime import timedelta  # noqa: E402, F811

