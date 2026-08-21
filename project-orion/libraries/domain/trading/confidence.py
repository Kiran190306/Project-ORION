"""Confidence scoring for the Trading Decision Engine.

Computes a 0-100 confidence score by combining liquidity, spread,
volatility, provider quality, consensus quality, and market state.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from libraries.domain.trading.market_state import MarketState
from libraries.domain.trading.models import TradingSignal


@dataclass(frozen=True, slots=True)
class ConfidenceFactors:
    """Individual factors contributing to the confidence score."""

    liquidity: float = 0.0
    spread: float = 0.0
    volatility: float = 0.0
    provider_quality: float = 0.0
    consensus_quality: float = 0.0
    market_state: float = 0.0
    signal_strength: float = 0.0
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def composite(self) -> float:
        """Weighted composite of all factors (0-100)."""
        weights = {
            "liquidity": 0.20,
            "spread": 0.15,
            "volatility": 0.10,
            "provider_quality": 0.15,
            "consensus_quality": 0.15,
            "market_state": 0.15,
            "signal_strength": 0.10,
        }
        score = (
            self.liquidity * weights["liquidity"]
            + self.spread * weights["spread"]
            + self.volatility * weights["volatility"]
            + self.provider_quality * weights["provider_quality"]
            + self.consensus_quality * weights["consensus_quality"]
            + self.market_state * weights["market_state"]
            + self.signal_strength * weights["signal_strength"]
        )
        return max(0.0, min(100.0, score * 100.0))


class ConfidenceScorer:
    """Computes confidence scores for trading signals.

    Thread-safe via asyncio.Lock.
    """

    def __init__(
        self,
        min_liquidity: float = 0.3,
        max_spread_pips: float = 5.0,
        volatility_penalty_threshold: float = 0.8,
    ) -> None:
        if not 0 <= min_liquidity <= 1:
            raise ValueError("min_liquidity must be between 0 and 1")
        if max_spread_pips <= 0:
            raise ValueError("max_spread_pips must be positive")
        self._min_liquidity = min_liquidity
        self._max_spread_pips = max_spread_pips
        self._volatility_penalty_threshold = volatility_penalty_threshold
        self._lock = asyncio.Lock()

    async def compute(
        self,
        signal: TradingSignal,
        market_state: MarketState,
        liquidity_score: float = 0.5,
        spread_pips: float = 1.0,
        volatility_score: float = 0.5,
        provider_quality: float = 0.7,
        consensus_quality: float = 0.7,
    ) -> float:
        """Compute confidence score 0-100.

        Args:
            signal: The trading signal.
            market_state: Current market state.
            liquidity_score: 0.0-1.0 liquidity score.
            spread_pips: Current spread in pips.
            volatility_score: 0.0-1.0 volatility score.
            provider_quality: 0.0-1.0 provider quality score.
            consensus_quality: 0.0-1.0 consensus quality score.

        Returns:
            Confidence score 0-100.
        """
        async with self._lock:
            factors = await self._compute_factors(
                signal,
                market_state,
                liquidity_score,
                spread_pips,
                volatility_score,
                provider_quality,
                consensus_quality,
            )
            return factors.composite

    async def compute_factors(
        self,
        signal: TradingSignal,
        market_state: MarketState,
        liquidity_score: float = 0.5,
        spread_pips: float = 1.0,
        volatility_score: float = 0.5,
        provider_quality: float = 0.7,
        consensus_quality: float = 0.7,
    ) -> ConfidenceFactors:
        """Compute detailed confidence factors."""
        async with self._lock:
            return await self._compute_factors(
                signal,
                market_state,
                liquidity_score,
                spread_pips,
                volatility_score,
                provider_quality,
                consensus_quality,
            )

    async def _compute_factors(
        self,
        signal: TradingSignal,
        market_state: MarketState,
        liquidity_score: float,
        spread_pips: float,
        volatility_score: float,
        provider_quality: float,
        consensus_quality: float,
    ) -> ConfidenceFactors:
        """Internal factors computation."""
        # Liquidity factor (0-1)
        liq_factor = max(0.0, min(1.0, liquidity_score))

        # Spread factor (0-1, inverse - lower spread = higher score)
        spread_factor = max(0.0, 1.0 - (spread_pips / self._max_spread_pips))

        # Volatility factor (0-1)
        if volatility_score >= self._volatility_penalty_threshold:
            vol_factor = 1.0 - volatility_score
        else:
            vol_factor = 1.0 - (volatility_score * 0.5)
        vol_factor = max(0.0, min(1.0, vol_factor))

        # Provider quality factor
        prov_factor = max(0.0, min(1.0, provider_quality))

        # Consensus quality factor
        cons_factor = max(0.0, min(1.0, consensus_quality))

        # Market state factor
        state_factor = market_state.confidence

        # Signal strength factor
        strength_map = {"strong": 1.0, "moderate": 0.6, "weak": 0.3}
        strength_factor = strength_map.get(signal.strength.value, 0.5)

        return ConfidenceFactors(
            liquidity=liq_factor,
            spread=spread_factor,
            volatility=vol_factor,
            provider_quality=prov_factor,
            consensus_quality=cons_factor,
            market_state=state_factor,
            signal_strength=strength_factor,
        )
