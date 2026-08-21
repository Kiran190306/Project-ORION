"""Protocol/port definitions for the Trading Decision Engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol, runtime_checkable

from libraries.domain.trading.decision_result import TradeDecision
from libraries.domain.trading.market_state import MarketState
from libraries.domain.trading.models import (
    SizingResult,
    StrategyType,
    TradingSignal,
)


@runtime_checkable
class MarketIntelligencePort(Protocol):
    """Port for querying market intelligence data."""

    async def get_liquidity_score(self, symbol: str) -> float:
        """Return liquidity score 0-1 for a symbol."""
        ...

    async def get_spread(self, symbol: str) -> float:
        """Return current spread in pips."""
        ...

    async def get_volatility(self, symbol: str) -> float:
        """Return current volatility measure."""
        ...

    async def get_consensus_quality(self, symbol: str) -> float:
        """Return consensus quality score 0-1."""
        ...

    async def get_provider_health(self, symbol: str) -> float:
        """Return aggregated provider health score 0-1."""
        ...


@runtime_checkable
class MarketStatePort(Protocol):
    """Port for querying current market state."""

    async def get_market_state(self, symbol: str) -> MarketState:
        """Return the current market state for a symbol."""
        ...


@runtime_checkable
class SignalGeneratorPort(Protocol):
    """Port for generating trading signals."""

    async def generate_signal(self, symbol: str) -> TradingSignal | None:
        """Generate a trading signal for a symbol."""
        ...


@runtime_checkable
class ConfidencePort(Protocol):
    """Port for computing confidence scores."""

    async def compute_confidence(self, symbol: str, signal: TradingSignal) -> float:
        """Compute confidence score 0-100 for a signal."""
        ...


@runtime_checkable
class RiskFilterPort(Protocol):
    """Port for risk filtering."""

    async def is_trade_allowed(
        self,
        symbol: str,
        signal: TradingSignal,
        confidence: float,
    ) -> tuple[bool, str]:
        """Check if a trade is allowed by risk rules."""
        ...


@runtime_checkable
class ExecutionFilterPort(Protocol):
    """Port for execution filtering."""

    async def can_execute(self, symbol: str, signal: TradingSignal) -> tuple[bool, str]:
        """Check if a trade can be executed under current market conditions."""
        ...


@runtime_checkable
class PositionSizerPort(Protocol):
    """Port for position sizing."""

    async def calculate_size(
        self,
        symbol: str,
        signal: TradingSignal,
        confidence: float,
        account_balance: Decimal,
    ) -> SizingResult:
        """Calculate position size."""
        ...


@runtime_checkable
class TradeValidatorPort(Protocol):
    """Port for final trade validation."""

    async def validate(
        self,
        symbol: str,
        signal: TradingSignal,
        decision: TradeDecision,
    ) -> tuple[bool, list[str]]:
        """Validate a trade decision before execution."""
        ...


@runtime_checkable
class StrategyRouterPort(Protocol):
    """Port for routing signals to appropriate strategies."""

    async def route(self, symbol: str, state: MarketState) -> StrategyType:
        """Route to the appropriate strategy based on market state."""
        ...


@runtime_checkable
class DecisionEnginePort(Protocol):
    """Port for the decision engine."""

    async def make_decision(self, symbol: str) -> TradeDecision | None:
        """Make a trading decision for a symbol."""
        ...


@runtime_checkable
class TradingDecisionSink(Protocol):
    """Consumer of final trading decisions."""

    async def on_decision(self, decision: TradeDecision) -> None:
        """Called when a new trading decision is produced."""
        ...
