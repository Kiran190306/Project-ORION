"""Market impact models for backtesting execution simulation.

Simulates the price impact of large orders on the market,
including both temporary and permanent impact components.
Based on Almgren-Chriss and similar institutional models.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class MarketImpactModelConfig:
    """Configuration for the market impact model."""

    temporary_impact_coefficient: float = 0.1
    permanent_impact_coefficient: float = 0.01
    volatility_impact_multiplier: float = 0.5
    liquidity_impact_divider: float = 2.0
    max_impact_bps: float = 100.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MarketImpactModel:
    """Calculates market impact of order execution.

    Implements a simplified Almgren-Chriss market impact model.
    Thread-safe via stateless design.
    """

    def __init__(self, config: MarketImpactModelConfig | None = None) -> None:
        """Initialize market impact model.

        Args:
            config: Market impact configuration. Uses defaults if None.
        """
        self._config = config or MarketImpactModelConfig()

    @property
    def config(self) -> MarketImpactModelConfig:
        """Return the current configuration."""
        return self._config

    def calculate_impact_bps(
        self,
        volume: Decimal,
        average_daily_volume: Decimal,
        volatility_bps: float = 10.0,
        liquidity_score: float = 1.0,
    ) -> float:
        """Calculate market impact in basis points.

        Uses a simplified square-root impact model:
        Impact = c * sigma * (Q / ADV)^0.5

        Args:
            volume: Order volume.
            average_daily_volume: Average daily volume.
            volatility_bps: Daily volatility in bps.
            liquidity_score: Liquidity score (0-1).

        Returns:
            Market impact in basis points.
        """
        cfg = self._config

        if average_daily_volume <= Decimal("0"):
            return 0.0

        participation_rate = float(volume / average_daily_volume)
        if participation_rate <= 0:
            return 0.0

        # Square-root impact model
        sqrt_participation = math.sqrt(participation_rate)
        impact = cfg.permanent_impact_coefficient * volatility_bps * sqrt_participation

        # Temporary impact (larger for illiquid markets)
        if liquidity_score > 0:
            impact *= 1.0 + (cfg.temporary_impact_coefficient / liquidity_score)

        # Volatility adjustment
        impact *= 1.0 + (volatility_bps / 100.0) * cfg.volatility_impact_multiplier

        # Clamp to max
        if impact > cfg.max_impact_bps:
            impact = cfg.max_impact_bps

        return round(impact, 2)

    def calculate_effective_spread(
        self,
        base_spread_pips: float,
        volume: Decimal,
        average_daily_volume: Decimal,
        pip_size: Decimal = Decimal("0.0001"),
    ) -> float:
        """Calculate effective spread including market impact.

        Args:
            base_spread_pips: Current market spread in pips.
            volume: Order volume.
            average_daily_volume: Average daily volume.
            pip_size: Pip value.

        Returns:
            Effective spread in pips.
        """
        impact_bps = self.calculate_impact_bps(volume, average_daily_volume)
        impact_pips = impact_bps / 10000.0 / float(pip_size) if pip_size > 0 else 0
        return base_spread_pips + impact_pips

    def calculate_impact_cost(
        self,
        volume: Decimal,
        price: Decimal,
        average_daily_volume: Decimal,
        volatility_bps: float = 10.0,
        liquidity_score: float = 1.0,
    ) -> Decimal:
        """Calculate the monetary cost of market impact.

        Args:
            volume: Order volume.
            price: Current market price.
            average_daily_volume: Average daily volume.
            volatility_bps: Daily volatility in bps.
            liquidity_score: Liquidity score (0-1).

        Returns:
            Impact cost in quote currency.
        """
        impact_bps = self.calculate_impact_bps(
            volume, average_daily_volume, volatility_bps, liquidity_score
        )
        impact_decimal = Decimal(str(impact_bps / 10000.0))
        notional = volume * price
        impact_cost = notional * impact_decimal
        return impact_cost.quantize(Decimal("0.01"))
