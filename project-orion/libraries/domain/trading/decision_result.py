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


@dataclass(frozen=True)
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

    def __init__(
        self,
        symbol: str,
        outcome: DecisionOutcome,
        direction: SignalDirection | None = None,
        confidence: float = 0.0,
        strategy: StrategyType = StrategyType.SWING,
        entry_price: Decimal | None = None,
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
        position_size: Decimal | None = None,
        position_size_currency: str = "units",
        risk_amount: Decimal | None = None,
        account_risk_pct: float = 0.0,
        reason: str = "",
        reject_reasons: list[str] | None = None,
        signal: TradingSignal | None = None,
        decision_id: str = "",
        timestamp: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        stop_price: Decimal | None = None,
    ) -> None:
        effective_stop = stop_loss if stop_loss is not None else stop_price
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "direction", direction)
        object.__setattr__(self, "confidence", confidence)
        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(self, "entry_price", entry_price)
        object.__setattr__(self, "stop_loss", effective_stop)
        object.__setattr__(self, "take_profit", take_profit)
        object.__setattr__(self, "position_size", position_size)
        object.__setattr__(self, "position_size_currency", position_size_currency)
        object.__setattr__(self, "risk_amount", risk_amount)
        object.__setattr__(self, "account_risk_pct", account_risk_pct)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(
            self,
            "reject_reasons",
            reject_reasons if reject_reasons is not None else [],
        )
        object.__setattr__(self, "signal", signal)
        object.__setattr__(self, "decision_id", decision_id)
        object.__setattr__(
            self,
            "timestamp",
            timestamp if timestamp is not None else datetime.now(timezone.utc),
        )
        object.__setattr__(self, "metadata", metadata if metadata is not None else {})

    @property
    def stop_price(self) -> Decimal | None:
        """Alias for canonical stop_loss."""
        return self.stop_loss

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
