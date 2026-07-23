"""Commission models for backtesting simulation.

Provides configurable commission structures including:
- Fixed per-lot commission
- Tiered commission based on volume
- Percentage-based commission
- Zero commission (for ECN/RAW accounts)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class CommissionType(StrEnum):
    """Commission calculation methods."""

    FIXED_PER_LOT = "fixed_per_lot"
    FIXED_PER_TRADE = "fixed_per_trade"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    PER_UNIT = "per_unit"
    ZERO = "zero"


@dataclass(frozen=True, slots=True)
class CommissionTier:
    """A single tier in a tiered commission structure."""

    min_volume: Decimal
    max_volume: Decimal
    rate: Decimal


@dataclass(frozen=True, slots=True)
class CommissionModelConfig:
    """Configuration for the commission model."""

    commission_type: CommissionType = CommissionType.FIXED_PER_LOT
    base_rate: Decimal = Decimal("7.0")  # Default $7 per lot
    currency: str = "USD"
    per_unit_rate: Decimal = Decimal("0")
    percentage_rate: Decimal = Decimal("0")
    minimum_commission: Decimal = Decimal("0")
    maximum_commission: Decimal = Decimal("0")  # 0 = no max
    tiers: tuple[CommissionTier, ...] = ()
    discount_rate: Decimal = Decimal("0")  # Volume discount %
    metadata: dict[str, Any] = field(default_factory=dict)


class CommissionModel:
    """Calculates commission for simulated trades.

    Supports multiple commission structures common in institutional FX trading.
    Thread-safe via stateless design — all state is in the config.
    """

    def __init__(self, config: CommissionModelConfig | None = None) -> None:
        """Initialize commission model.

        Args:
            config: Commission configuration. Uses defaults if None.
        """
        self._config = config or CommissionModelConfig()

    @property
    def config(self) -> CommissionModelConfig:
        """Return the current configuration."""
        return self._config

    def calculate(
        self,
        volume: Decimal,
        price: Decimal,
        currency: str = "USD",
        metadata: dict[str, Any] | None = None,
    ) -> Decimal:
        """Calculate commission for a trade.

        Args:
            volume: Trade volume in lots.
            price: Execution price.
            currency: Account currency.
            metadata: Optional additional parameters.

        Returns:
            Calculated commission amount.
        """
        cfg = self._config

        if cfg.commission_type == CommissionType.ZERO:
            return Decimal("0")

        if cfg.commission_type == CommissionType.FIXED_PER_LOT:
            commission = cfg.base_rate * volume

        elif cfg.commission_type == CommissionType.FIXED_PER_TRADE:
            commission = cfg.base_rate

        elif cfg.commission_type == CommissionType.PERCENTAGE:
            notional = volume * price
            commission = notional * (cfg.percentage_rate / Decimal("100"))

        elif cfg.commission_type == CommissionType.PER_UNIT:
            commission = cfg.per_unit_rate * volume

        elif cfg.commission_type == CommissionType.TIERED:
            commission = self._calculate_tiered(volume)

        else:
            commission = Decimal("0")

        # Apply discount
        if cfg.discount_rate > Decimal("0"):
            commission = commission * (Decimal("1") - cfg.discount_rate / Decimal("100"))

        # Apply min/max
        if cfg.minimum_commission > Decimal("0") and commission < cfg.minimum_commission:
            commission = cfg.minimum_commission
        if cfg.maximum_commission > Decimal("0") and commission > cfg.maximum_commission:
            commission = cfg.maximum_commission

        return commission

    def _calculate_tiered(self, volume: Decimal) -> Decimal:
        """Calculate commission using tiered structure.

        Args:
            volume: Trade volume in lots.

        Returns:
            Commission based on applicable tier.
        """
        cfg = self._config
        if not cfg.tiers:
            return cfg.base_rate * volume

        for tier in cfg.tiers:
            if tier.min_volume <= volume <= tier.max_volume:
                return tier.rate * volume

        # If volume exceeds all tiers, use last tier
        last_tier = cfg.tiers[-1]
        return last_tier.rate * volume

    def calculate_for_order(
        self,
        volume: Decimal,
        price: Decimal,
        is_open: bool = True,
        currency: str = "USD",
    ) -> Decimal:
        """Calculate commission for an order (open or close).

        Args:
            volume: Trade volume.
            price: Execution price.
            is_open: True for opening, False for closing.
            currency: Account currency.

        Returns:
            Commission amount.
        """
        commission = self.calculate(volume, price, currency)
        # Round to 2 decimal places
        return commission.quantize(Decimal("0.01"))
