"""Spread Model — simulates bid/ask spread during backtesting.

Supports:
- Fixed spread
- Variable spread (based on volatility)
- Spread spikes (for scenario testing)

All randomness uses configurable seeds for deterministic execution.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

from libraries.domain.backtesting.models import SpreadConfig

SpreadModelConfig = SpreadConfig


@dataclass
class SpreadModel:
    """Simulates bid/ask spread during backtesting.

    Thread-safe via per-instance Random state.
    """

    config: SpreadConfig = field(default_factory=SpreadConfig)
    _random: random.Random = field(default_factory=lambda: random.Random(42))

    def __post_init__(self) -> None:
        self._random = random.Random(42)

    def set_seed(self, seed: int | None) -> None:
        """Set random seed for deterministic simulation.

        Args:
            seed: Random seed.
        """
        self._random = random.Random(seed) if seed is not None else random.Random()

    async def calculate_spread_pips(
        self,
        volatility: float = 0.0,
        is_high_impact_news: bool = False,
        scenario_multiplier: float = 1.0,
    ) -> float:
        """Calculate spread in pips for current conditions.

        Args:
            volatility: Current volatility as fraction (0.0 - 1.0).
            is_high_impact_news: Whether high-impact news is active.
            scenario_multiplier: Scenario intensity multiplier.

        Returns:
            Spread in pips.
        """
        if self.config.type == "fixed":
            base_spread = self.config.value_pips
        elif self.config.type == "variable":
            variable = self.config.variable_factor * volatility
            base_spread = self.config.value_pips + variable
        else:
            base_spread = self.config.value_pips

        # News multiplier
        if is_high_impact_news:
            base_spread *= 3.0

        # Apply scenario multiplier
        base_spread *= scenario_multiplier

        # Random noise (small)
        noise = self._random.uniform(-0.1, 0.1) * base_spread
        spread = base_spread + noise

        # Clamp
        spread = max(spread, self.config.min_pips)
        spread = min(spread, self.config.max_pips)

        return round(spread, 1)

    async def apply_spread(
        self,
        mid_price: Decimal,
        volatility: float = 0.0,
        is_high_impact_news: bool = False,
        scenario_multiplier: float = 1.0,
    ) -> tuple[Decimal, Decimal]:
        """Apply spread to mid-price to get bid and ask.

        Args:
            mid_price: Mid-market price.
            volatility: Current volatility.
            is_high_impact_news: Whether news is active.
            scenario_multiplier: Scenario intensity.

        Returns:
            (bid_price, ask_price) with spread applied.
        """
        spread_pips = await self.calculate_spread_pips(
            volatility=volatility,
            is_high_impact_news=is_high_impact_news,
            scenario_multiplier=scenario_multiplier,
        )

        # Convert pips to price
        pip_value = Decimal("0.0001")  # Standard forex pip
        half_spread = Decimal(str(spread_pips / 2.0)) * pip_value

        bid = mid_price - half_spread
        ask = mid_price + half_spread

        # Ensure bid > 0
        if bid <= Decimal("0"):
            bid = Decimal("0.0001")

        return (bid, ask)

    async def spread_in_pips(self) -> float:
        """Return the current spread value in pips.

        Returns:
            Spread in pips based on configuration.
        """
        return self.config.value_pips

    async def get_config(self) -> SpreadConfig:
        """Return current configuration.

        Returns:
            Current SpreadConfig.
        """
        return self.config

    async def update_config(self, config: SpreadConfig) -> None:
        """Update spread configuration.

        Args:
            config: New SpreadConfig to use.
        """
        object.__setattr__(self, "config", config)
