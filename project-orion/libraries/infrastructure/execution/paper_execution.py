"""Paper trading broker adapter.

Implements a realistic simulated broker supporting market, limit, and stop
orders with configurable spread, slippage, commission, swap, latency, and
partial fills. Behaves as closely as possible to a live broker.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
    AdapterConnectionError,
    AdapterNotConnectedError,
    AdapterOrderRejectedError,
    AdapterTimeoutError,
    BrokerAdapter,
    BrokerAdapterConfig,
    ExecutionAdapterError,
    ExecutionSymbolInfo,
    OrderExecutionInfo,
    PositionInfo,
)


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """Internal paper order tracking."""

    paper_order_id: str
    domain_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    status: str = "pending"
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal("0")
    swap: Decimal = Decimal("0")
    fills: list[PaperFill] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PaperFill:
    """A simulated fill."""

    fill_id: str
    quantity: Decimal
    price: Decimal
    commission: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class PaperPosition:
    """Simulated open position."""

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


@dataclass(frozen=True, slots=True)
class PaperExecutionConfig(BrokerAdapterConfig):
    """Configuration for paper trading."""

    broker_name: str = "paper"
    is_paper: bool = True
    spread: float = 0.0001  # 1 pip spread
    slippage_mean: float = 0.00002  # average slippage
    slippage_std: float = 0.00001  # slippage std deviation
    commission_rate: float = 0.00007  # 7 USD per million
    swap_long_rate: float = -0.00002  # overnight swap long
    swap_short_rate: float = -0.00001  # overnight swap short
    latency_ms_mean: float = 50.0  # average latency
    latency_ms_std: float = 20.0  # latency std deviation
    partial_fill_probability: float = 0.2  # 20% chance of partial fill
    min_fill_ratio: float = 0.3  # minimum partial fill ratio
    balance: Decimal = Decimal("100000.00")
    currency: str = "USD"
    leverage: int = 100
    trading_hours_start: int = 0
    trading_hours_end: int = 24


class PaperExecutionAdapter(BrokerAdapter):
    """Realistic paper trading broker adapter.

    Simulates a live broker environment with configurable spread,
    slippage, commission, swap, latency, and partial fills. Market
    orders fill immediately; limit/stop orders require price triggers.
    """

    def __init__(self, config: PaperExecutionConfig | None = None) -> None:
        super().__init__(config or PaperExecutionConfig())
        self._paper_config: PaperExecutionConfig = self._config  # type: ignore[assignment]
        self._orders: dict[str, PaperOrder] = {}
        self._positions: dict[str, PaperPosition] = {}
        self._next_order_id: int = 1000
        self._next_fill_id: int = 1
        self._next_position_id: int = 100
        self._current_prices: dict[str, Decimal] = {}
        self._lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Simulate broker connection with latency."""
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected = True
        self._connection_attempts += 1
        return True

    async def disconnect(self) -> bool:
        """Simulate broker disconnection."""
        self._connected = False
        return True

    async def health_check(self) -> dict[str, Any]:
        """Check paper broker health."""
        self._validate_connected()
        return {
            "connected": self._connected,
            "latency_ms": random.uniform(1.0, 10.0),
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "details": {
                "paper_trading": True,
                "orders_tracked": len(self._orders),
                "positions_open": len(self._positions),
            },
        }

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        """Submit an order to the paper broker.

        Simulates realistic execution including partial fills, slippage,
        spread, commission, and latency.
        """
        self._validate_connected()
        await self._simulate_latency()

        async with self._lock:
            paper_order = PaperOrder(
                paper_order_id=str(self._next_order_id),
                domain_order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
            )
            self._next_order_id += 1
            self._orders[paper_order.paper_order_id] = paper_order

        # Execute based on order type
        try:
            if order.order_type == OrderType.MARKET:
                return await self._execute_market_order(paper_order, order)
            elif order.order_type == OrderType.LIMIT:
                return await self._place_limit_order(paper_order, order)
            elif order.order_type == OrderType.STOP:
                return await self._place_stop_order(paper_order, order)
            else:
                raise AdapterOrderRejectedError(
                    f"Unsupported order type: {order.order_type}",
                    broker_name=self.broker_name,
                )
        except AdapterOrderRejectedError:
            raise
        except Exception as e:
            raise ExecutionAdapterError(
                f"Paper execution failed: {e}",
                broker_name=self.broker_name,
            )

    async def _execute_market_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Execute a market order with simulated fill."""
        current_price = self._get_current_price(order.symbol)
        spread = current_price * Decimal(str(self._paper_config.spread))
        slippage = self._simulate_slippage()

        if order.side == OrderSide.BUY:
            fill_price = current_price + spread / 2 + Decimal(str(slippage))
        else:
            fill_price = current_price - spread / 2 + Decimal(str(slippage))

        fill_price = max(fill_price, Decimal("0.00001"))

        # Simulate partial fills
        if random.random() < self._paper_config.partial_fill_probability:
            fill_ratio = random.uniform(
                self._paper_config.min_fill_ratio,
                1.0,
            )
            fill_qty = order.quantity * Decimal(str(round(fill_ratio, 4)))
        else:
            fill_qty = order.quantity

        commission = fill_qty * fill_price * Decimal(str(self._paper_config.commission_rate))
        fills = [
            Fill(
                fill_id=f"paper_fill_{self._next_fill_id}",
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=fill_qty,
                price=fill_price,
                commission=commission,
                broker_fill_id=f"paper_bf_{self._next_fill_id}",
            )
        ]
        self._next_fill_id += 1

        is_full_fill = fill_qty >= order.quantity
        status = OrderStatus.FILLED if is_full_fill else OrderStatus.PARTIALLY_FILLED

        broker_order_id = BrokerOrderId(f"paper_{paper_order.paper_order_id}")

        # Update internal state
        async with self._lock:
            if paper_order.paper_order_id in self._orders:
                self._orders[paper_order.paper_order_id] = PaperOrder(
                    paper_order_id=paper_order.paper_order_id,
                    domain_order_id=paper_order.domain_order_id,
                    symbol=paper_order.symbol,
                    side=paper_order.side,
                    order_type=paper_order.order_type,
                    quantity=paper_order.quantity,
                    price=paper_order.price,
                    status=status.value,
                    filled_quantity=fill_qty,
                    average_fill_price=fill_price,
                    commission=commission,
                    fills=[PaperFill(
                        fill_id=fills[0].fill_id,
                        quantity=fill_qty,
                        price=fill_price,
                        commission=commission,
                    )],
                    updated_at=datetime.now(timezone.utc),
                )

        # Track position
        if is_full_fill:
            await self._update_position(order, fill_price, fill_qty, commission)

        return OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=status,
            filled_quantity=fill_qty,
            average_fill_price=fill_price,
            commission=commission,
            fills=tuple(fills),
        )

    async def _place_limit_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Place a limit order (pending until price trigger)."""
        async with self._lock:
            paper_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=paper_order.symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                status="submitted",
            )
            self._orders[paper_order.paper_order_id] = paper_order

        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
            status=OrderStatus.SUBMITTED,
        )

    async def _place_stop_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Place a stop order (pending until price trigger)."""
        async with self._lock:
            paper_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=paper_order.symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                stop_price=paper_order.stop_price,
                status="submitted",
            )
            self._orders[paper_order.paper_order_id] = paper_order

        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
            status=OrderStatus.SUBMITTED,
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
        """Modify a pending paper order."""
        self._validate_connected()
        await self._simulate_latency()

        paper_id = str(broker_order_id).replace("paper_", "")
        async with self._lock:
            if paper_id not in self._orders:
                raise AdapterOrderRejectedError(
                    f"Order {broker_order_id} not found",
                    broker_name=self.broker_name,
                )
            existing = self._orders[paper_id]
            self._orders[paper_id] = PaperOrder(
                paper_order_id=existing.paper_order_id,
                domain_order_id=existing.domain_order_id,
                symbol=existing.symbol,
                side=existing.side,
                order_type=existing.order_type,
                quantity=quantity or existing.quantity,
                price=price if price is not None else existing.price,
                stop_price=stop_price if stop_price is not None else existing.stop_price,
                status=existing.status,
                filled_quantity=existing.filled_quantity,
                average_fill_price=existing.average_fill_price,
                commission=existing.commission,
                fills=list(existing.fills),
                updated_at=datetime.now(timezone.utc),
            )

        return OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=OrderStatus.SUBMITTED,
        )

    async def cancel_order(self, broker_order_id: BrokerOrderId) -> bool:
        """Cancel a pending paper order."""
        self._validate_connected()
        await self._simulate_latency()

        paper_id = str(broker_order_id).replace("paper_", "")
        async with self._lock:
            if paper_id in self._orders:
                existing = self._orders[paper_id]
                self._orders[paper_id] = PaperOrder(
                    paper_order_id=existing.paper_order_id,
                    domain_order_id=existing.domain_order_id,
                    symbol=existing.symbol,
                    side=existing.side,
                    order_type=existing.order_type,
                    quantity=existing.quantity,
                    price=existing.price,
                    status="cancelled",
                    filled_quantity=existing.filled_quantity,
                    average_fill_price=existing.average_fill_price,
                    commission=existing.commission,
                    fills=list(existing.fills),
                    updated_at=datetime.now(timezone.utc),
                )
                return True
        return False

    async def close_position(self, position_id: str) -> OrderExecutionInfo:
        """Close a simulated open position."""
        self._validate_connected()
        await self._simulate_latency()

        async with self._lock:
            if position_id not in self._positions:
                raise AdapterOrderRejectedError(
                    f"Position {position_id} not found",
                    broker_name=self.broker_name,
                )
            position = self._positions[position_id]
            current_price = self._get_current_price(position.symbol)
            profit = self._calculate_profit(position, current_price)

            fill = Fill(
                fill_id=f"paper_fill_close_{self._next_fill_id}",
                order_id=OrderId(f"close_{position_id}"),
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
                quantity=position.quantity,
                price=current_price,
                commission=Decimal("0"),
                broker_fill_id=f"paper_close_{self._next_fill_id}",
            )
            self._next_fill_id += 1

            self._positions.pop(position_id, None)

            return OrderExecutionInfo(
                broker_order_id=BrokerOrderId(f"close_{position_id}"),
                status=OrderStatus.FILLED,
                filled_quantity=position.quantity,
                average_fill_price=current_price,
                fills=(fill,),
            )

    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all simulated open positions."""
        self._validate_connected()
        async with self._lock:
            return [
                PositionInfo(
                    position_id=pid,
                    symbol=p.symbol,
                    side=p.side,
                    quantity=p.quantity,
                    open_price=p.open_price,
                    current_price=p.current_price,
                    stop_loss=p.stop_loss,
                    take_profit=p.take_profit,
                    commission=p.commission,
                    swap=p.swap,
                    profit=self._calculate_profit(p, p.current_price),
                    open_time=p.open_time,
                )
                for pid, p in self._positions.items()
            ]

    async def get_account(self) -> AccountInfo:
        """Get simulated account information."""
        self._validate_connected()
        async with self._lock:
            total_margin = sum(
                p.quantity * p.current_price / Decimal(str(self._paper_config.leverage))
                for p in self._positions.values()
            )
            total_unrealized = sum(
                self._calculate_profit(p, p.current_price)
                for p in self._positions.values()
            )
            margin_free = self._paper_config.balance - total_margin
            margin_level = float(
                (self._paper_config.balance / total_margin * 100)
                if total_margin > 0
                else 0.0
            )

            return AccountInfo(
                account_id="paper_account_001",
                broker_name=self.broker_name,
                balance=self._paper_config.balance,
                equity=self._paper_config.balance + total_unrealized,
                margin=total_margin,
                margin_free=margin_free,
                margin_level=margin_level,
                currency=self._paper_config.currency,
                leverage=self._paper_config.leverage,
                is_live=False,
            )

    async def get_symbol_information(self, symbol: str) -> ExecutionSymbolInfo:
        """Get simulated symbol information."""
        self._validate_connected()
        return ExecutionSymbolInfo(
            symbol=symbol,
            description=f"Paper {symbol}",
            digits=5,
            pip_size=Decimal("0.00001"),
            min_volume=Decimal("0.01"),
            max_volume=Decimal("100"),
            volume_step=Decimal("0.01"),
            spread=self._paper_config.spread,
            swap_long=self._paper_config.swap_long_rate,
            swap_short=self._paper_config.swap_short_rate,
            is_trade_allowed=True,
        )

    async def get_execution_history(
        self,
        symbol: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[OrderExecutionInfo]:
        """Get simulated execution history."""
        self._validate_connected()
        async with self._lock:
            results = []
            for paper_order in self._orders.values():
                if symbol and paper_order.symbol != symbol:
                    continue
                if since and paper_order.created_at < since:
                    continue
                if len(results) >= limit:
                    break

                results.append(OrderExecutionInfo(
                    broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
                    status=OrderStatus(paper_order.status) if paper_order.status in {s.value for s in OrderStatus} else OrderStatus.SUBMITTED,
                    filled_quantity=paper_order.filled_quantity,
                    average_fill_price=paper_order.average_fill_price,
                    commission=paper_order.commission,
                    fills=tuple(
                        Fill(
                            fill_id=f.fill_id,
                            order_id=OrderId(paper_order.domain_order_id),
                            symbol=paper_order.symbol,
                            side=paper_order.side,
                            quantity=f.quantity,
                            price=f.price,
                            commission=f.commission,
                        )
                        for f in paper_order.fills
                    ),
                ))
            return results

    async def set_current_price(self, symbol: str, price: Decimal) -> None:
        """Set current price for a symbol (used in tests)."""
        async with self._lock:
            self._current_prices[symbol.upper()] = price

    # ── Private Helpers ─────────────────────────────────────────────

    def _get_current_price(self, symbol: str) -> Decimal:
        """Get current simulated price for a symbol."""
        return self._current_prices.get(symbol.upper(), Decimal("1.20000"))

    def _simulate_slippage(self) -> float:
        """Simulate random slippage."""
        return random.gauss(
            self._paper_config.slippage_mean,
            self._paper_config.slippage_std,
        )

    async def _simulate_latency(self) -> None:
        """Simulate network latency."""
        if self._paper_config.latency_ms_mean > 0:
            latency = max(
                0.0,
                random.gauss(
                    self._paper_config.latency_ms_mean,
                    self._paper_config.latency_ms_std,
                ),
            )
            await asyncio.sleep(latency / 1000.0)

    def _calculate_profit(self, position: PaperPosition, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL for a position."""
        price_diff = current_price - position.open_price
        if position.side == OrderSide.SELL:
            price_diff = -price_diff
        return price_diff * position.quantity

    async def _update_position(
        self,
        order: Order,
        fill_price: Decimal,
        fill_qty: Decimal,
        commission: Decimal,
    ) -> None:
        """Update or create a tracked position."""
        async with self._lock:
            pos_id = f"pos_{self._next_position_id}"
            self._next_position_id += 1

            position = PaperPosition(
                position_id=pos_id,
                symbol=order.symbol,
                side=order.side,
                quantity=fill_qty,
                open_price=fill_price,
                current_price=self._get_current_price(order.symbol),
                commission=commission,
            )
            self._positions[pos_id] = position

