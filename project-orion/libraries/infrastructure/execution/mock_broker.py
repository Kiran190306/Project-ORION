"""Deterministic Institutional Mock Broker Adapter for Project ORION.

Provides a seeded, offline, zero-network implementation of the BrokerAdapter contract.
Simulates realistic broker behaviors and supports scripted failure injection:
- Immediate full fills
- Partial fills with remaining resting order
- Order rejections with configurable rejection reasons
- HTTP 429 rate-limiting simulation
- Simulated network latency & timeouts
- Connection failures
- State discrepancy injection for reconciliation testing
- 100% Decimal financial arithmetic
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
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
    AdapterProviderUnavailableError,
    AdapterRateLimitError,
    AdapterTimeoutError,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionSymbolInfo,
    OrderExecutionInfo,
    PositionInfo,
)

logger = logging.getLogger("infrastructure.execution.mock_broker")


@dataclass(frozen=True, slots=True)
class MockBrokerConfig(BrokerAdapterConfig):
    """Configuration for the deterministic mock broker adapter."""

    broker_name: str = "mock_broker"
    api_endpoint: str = "http://mock-broker.internal"
    account_id: str = "mock_acc_001"
    seed: int | None = 42
    initial_balance: Decimal = Decimal("100000.0000")
    currency: str = "USD"
    leverage: int = 50
    margin_rate: Decimal = Decimal("0.02")  # 1:50 leverage
    simulated_latency_ms: float = 0.0
    mode: str = "IMMEDIATE_FILL"
    partial_fill_fraction: Decimal = Decimal("0.5")
    rejection_reason: str = "INSUFFICIENT_MARGIN"


class MockBrokerAdapter(BrokerAdapter):
    """Deterministic, seeded mock broker adapter for CI/CD and offline verification."""

    DEFAULT_SYMBOLS: dict[str, Decimal] = {
        "EUR/USD": Decimal("1.08500"),
        "EUR_USD": Decimal("1.08500"),
        "GBP/USD": Decimal("1.27500"),
        "GBP_USD": Decimal("1.27500"),
        "USD/JPY": Decimal("155.200"),
        "USD_JPY": Decimal("155.200"),
        "USD/CHF": Decimal("0.89500"),
        "USD_CHF": Decimal("0.89500"),
        "AUD/USD": Decimal("0.65500"),
        "AUD_USD": Decimal("0.65500"),
    }

    def __init__(self, config: MockBrokerConfig | None = None) -> None:
        cfg = config or MockBrokerConfig()
        super().__init__(cfg)
        self._mock_config: MockBrokerConfig = cfg
        self._rng = random.Random(cfg.seed)

        # Operational state
        self._mode: str = cfg.mode
        self._balance: Decimal = cfg.initial_balance
        self._margin_used: Decimal = Decimal("0.0000")
        self._orders: dict[str, OrderExecutionInfo] = {}  # keyed by broker_order_id string
        self._client_order_map: dict[str, str] = {}  # client_order_id -> broker_order_id
        self._positions: dict[str, PositionInfo] = {}  # keyed by symbol
        self._history: list[OrderExecutionInfo] = []
        self._request_count: int = 0
        self._current_prices: dict[str, Decimal] = dict(self.DEFAULT_SYMBOLS)

    # ── Test & Scripting Controls ─────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        """Set the mock execution mode (e.g. IMMEDIATE_FILL, PARTIAL_FILL, REJECT, RATE_LIMIT, TIMEOUT)."""
        self._mode = mode

    def set_price(self, symbol: str, price: Decimal) -> None:
        """Update simulated market price for an instrument."""
        self._current_prices[symbol] = price
        self._current_prices[symbol.replace("/", "_")] = price

    def inject_discrepancy(
        self,
        *,
        balance_offset: Decimal = Decimal("0"),
        extra_position: PositionInfo | None = None,
        extra_order: OrderExecutionInfo | None = None,
    ) -> None:
        """Artificially mutate broker state to test reconciliation detection."""
        if balance_offset != Decimal("0"):
            self._balance += balance_offset
        if extra_position is not None:
            self._positions[extra_position.symbol] = extra_position
        if extra_order is not None:
            b_id = str(extra_order.broker_order_id.value)
            self._orders[b_id] = extra_order

    def reset(self) -> None:
        """Reset internal ledger to initial configuration."""
        self._balance = self._mock_config.initial_balance
        self._margin_used = Decimal("0.0000")
        self._orders.clear()
        self._client_order_map.clear()
        self._positions.clear()
        self._history.clear()
        self._request_count = 0
        self._current_prices = dict(self.DEFAULT_SYMBOLS)
        self._rng = random.Random(self._mock_config.seed)

    # ── Connection Lifecycle ──────────────────────────────────────────

    async def connect(self) -> bool:
        self._request_count += 1
        if self._mode == "CONNECTION_FAILURE":
            raise AdapterConnectionError(
                "Simulated connection failure to mock broker",
                broker_name=self.broker_name,
            )
        if self._mock_config.simulated_latency_ms > 0:
            await asyncio.sleep(self._mock_config.simulated_latency_ms / 1000.0)

        self._connected = True
        self._connection_attempts += 1
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def health_check(self) -> dict[str, Any]:
        self._validate_connected()
        self._request_count += 1
        return {
            "connected": self._connected,
            "latency_ms": self._mock_config.simulated_latency_ms,
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "details": {
                "broker": self.broker_name,
                "mode": self._mode,
                "account_id": self._mock_config.account_id,
                "requests": self._request_count,
            },
        }

    # ── Order Management ──────────────────────────────────────────────

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        self._validate_connected()
        self._request_count += 1

        # Simulate latency
        if self._mock_config.simulated_latency_ms > 0:
            await asyncio.sleep(self._mock_config.simulated_latency_ms / 1000.0)

        # 1. Fault Injection Checks
        if self._mode == "TIMEOUT":
            raise AdapterTimeoutError(
                "Mock broker operation timed out during submission",
                broker_name=self.broker_name,
            )

        if self._mode == "RATE_LIMIT":
            raise AdapterRateLimitError(
                "HTTP 429 Too Many Requests: Rate limit quota exceeded on mock broker",
                broker_name=self.broker_name,
            )

        if self._mode == "PROVIDER_UNAVAILABLE":
            raise AdapterProviderUnavailableError(
                "Mock broker gateway 503 Service Unavailable",
                broker_name=self.broker_name,
            )

        # Idempotency check: if client_order_id exists, return existing execution
        client_oid = str(order.order_id.value)
        if client_oid in self._client_order_map:
            existing_b_id = self._client_order_map[client_oid]
            return self._orders[existing_b_id]

        broker_oid = BrokerOrderId(f"mock_b_{uuid.uuid4().hex[:12]}")
        b_id_str = str(broker_oid.value)
        self._client_order_map[client_oid] = b_id_str

        # 2. Rejection Mode
        if self._mode == "REJECT":
            exec_info = OrderExecutionInfo(
                broker_order_id=broker_oid,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                rejection_reason=self._mock_config.rejection_reason,
                metadata={"client_order_id": client_oid, "symbol": order.symbol},
            )
            self._orders[b_id_str] = exec_info
            self._history.append(exec_info)
            return exec_info

        # 3. Execution Price Resolution
        sym = order.symbol
        base_price = self._current_prices.get(sym) or self._current_prices.get(
            sym.replace("/", "_"), Decimal("1.00000")
        )
        fill_price = order.price if (order.price is not None and order.order_type != OrderType.MARKET) else base_price

        # 4. Partial vs Full Fill
        if self._mode == "PARTIAL_FILL":
            fill_qty = (order.quantity * self._mock_config.partial_fill_fraction).quantize(Decimal("0.01"))
            status = OrderStatus.PARTIALLY_FILLED
        else:
            fill_qty = order.quantity
            status = OrderStatus.FILLED

        fill = Fill(
            fill_id=str(uuid.uuid4()),
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fill_qty,
            price=fill_price,
            commission=Decimal("0.0000"),
            timestamp=datetime.now(timezone.utc),
        )

        exec_info = OrderExecutionInfo(
            broker_order_id=broker_oid,
            status=status,
            filled_quantity=fill_qty,
            average_fill_price=fill_price,
            fills=(fill,),
            metadata={"client_order_id": client_oid, "symbol": order.symbol},
        )
        self._orders[b_id_str] = exec_info
        self._history.append(exec_info)

        # 5. Update Position and Margin
        self._update_position_and_margin(order=order, fill_qty=fill_qty, fill_price=fill_price)

        return exec_info

    def _update_position_and_margin(self, order: Order, fill_qty: Decimal, fill_price: Decimal) -> None:
        """Update internal simulated positions and required margin using Decimal precision."""
        sym = order.symbol
        current_pos = self._positions.get(sym)

        if current_pos is None:
            # New position
            new_pos = PositionInfo(
                position_id=f"pos_{sym.replace('/', '_')}_{uuid.uuid4().hex[:8]}",
                symbol=sym,
                side=order.side,
                quantity=fill_qty,
                open_price=fill_price,
                current_price=fill_price,
            )
            self._positions[sym] = new_pos
            required_margin = (fill_qty * fill_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
            self._margin_used += required_margin
        else:
            # Existing position: netting
            if current_pos.side == order.side:
                # Add to position
                total_qty = current_pos.quantity + fill_qty
                avg_price = (
                    (current_pos.quantity * current_pos.open_price) + (fill_qty * fill_price)
                ) / total_qty
                updated_pos = PositionInfo(
                    position_id=current_pos.position_id,
                    symbol=sym,
                    side=current_pos.side,
                    quantity=total_qty,
                    open_price=avg_price.quantize(Decimal("0.00001")),
                    current_price=fill_price,
                )
                self._positions[sym] = updated_pos
                add_margin = (fill_qty * fill_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
                self._margin_used += add_margin
            else:
                # Opposite side: reduce or close
                if fill_qty >= current_pos.quantity:
                    # Fully close existing position
                    realized_pnl = self._calculate_pnl(
                        side=current_pos.side,
                        open_price=current_pos.open_price,
                        close_price=fill_price,
                        quantity=current_pos.quantity,
                    )
                    self._balance += realized_pnl
                    del self._positions[sym]
                    # Free margin
                    freed_margin = (current_pos.quantity * current_pos.open_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
                    self._margin_used = max(Decimal("0.0000"), self._margin_used - freed_margin)

                    # Remainder opens opposite side
                    remainder = fill_qty - current_pos.quantity
                    if remainder > Decimal("0"):
                        opp_pos = PositionInfo(
                            position_id=f"pos_{sym.replace('/', '_')}_{uuid.uuid4().hex[:8]}",
                            symbol=sym,
                            side=order.side,
                            quantity=remainder,
                            open_price=fill_price,
                            current_price=fill_price,
                        )
                        self._positions[sym] = opp_pos
                        add_margin = (remainder * fill_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
                        self._margin_used += add_margin
                else:
                    # Partially close
                    remaining_qty = current_pos.quantity - fill_qty
                    realized_pnl = self._calculate_pnl(
                        side=current_pos.side,
                        open_price=current_pos.open_price,
                        close_price=fill_price,
                        quantity=fill_qty,
                    )
                    self._balance += realized_pnl
                    updated_pos = PositionInfo(
                        position_id=current_pos.position_id,
                        symbol=sym,
                        side=current_pos.side,
                        quantity=remaining_qty,
                        open_price=current_pos.open_price,
                        current_price=fill_price,
                    )
                    self._positions[sym] = updated_pos
                    freed_margin = (fill_qty * current_pos.open_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
                    self._margin_used = max(Decimal("0.0000"), self._margin_used - freed_margin)

    def _calculate_pnl(
        self, side: OrderSide, open_price: Decimal, close_price: Decimal, quantity: Decimal
    ) -> Decimal:
        if side == OrderSide.BUY:
            return ((close_price - open_price) * quantity).quantize(Decimal("0.0001"))
        else:
            return ((open_price - close_price) * quantity).quantize(Decimal("0.0001"))

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
        self._validate_connected()
        b_id = str(broker_order_id.value)
        if b_id not in self._orders:
            raise AdapterOrderRejectedError(
                f"Order {b_id} not found on mock broker", broker_name=self.broker_name
            )

        existing = self._orders[b_id]
        updated = OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=existing.status,
            filled_quantity=existing.filled_quantity,
            average_fill_price=price or existing.average_fill_price,
            metadata={**existing.metadata, "modified": True},
        )
        self._orders[b_id] = updated
        return updated

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        self._validate_connected()
        b_id = str(broker_order_id.value)
        if b_id not in self._orders:
            return False

        existing = self._orders[b_id]
        cancelled = OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=OrderStatus.CANCELLED,
            filled_quantity=existing.filled_quantity,
            average_fill_price=existing.average_fill_price,
            metadata={**existing.metadata, "cancelled_at": datetime.now(timezone.utc).isoformat()},
        )
        self._orders[b_id] = cancelled
        return True

    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        self._validate_connected()
        target_sym = None
        for sym, pos in self._positions.items():
            if pos.position_id == position_id:
                target_sym = sym
                break

        if target_sym is None:
            raise AdapterOrderRejectedError(
                f"Position {position_id} not found on mock broker",
                broker_name=self.broker_name,
            )

        pos = self._positions[target_sym]
        close_price = self._current_prices.get(pos.symbol, pos.open_price)
        pnl = self._calculate_pnl(
            side=pos.side,
            open_price=pos.open_price,
            close_price=close_price,
            quantity=pos.quantity,
        )
        self._balance += pnl
        del self._positions[target_sym]

        freed_margin = (pos.quantity * pos.open_price * self._mock_config.margin_rate).quantize(Decimal("0.0001"))
        self._margin_used = max(Decimal("0.0000"), self._margin_used - freed_margin)

        broker_oid = BrokerOrderId(f"mock_close_{uuid.uuid4().hex[:12]}")
        exec_info = OrderExecutionInfo(
            broker_order_id=broker_oid,
            status=OrderStatus.FILLED,
            filled_quantity=pos.quantity,
            average_fill_price=close_price,
            metadata={"position_id": position_id, "realized_pnl": str(pnl)},
        )
        self._history.append(exec_info)
        return exec_info

    # ── Queries ───────────────────────────────────────────────────────

    async def get_open_positions(self) -> list[PositionInfo]:
        self._validate_connected()
        # Recalculate profit based on current price
        result: list[PositionInfo] = []
        for pos in self._positions.values():
            curr_p = self._current_prices.get(pos.symbol, pos.open_price)
            profit = self._calculate_pnl(pos.side, pos.open_price, curr_p, pos.quantity)
            updated = PositionInfo(
                position_id=pos.position_id,
                symbol=pos.symbol,
                side=pos.side,
                quantity=pos.quantity,
                open_price=pos.open_price,
                current_price=curr_p,
                profit=profit,
            )
            result.append(updated)
        return result

    async def get_account(self) -> AccountInfo:
        self._validate_connected()
        # Compute unrealized P&L
        unrealized = Decimal("0.0000")
        for pos in self._positions.values():
            curr_p = self._current_prices.get(pos.symbol, pos.open_price)
            unrealized += self._calculate_pnl(pos.side, pos.open_price, curr_p, pos.quantity)

        equity = self._balance + unrealized
        margin_free = max(Decimal("0.0000"), equity - self._margin_used)
        margin_level = (
            float((equity / self._margin_used) * 100) if self._margin_used > Decimal("0") else 0.0
        )

        return AccountInfo(
            account_id=self._mock_config.account_id,
            broker_name=self.broker_name,
            balance=self._balance,
            equity=equity,
            margin=self._margin_used,
            margin_free=margin_free,
            margin_level=margin_level,
            currency=self._mock_config.currency,
            leverage=self._mock_config.leverage,
            is_live=False,  # STRICT INVARIANT: Always False
            metadata={
                "unrealized_pnl": str(unrealized),
                "open_positions": len(self._positions),
                "mode": self._mode,
            },
        )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        self._validate_connected()
        norm_sym = symbol.replace("_", "/")
        return ExecutionSymbolInfo(
            symbol=norm_sym,
            description=f"Mock CFD for {norm_sym}",
            digits=5 if "JPY" not in norm_sym else 3,
            pip_size=Decimal("0.00001") if "JPY" not in norm_sym else Decimal("0.001"),
            pip_value=Decimal("10.00"),
            min_volume=Decimal("1000"),
            max_volume=Decimal("10000000"),
            volume_step=Decimal("1000"),
            spread=1.2,
            is_trade_allowed=True,
            margin_currency="USD",
            margin_rate=float(self._mock_config.margin_rate),
        )

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        self._validate_connected()
        result = self._history
        if symbol:
            result = [o for o in result if o.metadata.get("symbol") == symbol]
        if since:
            result = [o for o in result if o.timestamp >= since]
        return result[-limit:]
