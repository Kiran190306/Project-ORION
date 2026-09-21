"""Paper trading broker adapter.

Implements an institutional-grade simulated broker supporting market, limit,
stop, and trailing stop orders with configurable spread, adverse slippage,
commission, swap, latency, partial fills, position netting, and resting
order / SL / TP triggers. Strictly paper trading only ($0.00 capital at risk).
"""

from __future__ import annotations

import asyncio
import random
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
    AdapterOrderRejectedError,
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
    filled_quantity: Decimal = Decimal(0)
    average_fill_price: Decimal | None = None
    commission: Decimal = Decimal(0)
    swap: Decimal = Decimal(0)
    fills: list[PaperFill] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    trailing_distance: Decimal | None = None


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
    """Simulated open position with position tracking and trigger points."""

    position_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    open_price: Decimal
    current_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    trailing_distance: Decimal | None = None
    high_water_mark: Decimal | None = None
    low_water_mark: Decimal | None = None
    commission: Decimal = Decimal(0)
    swap: Decimal = Decimal(0)
    profit: Decimal = Decimal(0)
    realized_pnl: Decimal = Decimal(0)
    open_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class PaperExecutionConfig(BrokerAdapterConfig):
    """Configuration for paper trading simulation."""

    broker_name: str = "paper"
    is_paper: bool = True
    spread: float = 0.0001  # 1 pip spread on major FX
    slippage_mean: float = 0.00002  # average slippage
    slippage_std: float = 0.00001  # slippage std deviation
    commission_rate: float = 0.00007  # $7 USD per standard lot / million
    swap_long_rate: float = -0.00002  # overnight swap long
    swap_short_rate: float = -0.00001  # overnight swap short
    latency_ms_mean: float = 50.0  # average latency in ms
    latency_ms_std: float = 20.0  # latency std deviation in ms
    partial_fill_probability: float = 0.0  # probability of partial fill (default 0 for tests)
    min_fill_ratio: float = 0.3  # minimum partial fill ratio
    balance: Decimal = Decimal("100000.00")
    currency: str = "USD"
    leverage: int = 100
    trading_hours_start: int = 0
    trading_hours_end: int = 24
    deterministic: bool = False  # when True, zero latency sleep and deterministic fills


