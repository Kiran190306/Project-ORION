"""Swap (overnight financing) models for backtesting.

Calculates swap/overnight interest charges for positions held past
the daily rollover time. Supports both long and short swap rates
with optional tiered structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class SwapModelConfig:
    """Configuration for the swap model."""

    long_swap_rate: Decimal = Decimal("-2.0")  # Default -2 pips per lot per day
    short_swap_rate: Decimal = Decimal("-1.5")  # Default -1.5 pips per lot per day
    triple_swap_day: int = 3  # Wednesday (3 = ISO weekday)
    pip_size: Decimal = Decimal("0.0001")
    currency: str = "USD"
    rollover_time: str = "00:00:00"  # Server rollover time
    metadata: dict[str, Any] = field(default_factory=dict)


class SwapModel:
    """Calculates swap/overnight financing charges.

    Thread-safe via stateless design — all state is in config.
    """

    def __init__(self, config: SwapModelConfig | None = None) -> None:
        """Initialize swap model.

        Args:
            config: Swap configuration. Uses defaults if None.
        """
        self._config = config or SwapModelConfig()

    @property
    def config(self) -> SwapModelConfig:
        """Return the current configuration."""
        return self._config

    def calculate(
        self,
        volume: Decimal,
        side: str,
        position_value: Decimal,
        holding_days: int = 1,
        timestamp: datetime | None = None,
    ) -> Decimal:
        """Calculate swap charge for holding a position.

        Args:
            volume: Position volume in lots.
            side: 'long' or 'short'.
            position_value: Current position value in quote currency.
            holding_days: Number of days held (default 1).
            timestamp: Current timestamp (for triple swap calculation).

        Returns:
            Swap charge amount in account currency.
        """
        cfg = self._config

        rate = cfg.long_swap_rate if side.lower() == "long" else cfg.short_swap_rate

        # Check for triple swap
        ts = timestamp or datetime.now(timezone.utc)
        if ts.isoweekday() == cfg.triple_swap_day:
            holding_days *= 3

        # Calculate swap: rate * volume * days
        swap_pips = rate * volume * Decimal(str(holding_days))
        swap_amount = swap_pips * cfg.pip_size

        return swap_amount.quantize(Decimal("0.01"))

    def calculate_long_swap(
        self,
        volume: Decimal,
        position_value: Decimal,
        holding_days: int = 1,
    ) -> Decimal:
        """Calculate swap for a long position.

        Args:
            volume: Position volume.
            position_value: Position market value.
            holding_days: Days held.

        Returns:
            Swap amount.
        """
        return self.calculate(volume, "long", position_value, holding_days)

    def calculate_short_swap(
        self,
        volume: Decimal,
        position_value: Decimal,
        holding_days: int = 1,
    ) -> Decimal:
        """Calculate swap for a short position.

        Args:
            volume: Position volume.
            position_value: Position market value.
            holding_days: Days held.

        Returns:
            Swap amount.
        """
        return self.calculate(volume, "short", position_value, holding_days)
