"""Decision context aggregating all inputs for the Trading Decision Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from libraries.domain.trading.market_state import MarketState
from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """Complete context for making a trading decision.

    Aggregates all inputs from market intelligence, signal generation,
    confidence scoring, risk filtering, execution filtering, and
    strategy routing into a single context object.
    """

    symbol: str
    signal: TradingSignal | None = None
    market_state: MarketState | None = None
    confidence_score: float = 0.0
    liquidity_score: float = 0.0
    spread_pips: float = 0.0
    volatility_score: float = 0.0
    consensus_quality: float = 0.0
    provider_health: float = 0.0
    account_balance: Decimal = Decimal("0")
    current_position: Decimal = Decimal("0")
    strategy: StrategyType = StrategyType.SWING
    risk_allowed: bool = True
    risk_reason: str = ""
    execution_allowed: bool = True
    execution_reason: str = ""
    validation_errors: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        """Return whether the context has all required inputs for a decision."""
        return (
            self.signal is not None
            and self.market_state is not None
            and self.confidence_score > 0
            and self.risk_allowed
            and self.execution_allowed
            and not self.validation_errors
        )

    @property
    def signal_direction(self) -> SignalDirection | None:
        """Return the signal direction if signal exists."""
        if self.signal is not None:
            return self.signal.direction
        return None

    @property
    def composite_quality(self) -> float:
        """Compute a composite quality score from all inputs."""
        scores = [
            self.liquidity_score,
            1.0 - min(1.0, self.spread_pips / 10.0),
            self.consensus_quality,
            self.provider_health,
            self.confidence_score / 100.0,
        ]
        if self.market_state is not None:
            scores.append(self.market_state.confidence)
        return sum(scores) / len(scores) if scores else 0.0
