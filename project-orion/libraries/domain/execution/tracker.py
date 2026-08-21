"""Order Tracker.

Central registry for tracking all active orders through their lifecycle.
Provides lookup by order ID, decision ID, symbol, and status.
"""

from __future__ import annotations

import asyncio

from libraries.domain.execution.exceptions import OrderNotFoundError
from libraries.domain.execution.lifecycle import OrderLifecycleTracker
from libraries.domain.execution.models import Order, OrderStatus


class OrderTracker:
    """Tracks all active orders.

    Thread-safe via asyncio.Lock. Supports efficient lookup
    by order ID, decision ID, symbol, and status.
    """

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._lifecycles: dict[str, OrderLifecycleTracker] = {}
        self._decision_map: dict[str, str] = {}  # decision_id -> order_id
        self._symbol_map: dict[str, set[str]] = {}  # symbol -> {order_id, ...}
        self._lock = asyncio.Lock()

    async def register(self, order: Order, lifecycle: OrderLifecycleTracker) -> None:
        """Register an order for tracking.

        Args:
            order: The order to track.
            lifecycle: The lifecycle tracker for the order.
        """
        async with self._lock:
            order_id = str(order.order_id)
            self._orders[order_id] = order
            self._lifecycles[order_id] = lifecycle
            self._decision_map[order.decision_id] = order_id

            if order.symbol not in self._symbol_map:
                self._symbol_map[order.symbol] = set()
            self._symbol_map[order.symbol].add(order_id)

    async def get_order(self, order_id: str) -> Order:
        """Get an order by ID.

        Args:
            order_id: Order identifier.

        Returns:
            The Order.

        Raises:
            OrderNotFoundError: If not found.
        """
        async with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(f"Order {order_id} not found")
            return order

    async def get_lifecycle(self, order_id: str) -> OrderLifecycleTracker:
        """Get lifecycle tracker for an order.

        Args:
            order_id: Order identifier.

        Returns:
            OrderLifecycleTracker.

        Raises:
            OrderNotFoundError: If not found.
        """
        async with self._lock:
            lifecycle = self._lifecycles.get(order_id)
            if lifecycle is None:
                raise OrderNotFoundError(f"Lifecycle for order {order_id} not found")
            return lifecycle

    async def get_by_decision(self, decision_id: str) -> Order:
        """Get an order by decision ID.

        Args:
            decision_id: Decision engine decision ID.

        Returns:
            The Order.

        Raises:
            OrderNotFoundError: If not found.
        """
        async with self._lock:
            order_id = self._decision_map.get(decision_id)
            if order_id is None:
                raise OrderNotFoundError(f"No order found for decision {decision_id}")
            return self._orders[order_id]

    async def get_by_symbol(
        self,
        symbol: str,
        status: OrderStatus | None = None,
    ) -> list[Order]:
        """Get orders by symbol, optionally filtered by status.

        Args:
            symbol: Trading symbol.
            status: Optional status filter.

        Returns:
            List of matching orders.
        """
        async with self._lock:
            order_ids = self._symbol_map.get(symbol, set())
            orders = [self._orders[oid] for oid in order_ids if oid in self._orders]
            if status is not None:
                orders = [o for o in orders if o.status == status]
            return orders

    async def get_active_orders(self) -> list[Order]:
        """Get all active (non-terminal) orders.

        Returns:
            List of active orders.
        """
        async with self._lock:
            active = []
            for order_id, lifecycle in self._lifecycles.items():
                if await lifecycle.is_active():
                    order = self._orders.get(order_id)
                    if order is not None:
                        active.append(order)
            return active

    async def get_by_status(self, status: OrderStatus) -> list[Order]:
        """Get all orders with a specific status.

        Args:
            status: Order status to filter by.

        Returns:
            List of matching orders.
        """
        async with self._lock:
            return [o for o in self._orders.values() if o.status == status]

    async def update_order(self, order: Order) -> None:
        """Update a tracked order.

        Args:
            order: Updated order instance.

        Raises:
            OrderNotFoundError: If not found.
        """
        async with self._lock:
            order_id = str(order.order_id)
            if order_id not in self._orders:
                raise OrderNotFoundError(f"Order {order_id} not found")
            self._orders[order_id] = order

    async def remove(self, order_id: str) -> None:
        """Remove an order from tracking.

        Args:
            order_id: Order identifier.
        """
        async with self._lock:
            order = self._orders.pop(order_id, None)
            self._lifecycles.pop(order_id, None)
            if order is not None:
                self._decision_map.pop(order.decision_id, None)
                symbol_orders = self._symbol_map.get(order.symbol, set())
                symbol_orders.discard(order_id)
                if not symbol_orders:
                    self._symbol_map.pop(order.symbol, None)

    async def order_count(self) -> int:
        """Return total number of tracked orders."""
        async with self._lock:
            return len(self._orders)

    async def active_count(self) -> int:
        """Return number of active orders."""
        async with self._lock:
            active = 0
            for lifecycle in self._lifecycles.values():
                if await lifecycle.is_active():
                    active += 1
            return active

    async def clear(self) -> None:
        """Clear all tracked orders."""
        async with self._lock:
            self._orders.clear()
            self._lifecycles.clear()
            self._decision_map.clear()
            self._symbol_map.clear()
