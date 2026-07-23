"""Slippage models for backtesting execution simulation.

Provides configurable slippage calculation models including:
- Fixed slippage (bps-based)
- Volatility-adjusted slippage
- Liquidity-based slippage
- Spread-based slippage
- Market impact component
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class SlippageType(StrEnum):
    """Slippage calculation methods."""

    FIXED = "fixed"
    RELATIVE = "relative"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    LIQUIDITY_BASED = "liquidity_based"
    SPREAD_BASED = "spread_based"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class SlippageModelConfig:
    """Configuration for the slippage model."""

    slippage_type: SlippageType = SlippageType.FIXED
    fixed_bps: float = 1.0  # Default 1 bps slippage
    volatility_multiplier: float = 1.5
    liquidity_base_bps: float = 0.5
    spread_multiplier: float = 0.25
    max_slippage_bps: float = 50.0  # Max 50 bps
    min_slippage_bps: float = 0.0
    random_seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SlippageModel:
    """Calculates slippage for simulated order execution.

    Thread-safe via stateless design.
    """

    def __init__(self, config: SlippageModelConfig | None = None) -> None:
        """Initialize slippage model.

        Args:
            config: Slippage configuration. Uses defaults if None.
        """
        self._config = config or SlippageModelConfig()

    @property
    def config(self) -> SlippageModelConfig:
        """Return the current configuration."""
        return self._config

    def calculate(
        self,
        volume: Decimal,
        spread_pips: float = 0.0,
        volatility: float = 0.0,
        liquidity_score: float = 1.0,
        is_market_order: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> float:
        """Calculate slippage in bps.

        Args:
            volume: Order volume in lots.
            spread_pips: Current spread in pips.
            volatility: Current volatility measure.
            liquidity_score: Liquidity score (0-1).
            is_market_order: True for market orders.
            metadata: Optional additional parameters.

        Returns:
            Slippage in basis points.
        """
        cfg = self._config

        if cfg.slippage_type == SlippageType.NONE:
            return 0.0

        slippage = 0.0

        if cfg.slippage_type == SlippageType.FIXED:
            slippage = cfg.fixed_bps

        elif cfg.slippage_type == SlippageType.RELATIVE:
            slippage = cfg.fixed_bps * (1.0 + volatility * cfg.volatility_multiplier)

        elif cfg.slippage_type == SlippageType.VOLATILITY_ADJUSTED:
            slippage = cfg.fixed_bps * (1.0 + volatility * cfg.volatility_multiplier)

        elif cfg.slippage_type == SlippageType.LIQUIDITY_BASED:
            if liquidity_score > 0:
                slippage = cfg.liquidity_base_bps / liquidity_score
            else:
                slippage = cfg.liquidity_base_bps * 10.0

        elif cfg.slippage_type == SlippageType.SPREAD_BASED:
            slippage = spread_pips * cfg.spread_multiplier

        else:
            slippage = cfg.fixed_bps

        # Market orders have more slippage than limit orders
        if not is_market_order:
            slippage *= 0.5

        # Volume adjustment (larger orders = more slippage)
        if volume > Decimal("10"):
            slippage *= 1.0 + (float(volume) - 10.0) * 0.05

        # Clamp to min/max
        if slippage < cfg.min_slippage_bps:
            slippage = cfg.min_slippage_bps
        if slippage > cfg.max_slippage_bps:
            slippage = cfg.max_slippage_bps

        return round(slippage, 2)

    def calculate_slippage_price(
        self,
        price: Decimal,
        side: str,
        volume: Decimal,
        spread_pips: float = 0.0,
        volatility: float = 0.0,
        liquidity_score: float = 1.0,
        pip_size: Decimal = Decimal("0.0001"),
    ) -> Decimal:
        """Calculate the adjusted price after slippage.

        Args:
            price: Expected execution price.
            side: 'buy' or 'sell'.
            volume: Order volume.
            spread_pips: Current spread in pips.
            volatility: Current volatility.
            liquidity_score: Liquidity score (0-1).
            pip_size: Pip value for the instrument.

        Returns:
            Price adjusted for slippage.
        """
        slippage_bps = self.calculate(volume, spread_pips, volatility, liquidity_score)
        slippage_decimal = slippage_bps / 10000.0  # Convert bps to decimal

        if side.lower() == "buy":
            # Buy slippage is adverse (price moves up)
            return price * (Decimal("1") + Decimal(str(slippage_decimal)))
        else:
            # Sell slippage is adverse (price moves down)
            return price * (Decimal("1") - Decimal(str(slippage_decimal)))
