"""Strategy context providing market data to strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.trading.market_state import MarketState


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Immutable context passed to strategies during evaluation.

    Contains all market data a strategy might need to generate signals.
    """

    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Price data
    bid: Decimal | None = None
    ask: Decimal | None = None
    spread_pips: float = 0.0

    # Market state
    market_state: MarketState | None = None
    trend_strength: float = 0.0
    volatility_percentile: float = 0.5
    liquidity_score: float = 0.5

    # Technical indicators
    rsi: float | None = None
    ema_fast: Decimal | None = None
    ema_slow: Decimal | None = None
    atr: Decimal | None = None

    # Price position
    price_position: float = 0.5  # 0.0 = low of range, 1.0 = high of range
    volume_ratio: float = 1.0  # Current volume / average volume

    # Provider quality
    provider_quality: float = 0.5
    consensus_quality: float = 0.5

    # Extra data for extensibility
    extra: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get extra data by key."""
        return getattr(self, key, self.extra.get(key, default))