class PaperExecutionAdapter(BrokerAdapter):
    """Institutional-grade paper trading broker adapter.

    Simulates realistic exchange & OTC broker microstructure:
    - Side-aware pricing: BUY fills against Ask; SELL fills against Bid.
    - Adverse slippage: increases price for BUY, decreases price for SELL.
    - Resting limit & stop order evaluation against incoming quotes.
    - Position netting, accumulation with weighted average entry, and reduction.
    - Dynamic Stop Loss, Take Profit, and Trailing Stop execution.
    - Strict isolation: zero live broker routing; paper money only.
    """

    def __init__(self, config: PaperExecutionConfig | None = None) -> None:
        cfg = config or PaperExecutionConfig()
        super().__init__(cfg)
        self._paper_config: PaperExecutionConfig = cfg
        self._orders: dict[str, PaperOrder] = {}
        self._pending_orders: dict[str, PaperOrder] = {}
        self._positions: dict[str, PaperPosition] = {}
        self._next_order_id: int = 1000
        self._next_fill_id: int = 1
        self._next_position_id: int = 100
        self._current_prices: dict[str, Decimal] = {}
        self._current_quotes: dict[str, dict[str, Decimal]] = {}
        self._current_balance: Decimal = cfg.balance
        self._lock = asyncio.Lock()

    @property
    def config(self) -> PaperExecutionConfig:
        return self._paper_config

    async def connect(self) -> bool:
        """Simulate broker connection with latency."""
        if not self._paper_config.deterministic:
            await asyncio.sleep(0.05)
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
            "latency_ms": 1.0 if self._paper_config.deterministic else random.uniform(1.0, 10.0),
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "details": {
                "paper_trading": True,
                "orders_tracked": len(self._orders),
                "pending_orders": len(self._pending_orders),
                "positions_open": len(self._positions),
                "balance": str(self._current_balance),
            },
        }

    async def submit_order(self, order: Order) -> OrderExecutionInfo:
        """Submit an order to the paper matching engine.

        Simulates realistic execution:
        - Market order: executes immediately at Ask (BUY) or Bid (SELL) +/- adverse slippage.
        - Limit order: rests until market price reaches limit or fills immediately if marketable.
        - Stop order: rests until stop price is touched, then triggers market fill.
        """
        self._validate_connected()
        await self._simulate_latency()

        async with self._lock:
            paper_order_id = str(self._next_order_id)
            self._next_order_id += 1

            paper_order = PaperOrder(
                paper_order_id=paper_order_id,
                domain_order_id=str(order.order_id),
                symbol=order.symbol.upper().replace("/", "").replace("_", ""),
                side=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                price=order.price,
                stop_price=order.stop_price,
                stop_loss=order.stop_price if hasattr(order, "stop_price") else getattr(order, "stop_loss", None),
                take_profit=getattr(order, "take_profit", None),
                trailing_distance=getattr(order, "trailing_distance", None),
            )
            self._orders[paper_order_id] = paper_order

        # Execute based on order type
        try:
            if order.order_type == OrderType.MARKET:
                return await self._execute_market_order(paper_order, order)
            elif order.order_type == OrderType.LIMIT:
                return await self._place_limit_order(paper_order, order)
            elif order.order_type == OrderType.STOP:
                return await self._place_stop_order(paper_order, order)
            elif order.order_type == OrderType.TRAILING_STOP:
                return await self._place_trailing_stop_order(paper_order, order)
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
            ) from e

    async def _execute_market_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Execute a market order with realistic side-aware pricing and adverse slippage."""
        symbol = paper_order.symbol
        bid, ask, _ = self._get_quote(symbol)
        slippage = self._simulate_slippage()

        # Side-aware pricing with strictly ADVERSE slippage
        if order.side == OrderSide.BUY:
            # Buyers pay Ask + adverse slippage (price increases)
            fill_price = ask + slippage
        else:
            # Sellers receive Bid - adverse slippage (price decreases)
            fill_price = max(Decimal("0.00001"), bid - slippage)

        # Simulate partial fills if enabled
        if (
            not self._paper_config.deterministic
            and self._paper_config.partial_fill_probability > 0.0
            and random.random() < self._paper_config.partial_fill_probability
        ):
            fill_ratio = random.uniform(self._paper_config.min_fill_ratio, 0.95)
            fill_qty = (order.quantity * Decimal(str(round(fill_ratio, 4)))).quantize(Decimal("0.01"))
            if fill_qty <= Decimal(0):
                fill_qty = order.quantity
        else:
            fill_qty = order.quantity

        commission = (fill_qty * fill_price * Decimal(str(self._paper_config.commission_rate))).quantize(Decimal("0.0001"))

        async with self._lock:
            fill_id = f"paper_fill_{self._next_fill_id}"
            self._next_fill_id += 1

            fill = Fill(
                fill_id=fill_id,
                order_id=order.order_id,
                symbol=symbol,
                side=order.side,
                quantity=fill_qty,
                price=fill_price,
                commission=commission,
                broker_fill_id=f"paper_bf_{fill_id}",
            )

            is_full_fill = fill_qty >= order.quantity
            status = OrderStatus.FILLED if is_full_fill else OrderStatus.PARTIALLY_FILLED
            broker_order_id = BrokerOrderId(f"paper_{paper_order.paper_order_id}")

            # Update tracked order
            updated_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                stop_price=paper_order.stop_price,
                status=status.value,
                filled_quantity=fill_qty,
                average_fill_price=fill_price,
                commission=commission,
                fills=[
                    PaperFill(
                        fill_id=fill.fill_id,
                        quantity=fill_qty,
                        price=fill_price,
                        commission=commission,
                    )
                ],
                updated_at=datetime.now(timezone.utc),
                stop_loss=paper_order.stop_loss,
                take_profit=paper_order.take_profit,
                trailing_distance=paper_order.trailing_distance,
            )
            self._orders[paper_order.paper_order_id] = updated_order

            # Position netting and accounting update
            await self._update_position_locked(order, fill_price, fill_qty, commission)

        return OrderExecutionInfo(
            broker_order_id=broker_order_id,
            status=status,
            filled_quantity=fill_qty,
            average_fill_price=fill_price,
            commission=commission,
            fills=(fill,),
        )

    async def _place_limit_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Place a limit order. Fills immediately if marketable, else rests until trigger."""
        if order.price is None:
            raise AdapterOrderRejectedError("Limit order requires price", broker_name=self.broker_name)

        symbol = paper_order.symbol
        bid, ask, _ = self._get_quote(symbol)

        # Check if immediately marketable
        is_marketable = (order.side == OrderSide.BUY and ask <= order.price) or (
            order.side == OrderSide.SELL and bid >= order.price
        )

        if is_marketable:
            return await self._execute_market_order(paper_order, order)

        async with self._lock:
            updated_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                status="submitted",
                stop_loss=paper_order.stop_loss,
                take_profit=paper_order.take_profit,
                trailing_distance=paper_order.trailing_distance,
            )
            self._orders[paper_order.paper_order_id] = updated_order
            self._pending_orders[paper_order.paper_order_id] = updated_order

        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
            status=OrderStatus.SUBMITTED,
        )

    async def _place_stop_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Place a stop order. Fills immediately if triggered, else rests until trigger."""
        stop_price = order.stop_price or getattr(order, "stop_loss", None)
        if stop_price is None:
            raise AdapterOrderRejectedError("Stop order requires stop_price", broker_name=self.broker_name)

        symbol = paper_order.symbol
        bid, ask, _ = self._get_quote(symbol)

        # Check if already triggered
        is_triggered = (order.side == OrderSide.BUY and ask >= stop_price) or (
            order.side == OrderSide.SELL and bid <= stop_price
        )

        if is_triggered:
            return await self._execute_market_order(paper_order, order)

        async with self._lock:
            updated_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=symbol,
                side=paper_order.side,
                order_type=paper_order.order_type,
                quantity=paper_order.quantity,
                price=paper_order.price,
                stop_price=stop_price,
                status="submitted",
                stop_loss=paper_order.stop_loss,
                take_profit=paper_order.take_profit,
                trailing_distance=paper_order.trailing_distance,
            )
            self._orders[paper_order.paper_order_id] = updated_order
            self._pending_orders[paper_order.paper_order_id] = updated_order

        return OrderExecutionInfo(
            broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
            status=OrderStatus.SUBMITTED,
        )

    async def _place_trailing_stop_order(
        self,
        paper_order: PaperOrder,
        order: Order,
    ) -> OrderExecutionInfo:
        """Place a trailing stop order."""
        dist = getattr(order, "trailing_distance", None)
        if dist is None or dist <= Decimal(0):
            raise AdapterOrderRejectedError("Trailing stop requires positive trailing_distance", broker_name=self.broker_name)

        symbol = paper_order.symbol
        bid, ask, _ = self._get_quote(symbol)
        ref_price = bid if order.side == OrderSide.SELL else ask
        initial_stop = ref_price - dist if order.side == OrderSide.BUY else ref_price + dist

        async with self._lock:
            updated_order = PaperOrder(
                paper_order_id=paper_order.paper_order_id,
                domain_order_id=paper_order.domain_order_id,
                symbol=symbol,
                side=paper_order.side,
                order_type=OrderType.TRAILING_STOP,
                quantity=paper_order.quantity,
                stop_price=initial_stop,
                status="submitted",
                trailing_distance=dist,
            )
            self._orders[paper_order.paper_order_id] = updated_order
            self._pending_orders[paper_order.paper_order_id] = updated_order

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
            if existing.status not in ("submitted", "pending", "partially_filled"):
                raise AdapterOrderRejectedError(
                    f"Cannot modify order in state '{existing.status}'",
                    broker_name=self.broker_name,
                )

            updated = PaperOrder(
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
                stop_loss=stop_loss if stop_loss is not None else existing.stop_loss,
                take_profit=take_profit if take_profit is not None else existing.take_profit,
                trailing_distance=existing.trailing_distance,
            )
            self._orders[paper_id] = updated
            if paper_id in self._pending_orders:
                self._pending_orders[paper_id] = updated

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
                if existing.status in ("filled", "cancelled", "rejected", "expired"):
                    return False

                cancelled = PaperOrder(
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
                self._orders[paper_id] = cancelled
                self._pending_orders.pop(paper_id, None)
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
            bid, ask, _ = self._get_quote(position.symbol)
            close_price = bid if position.side == OrderSide.BUY else ask

            # Calculate realized PnL
            if position.side == OrderSide.BUY:
                pnl = (close_price - position.open_price) * position.quantity - position.commission - position.swap
            else:
                pnl = (position.open_price - close_price) * position.quantity - position.commission - position.swap

            self._current_balance += pnl

            fill_id = f"paper_fill_close_{self._next_fill_id}"
            self._next_fill_id += 1
            fill = Fill(
                fill_id=fill_id,
                order_id=OrderId(f"close_{position_id}"),
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY,
                quantity=position.quantity,
                price=close_price,
                commission=Decimal(0),
                broker_fill_id=f"paper_close_{fill_id}",
            )

            self._positions.pop(position_id, None)

            return OrderExecutionInfo(
                broker_order_id=BrokerOrderId(f"close_{position_id}"),
                status=OrderStatus.FILLED,
                filled_quantity=position.quantity,
                average_fill_price=close_price,
                fills=(fill,),
            )

    async def get_open_positions(self) -> list[PositionInfo]:
        """Get all simulated open positions."""
        self._validate_connected()
        async with self._lock:
            results: list[PositionInfo] = []
            for pid, p in self._positions.items():
                bid, ask, _ = self._get_quote(p.symbol)
                current_price = bid if p.side == OrderSide.BUY else ask
                results.append(
                    PositionInfo(
                        position_id=pid,
                        symbol=p.symbol,
                        side=p.side,
                        quantity=p.quantity,
                        open_price=p.open_price,
                        current_price=current_price,
                        stop_loss=p.stop_loss,
                        take_profit=p.take_profit,
                        commission=p.commission,
                        swap=p.swap,
                        profit=self._calculate_profit(p, current_price),
                        open_time=p.open_time,
                    )
                )
            return results

    async def get_account(self) -> AccountInfo:
        """Get simulated account information with accurate margin and equity."""
        self._validate_connected()
        async with self._lock:
            total_margin = Decimal(0)
            total_unrealized = Decimal(0)

            for p in self._positions.values():
                bid, ask, _ = self._get_quote(p.symbol)
                current_price = bid if p.side == OrderSide.BUY else ask
                margin = (p.quantity * current_price) / Decimal(str(self._paper_config.leverage))
                total_margin += margin
                total_unrealized += self._calculate_profit(p, current_price)

            equity = self._current_balance + total_unrealized
            margin_free = max(Decimal(0), equity - total_margin)
            margin_level = float((equity / total_margin * 100) if total_margin > Decimal(0) else 0.0)

            return AccountInfo(
                account_id="paper_account_001",
                broker_name=self.broker_name,
                balance=self._current_balance,
                equity=equity,
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
        norm_symbol = symbol.upper().replace("/", "").replace("_", "")
        _, _, spread = self._get_quote(norm_symbol)
        return ExecutionSymbolInfo(
            symbol=norm_symbol,
            description=f"Paper {norm_symbol}",
            digits=5,
            pip_size=Decimal("0.00001"),
            min_volume=Decimal("0.01"),
            max_volume=Decimal(100),
            volume_step=Decimal("0.01"),
            spread=float(spread),
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
            results: list[OrderExecutionInfo] = []
            norm_symbol = symbol.upper().replace("/", "").replace("_", "") if symbol else None
            for paper_order in self._orders.values():
                if norm_symbol and paper_order.symbol != norm_symbol:
                    continue
                if since and paper_order.created_at < since:
                    continue
                if len(results) >= limit:
                    break

                results.append(
                    OrderExecutionInfo(
                        broker_order_id=BrokerOrderId(f"paper_{paper_order.paper_order_id}"),
                        status=(
                            OrderStatus(paper_order.status)
                            if paper_order.status in {s.value for s in OrderStatus}
                            else OrderStatus.SUBMITTED
                        ),
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
                    )
                )
            return results

    async def set_current_price(self, symbol: str, price: Decimal) -> None:
        """Set current price for a symbol and evaluate resting triggers."""
        norm_symbol = symbol.upper().replace("/", "").replace("_", "")
        spread = price * Decimal(str(self._paper_config.spread))
        bid = price - spread / Decimal(2)
        ask = price + spread / Decimal(2)

        async with self._lock:
            self._current_prices[norm_symbol] = price
            self._current_quotes[norm_symbol] = {"bid": bid, "ask": ask, "mid": price, "spread": spread}
            if symbol and symbol != norm_symbol:
                self._current_prices[symbol] = price
                self._current_quotes[symbol] = {"bid": bid, "ask": ask, "mid": price, "spread": spread}

        await self._evaluate_resting_triggers(norm_symbol, bid, ask)

    async def update_quote(self, quote: Any) -> None:
        """Ingest fresh quote from MarketDataService and trigger resting orders/SL/TP."""
        symbol_raw = getattr(quote, "symbol", None) or (quote.get("symbol") if isinstance(quote, dict) else "")
        norm_symbol = str(symbol_raw).upper().replace("/", "").replace("_", "")
        if not norm_symbol:
            return

        bid = Decimal(str(getattr(quote, "bid", None) or (quote.get("bid") if isinstance(quote, dict) else "1.20000")))
        ask = Decimal(str(getattr(quote, "ask", None) or (quote.get("ask") if isinstance(quote, dict) else "1.20010")))
        mid = Decimal(str(getattr(quote, "mid", None) or (quote.get("mid") if isinstance(quote, dict) else (bid + ask) / Decimal(2))))
        spread = Decimal(str(getattr(quote, "spread", None) or (quote.get("spread") if isinstance(quote, dict) else (ask - bid))))

        async with self._lock:
            self._current_prices[norm_symbol] = mid
            self._current_quotes[norm_symbol] = {"bid": bid, "ask": ask, "mid": mid, "spread": spread}
            if symbol_raw and symbol_raw != norm_symbol:
                self._current_prices[symbol_raw] = mid
                self._current_quotes[symbol_raw] = {"bid": bid, "ask": ask, "mid": mid, "spread": spread}

        await self._evaluate_resting_triggers(norm_symbol, bid, ask)

    async def reset_account(self, balance: Decimal = Decimal("100000.00")) -> None:
        """Reset paper account balance and clear all active positions and orders."""
        async with self._lock:
            self._orders.clear()
            self._pending_orders.clear()
            self._positions.clear()
            self._current_balance = balance
            self._next_order_id = 1000
            self._next_fill_id = 1
            self._next_position_id = 100

    def update_config(self, **kwargs: Any) -> None:
        """Update simulation configuration parameters dynamically."""
        new_dict = {
            "broker_name": self._paper_config.broker_name,
            "is_paper": True,
            "spread": kwargs.get("spread", self._paper_config.spread),
            "slippage_mean": kwargs.get("slippage_mean", self._paper_config.slippage_mean),
            "slippage_std": kwargs.get("slippage_std", self._paper_config.slippage_std),
            "commission_rate": kwargs.get("commission_rate", self._paper_config.commission_rate),
            "swap_long_rate": kwargs.get("swap_long_rate", self._paper_config.swap_long_rate),
            "swap_short_rate": kwargs.get("swap_short_rate", self._paper_config.swap_short_rate),
            "latency_ms_mean": kwargs.get("latency_ms_mean", self._paper_config.latency_ms_mean),
            "latency_ms_std": kwargs.get("latency_ms_std", self._paper_config.latency_ms_std),
            "partial_fill_probability": kwargs.get("partial_fill_probability", self._paper_config.partial_fill_probability),
            "min_fill_ratio": kwargs.get("min_fill_ratio", self._paper_config.min_fill_ratio),
            "balance": kwargs.get("balance", self._paper_config.balance),
            "currency": kwargs.get("currency", self._paper_config.currency),
            "leverage": kwargs.get("leverage", self._paper_config.leverage),
            "deterministic": kwargs.get("deterministic", self._paper_config.deterministic),
        }
        self._paper_config = PaperExecutionConfig(**new_dict)

    # ── Private Microstructure & Trigger Helpers ───────────────────────────

    def _get_quote(self, symbol: str) -> tuple[Decimal, Decimal, Decimal]:
        """Return (bid, ask, spread) for a symbol."""
        norm_symbol = symbol.upper().replace("/", "").replace("_", "")
        if norm_symbol in self._current_quotes:
            q = self._current_quotes[norm_symbol]
            return q["bid"], q["ask"], q["spread"]

        price = self._current_prices.get(norm_symbol, Decimal("1.20000"))
        spread = price * Decimal(str(self._paper_config.spread))
        bid = price - spread / Decimal(2)
        ask = price + spread / Decimal(2)
        return bid, ask, spread

    def _simulate_slippage(self) -> Decimal:
        """Simulate strictly positive adverse slippage magnitude."""
        if self._paper_config.deterministic:
            return Decimal(0)

        val = max(0.0, random.gauss(self._paper_config.slippage_mean, self._paper_config.slippage_std))
        return Decimal(str(round(val, 6)))

    async def _simulate_latency(self) -> None:
        """Simulate realistic network/order matching latency."""
        if self._paper_config.deterministic or self._paper_config.latency_ms_mean <= 0:
            return

        latency = max(0.0, random.gauss(self._paper_config.latency_ms_mean, self._paper_config.latency_ms_std))
        if latency > 0:
            await asyncio.sleep(latency / 1000.0)

    def _calculate_profit(self, position: PaperPosition, current_price: Decimal) -> Decimal:
        """Calculate unrealized PnL for an open position."""
        if position.side == OrderSide.BUY:
            price_diff = current_price - position.open_price
        else:
            price_diff = position.open_price - current_price
        return price_diff * position.quantity

    async def _update_position_locked(
        self,
        order: Order,
        fill_price: Decimal,
        fill_qty: Decimal,
        commission: Decimal,
    ) -> None:
        """Update positions with institutional netting and accumulation (caller holds lock)."""
        symbol = order.symbol.upper().replace("/", "").replace("_", "")

        # Find existing position for this symbol
        existing_pos_id: str | None = None
        for pid, p in self._positions.items():
            if p.symbol == symbol:
                existing_pos_id = pid
                break

        if existing_pos_id is None:
            # 1. No open position -> open new position
            pos_id = f"pos_{self._next_position_id}"
            self._next_position_id += 1
            ref_price = fill_price
            high_water = ref_price if order.side == OrderSide.BUY else None
            low_water = ref_price if order.side == OrderSide.SELL else None

            self._positions[pos_id] = PaperPosition(
                position_id=pos_id,
                symbol=symbol,
                side=order.side,
                quantity=fill_qty,
                open_price=fill_price,
                current_price=fill_price,
                stop_loss=order.stop_price if hasattr(order, "stop_price") else getattr(order, "stop_loss", None),
                take_profit=getattr(order, "take_profit", None),
                trailing_distance=getattr(order, "trailing_distance", None),
                high_water_mark=high_water,
                low_water_mark=low_water,
                commission=commission,
            )
            return

        existing = self._positions[existing_pos_id]

        if existing.side == order.side:
            # 2. Same direction -> accumulate position with weighted average entry price
            new_qty = existing.quantity + fill_qty
            new_open_price = ((existing.open_price * existing.quantity) + (fill_price * fill_qty)) / new_qty
            new_commission = existing.commission + commission

            self._positions[existing_pos_id] = PaperPosition(
                position_id=existing.position_id,
                symbol=existing.symbol,
                side=existing.side,
                quantity=new_qty,
                open_price=new_open_price,
                current_price=fill_price,
                stop_loss=getattr(order, "stop_loss", existing.stop_loss),
                take_profit=getattr(order, "take_profit", existing.take_profit),
                trailing_distance=getattr(order, "trailing_distance", existing.trailing_distance),
                high_water_mark=max(existing.high_water_mark or fill_price, fill_price) if existing.side == OrderSide.BUY else None,
                low_water_mark=min(existing.low_water_mark or fill_price, fill_price) if existing.side == OrderSide.SELL else None,
                commission=new_commission,
                swap=existing.swap,
                open_time=existing.open_time,
            )
        else:
            # 3. Opposite direction -> netting / position reduction / closure
            if fill_qty < existing.quantity:
                # Partial reduction
                closed_qty = fill_qty
                remaining_qty = existing.quantity - fill_qty

                # Realize PnL on closed portion
                if existing.side == OrderSide.BUY:
                    pnl = (fill_price - existing.open_price) * closed_qty - commission
                else:
                    pnl = (existing.open_price - fill_price) * closed_qty - commission

                self._current_balance += pnl

                self._positions[existing_pos_id] = PaperPosition(
                    position_id=existing.position_id,
                    symbol=existing.symbol,
                    side=existing.side,
                    quantity=remaining_qty,
                    open_price=existing.open_price,
                    current_price=fill_price,
                    stop_loss=existing.stop_loss,
                    take_profit=existing.take_profit,
                    trailing_distance=existing.trailing_distance,
                    high_water_mark=existing.high_water_mark,
                    low_water_mark=existing.low_water_mark,
                    commission=existing.commission,
                    swap=existing.swap,
                    realized_pnl=existing.realized_pnl + pnl,
                    open_time=existing.open_time,
                )
            elif fill_qty == existing.quantity:
                # Full closure
                closed_qty = fill_qty
                if existing.side == OrderSide.BUY:
                    pnl = (fill_price - existing.open_price) * closed_qty - commission
                else:
                    pnl = (existing.open_price - fill_price) * closed_qty - commission

                self._current_balance += pnl
                self._positions.pop(existing_pos_id, None)
            else:
                # Reversal: close existing and open residual in opposite direction
                closed_qty = existing.quantity
                residual_qty = fill_qty - existing.quantity

                if existing.side == OrderSide.BUY:
                    pnl = (fill_price - existing.open_price) * closed_qty - commission
                else:
                    pnl = (existing.open_price - fill_price) * closed_qty - commission

                self._current_balance += pnl
                self._positions.pop(existing_pos_id, None)

                # Open residual position
                new_pos_id = f"pos_{self._next_position_id}"
                self._next_position_id += 1
                self._positions[new_pos_id] = PaperPosition(
                    position_id=new_pos_id,
                    symbol=symbol,
                    side=order.side,
                    quantity=residual_qty,
                    open_price=fill_price,
                    current_price=fill_price,
                    stop_loss=getattr(order, "stop_loss", None),
                    take_profit=getattr(order, "take_profit", None),
                    trailing_distance=getattr(order, "trailing_distance", None),
                    commission=Decimal(0),
                )

    async def _evaluate_resting_triggers(self, symbol: str, bid: Decimal, ask: Decimal) -> None:
        """Evaluate pending limit/stop orders and position SL/TP/Trailing Stop upon quote arrival."""
        triggered_orders: list[PaperOrder] = []

        async with self._lock:
            # 1. Evaluate pending resting orders
            for paper_id, order in list(self._pending_orders.items()):
                if order.symbol != symbol:
                    continue

                should_trigger = False
                if order.order_type == OrderType.LIMIT and (
                    (order.side == OrderSide.BUY and order.price is not None and ask <= order.price)
                    or (order.side == OrderSide.SELL and order.price is not None and bid >= order.price)
                ) or order.order_type in (OrderType.STOP, OrderType.TRAILING_STOP) and (
                    (order.side == OrderSide.BUY and order.stop_price is not None and ask >= order.stop_price)
                    or (order.side == OrderSide.SELL and order.stop_price is not None and bid <= order.stop_price)
                ):
                    should_trigger = True

                if should_trigger:
                    triggered_orders.append(order)
                    self._pending_orders.pop(paper_id, None)

            # 2. Evaluate position stop loss, take profit, and trailing stops
            for pid, pos in list(self._positions.items()):
                if pos.symbol != symbol:
                    continue

                # Trailing stop high/low water mark update
                if pos.trailing_distance:
                    if pos.side == OrderSide.BUY:
                        if pos.high_water_mark is None or bid > pos.high_water_mark:
                            new_sl = bid - pos.trailing_distance
                            self._positions[pid] = PaperPosition(
                                position_id=pos.position_id,
                                symbol=pos.symbol,
                                side=pos.side,
                                quantity=pos.quantity,
                                open_price=pos.open_price,
                                current_price=bid,
                                stop_loss=max(pos.stop_loss or Decimal(0), new_sl),
                                take_profit=pos.take_profit,
                                trailing_distance=pos.trailing_distance,
                                high_water_mark=bid,
                                low_water_mark=pos.low_water_mark,
                                commission=pos.commission,
                                swap=pos.swap,
                                open_time=pos.open_time,
                            )
                            pos = self._positions[pid]
                    else:
                        if pos.low_water_mark is None or ask < pos.low_water_mark:
                            new_sl = ask + pos.trailing_distance
                            self._positions[pid] = PaperPosition(
                                position_id=pos.position_id,
                                symbol=pos.symbol,
                                side=pos.side,
                                quantity=pos.quantity,
                                open_price=pos.open_price,
                                current_price=ask,
                                stop_loss=min(pos.stop_loss or Decimal(999999), new_sl),
                                take_profit=pos.take_profit,
                                trailing_distance=pos.trailing_distance,
                                high_water_mark=pos.high_water_mark,
                                low_water_mark=ask,
                                commission=pos.commission,
                                swap=pos.swap,
                                open_time=pos.open_time,
                            )
                            pos = self._positions[pid]

                # Check SL / TP breach
                close_needed = False
                exit_price = Decimal(0)

                if pos.side == OrderSide.BUY:
                    if pos.stop_loss is not None and bid <= pos.stop_loss or pos.take_profit is not None and bid >= pos.take_profit:
                        close_needed = True
                        exit_price = bid
                else:
                    if pos.stop_loss is not None and ask >= pos.stop_loss or pos.take_profit is not None and ask <= pos.take_profit:
                        close_needed = True
                        exit_price = ask

                if close_needed:
                    if pos.side == OrderSide.BUY:
                        pnl = (exit_price - pos.open_price) * pos.quantity - pos.commission - pos.swap
                    else:
                        pnl = (pos.open_price - exit_price) * pos.quantity - pos.commission - pos.swap

                    self._current_balance += pnl
                    self._positions.pop(pid, None)

        # Execute fills for triggered resting orders
        for order in triggered_orders:
            domain_order = Order(
                order_id=OrderId(order.domain_order_id),
                decision_id="trigger",
                execution_id="trigger",
                symbol=order.symbol,
                side=order.side,
                order_type=OrderType.MARKET,
                quantity=order.quantity,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                trailing_distance=order.trailing_distance,
            )
            await self._execute_market_order(order, domain_order)
