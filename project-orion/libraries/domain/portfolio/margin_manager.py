"""Margin Manager — calculates margin requirements and utilization.

Supports:
- Required Margin
- Used Margin
- Free Margin
- Margin Utilization
- Margin Call Threshold
- Stop Out Threshold
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from libraries.domain.portfolio.models import MarginCallThresholds


@dataclass(frozen=True, slots=True)
class MarginSnapshot:
    """Immutable snapshot of margin state."""

    required_margin: Decimal = Decimal(0)
    used_margin: Decimal = Decimal(0)
    free_margin: Decimal = Decimal(0)
    equity: Decimal = Decimal(0)
    margin_level: float = 0.0  # equity / used_margin * 100
    margin_utilization_pct: float = 0.0
    margin_call_active: bool = False
    stop_out_active: bool = False
    margin_call_threshold: float = 100.0
    stop_out_threshold: float = 50.0
    currency: str = "USD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_healthy(self) -> bool:
        """Margin is healthy if level > 200%."""
        return self.margin_level > 200.0

    @property
    def is_warning(self) -> bool:
        """Margin warning if level between 100% and 200%."""
        return 100.0 < self.margin_level <= 200.0

    @property
    def is_critical(self) -> bool:
        """Margin is critical if level <= 100%."""
        return self.margin_level <= 100.0


class MarginManager:
    """Manages margin calculations.

    Thread-safe via asyncio.Lock.
    Supports margin requirement calculation per position.
    """

    def __init__(
        self,
        thresholds: MarginCallThresholds | None = None,
        currency: str = "USD",
    ) -> None:
        self._lock = asyncio.Lock()
        self._thresholds = thresholds or MarginCallThresholds()
        self._currency = currency
        self._position_margins: dict[str, Decimal] = {}  # position_id -> margin

    @property
    def thresholds(self) -> MarginCallThresholds:
        return self._thresholds

    async def calculate_required_margin(
        self,
        notional_value: Decimal,
        leverage: Decimal = Decimal(100),
        margin_rate: Decimal = Decimal("0.01"),
    ) -> Decimal:
        """Calculate required margin for a position.

        required_margin = notional_value * margin_rate / leverage

        Args:
            notional_value: Position notional value.
            leverage: Account leverage.
            margin_rate: Margin requirement rate (default 1%).

        Returns:
            Required margin amount.
        """
        return (notional_value * margin_rate) / max(leverage, Decimal(1))

    async def get_required_margin(self) -> Decimal:
        """Return total required margin across all positions."""
        async with self._lock:
            return sum(self._position_margins.values(), Decimal(0))

    async def get_used_margin(self) -> Decimal:
        """Return total used margin."""
        async with self._lock:
            return sum(self._position_margins.values(), Decimal(0))

    async def register_position_margin(
        self,
        position_id: str,
        margin: Decimal,
    ) -> None:
        """Register margin requirement for a position.

        Args:
            position_id: Position ID.
            margin: Margin amount required.
        """
        async with self._lock:
            if margin < 0:
                raise ValueError("Margin must be non-negative")
            self._position_margins[position_id] = margin

    async def unregister_position_margin(self, position_id: str) -> None:
        """Remove margin requirement for a position.

        Args:
            position_id: Position ID.
        """
        async with self._lock:
            self._position_margins.pop(position_id, None)

    async def update_position_margin(
        self,
        position_id: str,
        margin: Decimal,
    ) -> None:
        """Update margin requirement for a position.

        Args:
            position_id: Position ID.
            margin: New margin amount.
        """
        async with self._lock:
            if margin < 0:
                raise ValueError("Margin must be non-negative")
            self._position_margins[position_id] = margin

    async def get_free_margin(
        self,
        equity: Decimal,
    ) -> Decimal:
        """Calculate free margin.

        free_margin = equity - used_margin

        Args:
            equity: Current equity.

        Returns:
            Free margin amount.
        """
        async with self._lock:
            used = sum(self._position_margins.values(), Decimal(0))
            return max(Decimal(0), equity - used)

    async def get_margin_level(
        self,
        equity: Decimal,
    ) -> float:
        """Calculate margin level percentage.

        margin_level = equity / used_margin * 100

        Args:
            equity: Current equity.

        Returns:
            Margin level as percentage.
        """
        async with self._lock:
            used = sum(self._position_margins.values(), Decimal(0))
            if used == 0:
                return float("inf")
            return float(equity / used * 100)

    async def get_margin_utilization(
        self,
        equity: Decimal,
    ) -> float:
        """Calculate margin utilization as percentage of equity.

        Args:
            equity: Current equity.

        Returns:
            Margin utilization percentage.
        """
        async with self._lock:
            used = sum(self._position_margins.values(), Decimal(0))
            if equity == 0:
                return 0.0
            return float(used / equity * 100)

    async def check_margin_call(self, equity: Decimal) -> bool:
        """Check if margin call threshold is breached.

        Args:
            equity: Current equity.

        Returns:
            True if margin level <= margin_call_threshold.
        """
        level = await self.get_margin_level(equity)
        return level <= self._thresholds.margin_call_level

    async def check_stop_out(self, equity: Decimal) -> bool:
        """Check if stop-out threshold is breached.

        Args:
            equity: Current equity.

        Returns:
            True if margin level <= stop_out_threshold.
        """
        level = await self.get_margin_level(equity)
        return level <= self._thresholds.stop_out_level

    async def check_warning(self, equity: Decimal) -> bool:
        """Check if warning threshold is breached.

        Args:
            equity: Current equity.

        Returns:
            True if margin level <= warning_level.
        """
        level = await self.get_margin_level(equity)
        return level <= self._thresholds.warning_level

    async def get_snapshot(
        self,
        equity: Decimal,
    ) -> MarginSnapshot:
        """Get current margin snapshot.

        Args:
            equity: Current equity.

        Returns:
            MarginSnapshot.
        """
        async with self._lock:
            used = sum(self._position_margins.values(), Decimal(0))
            free = max(Decimal(0), equity - used)
            level = float(equity / used * 100) if used > 0 else float("inf")
            utilization = float(used / equity * 100) if equity > 0 else 0.0

            return MarginSnapshot(
                required_margin=used,
                used_margin=used,
                free_margin=free,
                equity=equity,
                margin_level=round(level, 2),
                margin_utilization_pct=round(utilization, 2),
                margin_call_active=level <= self._thresholds.margin_call_level,
                stop_out_active=level <= self._thresholds.stop_out_level,
                margin_call_threshold=self._thresholds.margin_call_level,
                stop_out_threshold=self._thresholds.stop_out_level,
                currency=self._currency,
            )

    async def reset(self) -> None:
        """Reset margin manager (for testing)."""
        async with self._lock:
            self._position_margins.clear()
