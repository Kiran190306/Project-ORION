"""Decision result models for the Trading Decision Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any

from libraries.domain.trading.models import StrategyType, TradingSignal
from libraries.domain.trading.signals import SignalDirection


class DecisionOutcome(StrEnum):
    """Outcome of a trading decision."""

    EXECUTE = "execute"
    REJECT = "reject"
    DEFER = "defer"


@dataclass(frozen=True, slots=True)
class TradeDecision:
    """Final structured trading decision produced by the DecisionEngine.

    This is the single output of the decision-making pipeline. It contains
    everything needed to execute or reject a trade.
    """

    symbol: str
    outcome: DecisionOutcome
    direction: SignalDirection | None = None
    confidence: float = 0.0
    strategy: StrategyType = StrategyType.SWING
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    position_size: Decimal | None = None
    position_size_currency: str = "units"
    risk_amount: Decimal | None = None
    account_risk_pct: float = 0.0
    reason: str = ""
    reject_reasons: list[str] = field(default_factory=list)
    signal: TradingSignal | None = None
    decision_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_executable(self) -> bool:
        """Return True if this decision should be executed."""
        return self.outcome == DecisionOutcome.EXECUTE and self.direction is not None

    @property
    def is_rejected(self) -> bool:
        """Return True if this decision was rejected."""
        return self.outcome == DecisionOutcome.REJECT

    @property
    def is_deferred(self) -> bool:
        """Return True if this decision was deferred."""
        return self.outcome == DecisionOutcome.DEFER
