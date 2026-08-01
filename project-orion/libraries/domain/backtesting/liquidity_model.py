"""Liquidity models for backtesting execution simulation.

Simulates market liquidity constraints that affect order execution,
including volume-based limits, time-based liquidity profiles,
and symbol-specific liquidity scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class LiquidityModelConfig:
    """Configuration for the liquidity model."""

    default_liquidity_score: float = 0.8  # 0-1 score
    max_order_pct_of_volume: float = 0.1  # Max 10% of volume
    volume_threshold_lots: Decimal = Decimal("50")  # Above this = reduced liquidity
    liquidity_decay_factor: float = 0.95  # Decay per lot above threshold
    min_liquidity_score: float = 0.1
    metadata: dict[str, Any] = field(default_factory=dict)


class LiquidityModel:
    """Models market liquidity for execution simulation.

    Thread-safe via stateless design.
    """

    def __init__(self, config: LiquidityModelConfig | None = None) -> None:
        """Initialize liquidity model.

        Args:
            config: Liquidity configuration. Uses defaults if None.
        """
        self._config = config or LiquidityModelConfig()

    @property
    def config(self) -> LiquidityModelConfig:
        """Return the current configuration."""
        return self._config

    def get_liquidity_score(
        self,
        symbol: str,
        volume: Decimal,
        timestamp: datetime | None = None,
        base_score: float | None = None,
    ) -> float:
        """Calculate effective liquidity score for an order.

        Args:
            symbol: Trading symbol.
            volume: Order volume in lots.
            timestamp: Current timestamp (for session-based liquidity).
            base_score: Optional base liquidity score for the symbol.

        Returns:
            Effective liquidity score (0-1).
        """
        cfg = self._config
        score = base_score or cfg.default_liquidity_score

        # Reduce liquidity for large orders
        if volume > cfg.volume_threshold_lots:
            excess_lots = float(volume - cfg.volume_threshold_lots)
            decay = cfg.liquidity_decay_factor**excess_lots
            score *= decay

        # Time-based liquidity adjustment only applies when an explicit
        # timestamp is provided. Without one, the score is deterministic
        # and independent of wall-clock time.
        if timestamp is not None:
            hour = timestamp.hour
            # Lower liquidity during Asian session, higher during London/NY overlap
            if 0 <= hour < 7:
                score *= 0.7
            elif 13 <= hour < 17:
                score *= 1.2
            elif 17 <= hour < 21:
                score *= 0.85

        # Ensure minimum
        if score < cfg.min_liquidity_score:
            score = cfg.min_liquidity_score

        return round(score, 4)

    def is_executable(
        self,
        volume: Decimal,
        current_volume: Decimal | None = None,
    ) -> bool:
        """Check if an order is executable given current liquidity.

        Args:
            volume: Order volume.
            current_volume: Current market volume (optional).

        Returns:
            True if the order is executable.
        """
        cfg = self._config
        if current_volume is not None and current_volume > Decimal("0"):
            ratio = float(volume / current_volume)
            return ratio <= cfg.max_order_pct_of_volume
        return True

    def get_max_executable_volume(
        self,
        available_liquidity: Decimal,
    ) -> Decimal:
        """Get maximum executable volume given available liquidity.

        Args:
            available_liquidity: Available market liquidity.

        Returns:
            Maximum executable volume.
        """
        cfg = self._config
        max_vol = available_liquidity * Decimal(str(cfg.max_order_pct_of_volume))
        return max_vol.quantize(Decimal("0.01"))
