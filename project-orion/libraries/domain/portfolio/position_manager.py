"""Position Manager — single source of truth for all position state.

Supports:
- Open Position
- Close Position
- Partial Close
- Increase Position
- Reduce Position
- Position Merge
- Position Split
- Position History
- O(1) position lookup by ID and by symbol
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.portfolio.exceptions import (
    DuplicatePositionError,
    InvalidPositionStateError,
    PositionNotFoundError,
    PositionSizeError,
)
from libraries.domain.portfolio.models import (
    Position,
    PositionSide,
    PositionStatus,
    PositionSummary,
)


@dataclass(frozen=True, slots=True)
class PositionManagerConfig:
    """Configuration for the PositionManager."""

    generate_position_id: bool = True
    track_history: bool = True
    max_history_per_position: int = 100


class PositionManager:
    """Manages all positions with O(1) lookups.

    Thread-safe via asyncio.Lock.
    Maintains dict indexes for O(1) position_id and symbol lookups.
    All outputs are immutable Position instances.
    """

    def __init__(
        self,
        config: PositionManagerConfig | None = None,
    ) -> None:
        self._config = config or PositionManagerConfig()
        self._lock = asyncio.Lock()
        self._positions: dict[str, Position] = {}  # O(1) by position_id
        self._symbol_index: dict[str, set[str]] = {}  # O(1) symbol -> position_ids
        self._history: dict[str, list[Position]] = {}  # position_id -> history
        self._position_counter: int = 0

    # ─── Properties ──────────────────────────────────────────

    @property
    def config(self) -> PositionManagerConfig:
        return self._config

    @property
    async def open_count(self) -> int:
        """Return count of open positions."""
        async with self._lock:
            return sum(1 for p in self._positions.values() if p.is_active)

    @property
    async def total_count(self) -> int:
        """Return total positions tracked."""
        async with self._lock:
            return len(self._positions)

    # ─── Position CRUD ────────────────────────────────────────

    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: Decimal,
        entry_price: Decimal,
        *,
        position_id: str | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        decision_id: str = "",
        execution_id: str = "",
        strategy: str = "",
        currency: str = "USD",
        broker: str = "",
        leverage: Decimal = Decimal(1),
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        margin_used: Decimal = Decimal(0),
        tags: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Open a new position.

        Args:
            symbol: Trading symbol.
            side: LONG or SHORT.
            quantity: Position size.
            entry_price: Entry price.
            position_id: Optional custom position ID.
            stop_loss: Optional stop loss price.
            take_profit: Optional take profit price.
            decision_id: Decision ID from DecisionEngine.
            execution_id: Execution ID from ExecutionEngine.
            strategy: Strategy name.
            currency: Position currency.
            broker: Broker name.
            leverage: Leverage multiplier.
            commission: Commission charged.
            swap: Swap/rollover.
            fees: Additional fees.
            margin_used: Margin used.
            tags: Position tags.
            metadata: Additional metadata.

        Returns:
            The newly created Position.

        Raises:
            DuplicatePositionError: If position_id already exists.
        """
        pid = position_id
        if pid is None:
            if not self._config.generate_position_id:
                raise ValueError("position_id is required when generate_position_id is False")
            pid = self._next_position_id()
        now = datetime.now(timezone.utc)

        position = Position(
            position_id=pid,
            symbol=symbol,
            side=side,
            status=PositionStatus.OPEN,
            quantity=quantity,
            initial_quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            realized_pnl=Decimal(0),
            unrealized_pnl=Decimal(0),
            commission=commission,
            swap=swap,
            fees=fees,
            margin_used=margin_used,
            leverage=leverage,
            decision_id=decision_id,
            execution_id=execution_id,
            strategy=strategy,
            currency=currency,
            broker=broker,
            open_time=now,
            close_time=None,
            updated_at=now,
            close_reason="",
            tags=tags,
            metadata=metadata or {},
        )

        async with self._lock:
            if pid in self._positions:
                raise DuplicatePositionError(f"Position with id '{pid}' already exists")
            self._positions[pid] = position
            self._add_to_symbol_index(pid, symbol)
            if self._config.track_history:
                self._add_history(pid, position)

        return position

    async def close_position(
        self,
        position_id: str,
        close_price: Decimal,
        close_reason: str = "",
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Close a position completely.

        Args:
            position_id: ID of the position to close.
            close_price: Price at which position is closed.
            close_reason: Reason for closing.
            commission: Commission for this close.
            swap: Swap for this close.
            fees: Fees for this close.
            metadata: Additional metadata.

        Returns:
            Updated closed Position.

        Raises:
            PositionNotFoundError: If position not found.
            InvalidPositionStateError: If position is already closed.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if position.status.is_closed:
                raise InvalidPositionStateError(
                    f"Position '{position_id}' is already closed (status: {position.status.value})"
                )

            realized = self._calculate_realized_pnl(position, close_price)
            total_commission = position.commission + commission
            total_swap = position.swap + swap
            total_fees = position.fees + fees

            now = datetime.now(timezone.utc)
            updated = position.with_update(
                status=PositionStatus.CLOSED,
                quantity=Decimal(0),
                current_price=close_price,
                realized_pnl=realized,
                unrealized_pnl=Decimal(0),
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                close_time=now,
                updated_at=now,
                close_reason=close_reason,
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)

            return updated

    async def partially_close_position(
        self,
        position_id: str,
        close_quantity: Decimal,
        close_price: Decimal,
        close_reason: str = "",
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Partially close a position.

        Args:
            position_id: ID of the position.
            close_quantity: Quantity to close.
            close_price: Price at which the partial close happens.
            close_reason: Reason for closing.
            commission: Commission for this partial close.
            swap: Swap for this partial close.
            fees: Fees for this partial close.
            metadata: Additional metadata.

        Returns:
            Updated partially-closed Position.

        Raises:
            PositionNotFoundError: If position not found.
            PositionSizeError: If close_quantity > position quantity.
            InvalidPositionStateError: If position is already closed.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if position.status.is_closed:
                raise InvalidPositionStateError(f"Position '{position_id}' is already closed")
            if close_quantity <= 0:
                raise PositionSizeError("Close quantity must be positive")
            if close_quantity > position.quantity:
                raise PositionSizeError(
                    f"Close quantity {close_quantity} exceeds position quantity {position.quantity}"
                )

            remaining = position.quantity - close_quantity
            new_status = (
                PositionStatus.CLOSED if remaining == 0 else PositionStatus.PARTIALLY_CLOSED
            )

            # Realized P&L for the closed portion
            realized = self._calculate_realized_pnl_for_quantity(
                position,
                close_quantity,
                close_price,
            )
            total_commission = position.commission + commission
            total_swap = position.swap + swap
            total_fees = position.fees + fees

            # Unrealized P&L for remaining portion
            unrealized = Decimal(0)
            if remaining > 0 and position.current_price:
                if position.is_long:
                    unrealized = (position.current_price - position.entry_price) * remaining
                else:
                    unrealized = (position.entry_price - position.current_price) * remaining

            now = datetime.now(timezone.utc)
            updated = position.with_update(
                status=new_status,
                quantity=remaining,
                current_price=close_price,
                realized_pnl=position.realized_pnl + realized,
                unrealized_pnl=unrealized,
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                close_time=now if new_status == PositionStatus.CLOSED else None,
                updated_at=now,
                close_reason=close_reason if new_status == PositionStatus.CLOSED else "",
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)

            return updated

    async def increase_position(
        self,
        position_id: str,
        additional_quantity: Decimal,
        entry_price: Decimal,
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Increase the size of an existing position (add to position).

        Args:
            position_id: ID of the position.
            additional_quantity: Quantity to add.
            entry_price: Price at which the additional quantity is added.
            commission: Commission for this addition.
            swap: Swap for this addition.
            fees: Fees for this addition.
            metadata: Additional metadata.

        Returns:
            Updated Position with increased size.

        Raises:
            PositionNotFoundError: If position not found.
            InvalidPositionStateError: If position is not active.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if not position.is_active:
                raise InvalidPositionStateError(
                    f"Position '{position_id}' is not active (status: {position.status.value})"
                )

            new_quantity = position.quantity + additional_quantity
            # Weighted average entry price
            new_entry_price = (
                (position.entry_price * position.quantity) + (entry_price * additional_quantity)
            ) / new_quantity

            total_commission = position.commission + commission
            total_swap = position.swap + swap
            total_fees = position.fees + fees

            now = datetime.now(timezone.utc)
            updated = position.with_update(
                quantity=new_quantity,
                initial_quantity=position.initial_quantity + additional_quantity,
                entry_price=new_entry_price,
                current_price=entry_price,
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                updated_at=now,
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)

            return updated

    async def reduce_position(
        self,
        position_id: str,
        reduce_quantity: Decimal,
        close_price: Decimal,
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Reduce the size of an existing position (same as partial close).

        Args:
            position_id: ID of the position.
            reduce_quantity: Quantity to reduce.
            close_price: Price at which reduction happens.
            commission: Commission for this reduction.
            swap: Swap for this reduction.
            fees: Fees for this reduction.
            metadata: Additional metadata.

        Returns:
            Updated Position with reduced size.
        """
        return await self.partially_close_position(
            position_id=position_id,
            close_quantity=reduce_quantity,
            close_price=close_price,
            close_reason="position_reduced",
            commission=commission,
            swap=swap,
            fees=fees,
            metadata=metadata,
        )

    async def merge_positions(
        self,
        position_ids: list[str],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Merge multiple positions into one.

        All positions must be for the same symbol and same side.
        The first position becomes the merged result.

        Args:
            position_ids: List of position IDs to merge.
            metadata: Additional metadata.

        Returns:
            The merged Position.

        Raises:
            PositionNotFoundError: If any position not found.
            InvalidPositionStateError: If positions mismatch.
        """
        async with self._lock:
            if len(position_ids) < 2:
                raise InvalidPositionStateError("At least 2 positions required for merge")

            positions = [self._get_position_or_raise(pid) for pid in position_ids]

            # Validate compatibility
            base = positions[0]
            if not base.is_active:
                raise InvalidPositionStateError(
                    f"Cannot merge: base position '{base.position_id}' is not active"
                )
            for p in positions[1:]:
                if p.symbol != base.symbol:
                    raise InvalidPositionStateError(
                        f"Cannot merge: symbol mismatch ({p.symbol} != {base.symbol})"
                    )
                if p.side != base.side:
                    raise InvalidPositionStateError(
                        f"Cannot merge: side mismatch ({p.side.value} != {base.side.value})"
                    )
                if not p.is_active:
                    raise InvalidPositionStateError(
                        f"Cannot merge: position '{p.position_id}' is not active"
                    )

            # Calculate merged values
            total_quantity = sum((p.quantity for p in positions), Decimal(0))
            total_initial = sum((p.initial_quantity for p in positions), Decimal(0))
            total_cost_basis = sum((p.entry_price * p.quantity for p in positions), Decimal(0))
            avg_price = (
                total_cost_basis / total_quantity if total_quantity > 0 else base.entry_price
            )

            total_realized = sum((p.realized_pnl for p in positions), Decimal(0))
            total_commission = sum((p.commission for p in positions), Decimal(0))
            total_swap = sum((p.swap for p in positions), Decimal(0))
            total_fees = sum((p.fees for p in positions), Decimal(0))
            total_margin = sum((p.margin_used for p in positions), Decimal(0))

            now = datetime.now(timezone.utc)

            # Close all positions except base, update base as merged
            merged = base.with_update(
                quantity=total_quantity,
                initial_quantity=total_initial,
                entry_price=avg_price,
                realized_pnl=total_realized,
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                margin_used=total_margin,
                updated_at=now,
                metadata={**(base.metadata), **(metadata or {})},
            )
            self._positions[base.position_id] = merged

            # Mark other positions as closed
            for p in positions[1:]:
                closed = p.with_update(
                    status=PositionStatus.CLOSED,
                    quantity=Decimal(0),
                    close_time=now,
                    updated_at=now,
                    close_reason="merged",
                )
                self._positions[p.position_id] = closed
                if self._config.track_history:
                    self._add_history(p.position_id, closed)

            if self._config.track_history:
                self._add_history(base.position_id, merged)

            return merged

    async def split_position(
        self,
        position_id: str,
        split_ratios: list[float],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[Position]:
        """Split a position into multiple positions.

        Args:
            position_id: ID of the position to split.
            split_ratios: Ratios for splitting (e.g., [0.5, 0.5] for 2 equal positions).
            metadata: Additional metadata.

        Returns:
            List of resulting positions.

        Raises:
            PositionNotFoundError: If position not found.
            InvalidPositionStateError: If position is not active or ratios mismatch.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if not position.is_active:
                raise InvalidPositionStateError(f"Position '{position_id}' is not active")

            total_ratio = sum(split_ratios)
            if abs(total_ratio - 1.0) > 0.0001:
                raise InvalidPositionStateError(f"Split ratios must sum to 1.0, got {total_ratio}")

            now = datetime.now(timezone.utc)
            results: list[Position] = []

            # Update original position with first split
            first_quantity = (position.quantity * Decimal(str(split_ratios[0]))).quantize(
                Decimal("0.000001")
            )
            first = position.with_update(
                quantity=first_quantity,
                updated_at=now,
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = first
            if self._config.track_history:
                self._add_history(position_id, first)
            results.append(first)

            # Create new positions for remaining splits
            for i, ratio in enumerate(split_ratios[1:], start=1):
                new_id = self._next_position_id()
                split_quantity = (position.quantity * Decimal(str(ratio))).quantize(
                    Decimal("0.000001")
                )
                new_pos = Position(
                    position_id=new_id,
                    symbol=position.symbol,
                    side=position.side,
                    status=PositionStatus.OPEN,
                    quantity=split_quantity,
                    initial_quantity=split_quantity,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    stop_loss=position.stop_loss,
                    take_profit=position.take_profit,
                    realized_pnl=Decimal(0),
                    unrealized_pnl=Decimal(0),
                    commission=Decimal(0),
                    swap=Decimal(0),
                    fees=Decimal(0),
                    margin_used=position.margin_used / len(split_ratios),
                    leverage=position.leverage,
                    decision_id=position.decision_id,
                    execution_id=position.execution_id,
                    strategy=position.strategy,
                    currency=position.currency,
                    broker=position.broker,
                    open_time=now,
                    close_time=None,
                    updated_at=now,
                    close_reason="",
                    tags=position.tags,
                    metadata={**(position.metadata), **(metadata or {})},
                )
                self._positions[new_id] = new_pos
                self._add_to_symbol_index(new_id, position.symbol)
                if self._config.track_history:
                    self._add_history(new_id, new_pos)
                results.append(new_pos)

            return results

    async def liquidate_position(
        self,
        position_id: str,
        close_price: Decimal,
        reason: str = "liquidated",
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Force-liquidate a position (e.g., due to margin call).

        Args:
            position_id: ID of the position.
            close_price: Liquidation price.
            reason: Reason for liquidation.
            commission: Commission.
            swap: Swap.
            fees: Fees.
            metadata: Additional metadata.

        Returns:
            Liquidated Position.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if position.status.is_closed:
                raise InvalidPositionStateError(f"Position '{position_id}' is already closed")

            realized = self._calculate_realized_pnl(position, close_price)
            total_commission = position.commission + commission
            total_swap = position.swap + swap
            total_fees = position.fees + fees

            now = datetime.now(timezone.utc)
            updated = position.with_update(
                status=PositionStatus.LIQUIDATED,
                quantity=Decimal(0),
                current_price=close_price,
                realized_pnl=realized,
                unrealized_pnl=Decimal(0),
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                close_time=now,
                updated_at=now,
                close_reason=reason,
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)

            return updated

    async def forced_close_position(
        self,
        position_id: str,
        close_price: Decimal,
        reason: str = "forced_close",
        *,
        commission: Decimal = Decimal(0),
        swap: Decimal = Decimal(0),
        fees: Decimal = Decimal(0),
        metadata: dict[str, Any] | None = None,
    ) -> Position:
        """Force-close a position (e.g., due to risk policy violation).

        Args:
            position_id: ID of the position.
            close_price: Close price.
            reason: Reason for forced close.
            commission: Commission.
            swap: Swap.
            fees: Fees.
            metadata: Additional metadata.

        Returns:
            Force-closed Position.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if position.status.is_closed:
                raise InvalidPositionStateError(f"Position '{position_id}' is already closed")

            realized = self._calculate_realized_pnl(position, close_price)
            total_commission = position.commission + commission
            total_swap = position.swap + swap
            total_fees = position.fees + fees

            now = datetime.now(timezone.utc)
            updated = position.with_update(
                status=PositionStatus.FORCED_CLOSE,
                quantity=Decimal(0),
                current_price=close_price,
                realized_pnl=realized,
                unrealized_pnl=Decimal(0),
                commission=total_commission,
                swap=total_swap,
                fees=total_fees,
                close_time=now,
                updated_at=now,
                close_reason=reason,
                metadata={**(position.metadata), **(metadata or {})},
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)

            return updated

    # ─── Query Methods ───────────────────────────────────────

    async def get_position(self, position_id: str) -> Position | None:
        """Get a position by ID. O(1).

        Args:
            position_id: Position ID.

        Returns:
            Position if found, None otherwise.
        """
        async with self._lock:
            return self._positions.get(position_id)

    async def get_position_or_raise(self, position_id: str) -> Position:
        """Get a position by ID, raising if not found. O(1).

        Args:
            position_id: Position ID.

        Returns:
            Position.

        Raises:
            PositionNotFoundError: If not found.
        """
        async with self._lock:
            return self._get_position_or_raise(position_id)

    async def get_positions_by_symbol(self, symbol: str) -> list[Position]:
        """Get all positions for a symbol. O(1) index lookup.

        Args:
            symbol: Trading symbol.

        Returns:
            List of positions.
        """
        async with self._lock:
            position_ids = self._symbol_index.get(symbol, set())
            return [self._positions[pid] for pid in position_ids if pid in self._positions]

    async def get_all_positions(self) -> list[Position]:
        """Get all tracked positions.

        Returns:
            List of all positions.
        """
        async with self._lock:
            return list(self._positions.values())

    async def get_open_positions(self) -> list[Position]:
        """Get all currently open positions.

        Returns:
            List of open positions.
        """
        async with self._lock:
            return [p for p in self._positions.values() if p.is_active]

    async def get_closed_positions(self) -> list[Position]:
        """Get all closed positions.

        Returns:
            List of closed positions.
        """
        async with self._lock:
            return [p for p in self._positions.values() if p.status.is_closed]

    async def get_position_summary(self, symbol: str) -> PositionSummary:
        """Get aggregated summary for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            PositionSummary with aggregated metrics.
        """
        async with self._lock:
            positions = [
                self._positions[pid]
                for pid in self._symbol_index.get(symbol, set())
                if pid in self._positions
            ]
            active = [p for p in positions if p.is_active]

            total_long_qty = sum((p.quantity for p in active if p.is_long), Decimal(0))
            total_short_qty = sum((p.quantity for p in active if p.is_short), Decimal(0))

            long_positions = [p for p in active if p.is_long]
            short_positions = [p for p in active if p.is_short]

            avg_long = (
                sum((p.entry_price * p.quantity for p in long_positions), Decimal(0)) / total_long_qty
                if total_long_qty > 0
                else Decimal(0)
            )
            avg_short = (
                sum((p.entry_price * p.quantity for p in short_positions), Decimal(0)) / total_short_qty
                if total_short_qty > 0
                else Decimal(0)
            )

            return PositionSummary(
                symbol=symbol,
                total_long_quantity=total_long_qty,
                total_short_quantity=total_short_qty,
                net_quantity=total_long_qty - total_short_qty,
                avg_long_price=avg_long,
                avg_short_price=avg_short,
                unrealized_pnl=sum((p.unrealized_pnl for p in active), Decimal(0)),
                realized_pnl=sum((p.realized_pnl for p in positions), Decimal(0)),
                position_count=len(positions),
                active_count=len(active),
            )

    async def get_position_history(self, position_id: str) -> list[Position]:
        """Get the modification history for a position.

        Args:
            position_id: Position ID.

        Returns:
            List of historical Position states (oldest first).
        """
        async with self._lock:
            if position_id not in self._positions:
                raise PositionNotFoundError(f"Position '{position_id}' not found")
            history = self._history.get(position_id, [])
            return list(history)

    async def position_exists(self, position_id: str) -> bool:
        """Check if a position exists. O(1).

        Args:
            position_id: Position ID.

        Returns:
            True if position exists.
        """
        async with self._lock:
            return position_id in self._positions

    async def get_symbols(self) -> list[str]:
        """Get all symbols with open positions.

        Returns:
            List of symbols.
        """
        async with self._lock:
            return list(self._symbol_index.keys())

    # ─── Update Methods ──────────────────────────────────────

    async def update_position_price(
        self,
        position_id: str,
        current_price: Decimal,
    ) -> Position:
        """Update the current market price for a position (for unrealized P&L).

        Args:
            position_id: Position ID.
            current_price: Current market price.

        Returns:
            Updated Position.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if not position.is_active:
                return position

            # Calculate unrealized P&L
            if position.is_long:
                unrealized = (current_price - position.entry_price) * position.quantity
            else:
                unrealized = (position.entry_price - current_price) * position.quantity

            updated = position.with_update(
                current_price=current_price,
                unrealized_pnl=unrealized,
                updated_at=datetime.now(timezone.utc),
            )
            self._positions[position_id] = updated
            return updated

    async def update_position_stop_loss(
        self,
        position_id: str,
        stop_loss: Decimal,
    ) -> Position:
        """Update the stop loss for a position.

        Args:
            position_id: Position ID.
            stop_loss: New stop loss price.

        Returns:
            Updated Position.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if not position.is_active:
                raise InvalidPositionStateError(f"Position '{position_id}' is not active")
            updated = position.with_update(
                stop_loss=stop_loss,
                updated_at=datetime.now(timezone.utc),
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)
            return updated

    async def update_position_take_profit(
        self,
        position_id: str,
        take_profit: Decimal,
    ) -> Position:
        """Update the take profit for a position.

        Args:
            position_id: Position ID.
            take_profit: New take profit price.

        Returns:
            Updated Position.
        """
        async with self._lock:
            position = self._get_position_or_raise(position_id)
            if not position.is_active:
                raise InvalidPositionStateError(f"Position '{position_id}' is not active")
            updated = position.with_update(
                take_profit=take_profit,
                updated_at=datetime.now(timezone.utc),
            )
            self._positions[position_id] = updated
            if self._config.track_history:
                self._add_history(position_id, updated)
            return updated

    # ─── Internal Helpers ────────────────────────────────────

    def _get_position_or_raise(self, position_id: str) -> Position:
        """Internal: get position or raise PositionNotFoundError."""
        position = self._positions.get(position_id)
        if position is None:
            raise PositionNotFoundError(f"Position '{position_id}' not found")
        return position

    def _add_to_symbol_index(self, position_id: str, symbol: str) -> None:
        """Add position_id to symbol index."""
        if symbol not in self._symbol_index:
            self._symbol_index[symbol] = set()
        self._symbol_index[symbol].add(position_id)

    def _add_history(self, position_id: str, position: Position) -> None:
        """Add a position state to its history."""
        if position_id not in self._history:
            self._history[position_id] = []
        self._history[position_id].append(position)
        if len(self._history[position_id]) > self._config.max_history_per_position:
            self._history[position_id] = self._history[position_id][
                -self._config.max_history_per_position :
            ]

    def _next_position_id(self) -> str:
        """Generate a unique position ID."""
        self._position_counter += 1
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"POS-{ts}-{self._position_counter:04d}"

    @staticmethod
    def _calculate_realized_pnl(position: Position, close_price: Decimal) -> Decimal:
        """Calculate realized P&L for fully closing a position."""
        if position.is_long:
            return (close_price - position.entry_price) * position.quantity
        else:
            return (position.entry_price - close_price) * position.quantity

    @staticmethod
    def _calculate_realized_pnl_for_quantity(
        position: Position,
        close_quantity: Decimal,
        close_price: Decimal,
    ) -> Decimal:
        """Calculate realized P&L for a specific quantity."""
        if position.is_long:
            return (close_price - position.entry_price) * close_quantity
        else:
            return (position.entry_price - close_price) * close_quantity

    # ─── Bulk Operations ─────────────────────────────────────

    async def clear_all(self) -> None:
        """Clear all positions (for testing)."""
        async with self._lock:
            self._positions.clear()
            self._symbol_index.clear()
            self._history.clear()
            self._position_counter = 0
