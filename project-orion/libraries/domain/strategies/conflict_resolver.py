"""Conflict resolution between strategies producing conflicting signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.trading.signals import SignalDirection


class ConflictResolutionStrategy(StrEnum):
    """Strategies for resolving conflicts between strategy results."""

    EXIT_WINS = "exit_wins"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MOST_RECENT = "most_recent"
    DEFER = "defer"
    VOTE = "vote"


@dataclass(frozen=True, slots=True)
class ConflictResult:
    """Result of conflict resolution."""

    resolved_direction: SignalDirection | None
    confidence: float
    resolution_method: ConflictResolutionStrategy
    winners: list[StrategyResult] = field(default_factory=list)
    losers: list[StrategyResult] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class ConflictResolver:
    """Resolves conflicts between strategies producing different signals.

    EXIT always takes highest priority (safety first).
    """

    def __init__(
        self,
        default_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
    ) -> None:
        self._default_strategy = default_strategy

    def resolve(
        self,
        results: list[StrategyResult],
        strategy: ConflictResolutionStrategy | None = None,
    ) -> ConflictResult:
        """Resolve conflicts among strategy results.

        Args:
            results: Strategy results, possibly with conflicting directions.
            strategy: Resolution strategy to use.

        Returns:
            ConflictResult with the resolved decision.
        """
        if not results:
            return ConflictResult(
                resolved_direction=None,
                confidence=0.0,
                resolution_method=strategy or self._default_strategy,
            )

        # Check if any strategy wants EXIT - EXIT always wins
        for result in results:
            if result.direction == SignalDirection.EXIT:
                return ConflictResult(
                    resolved_direction=SignalDirection.EXIT,
                    confidence=result.confidence,
                    resolution_method=ConflictResolutionStrategy.EXIT_WINS,
                    winners=[result],
                    losers=[r for r in results if r is not result],
                    details={"reason": "EXIT override - safety first"},
                )

        strategy = strategy or self._default_strategy

        if strategy == ConflictResolutionStrategy.HIGHEST_CONFIDENCE:
            return self._resolve_highest_confidence(results)
        elif strategy == ConflictResolutionStrategy.MOST_RECENT:
            return self._resolve_most_recent(results)
        elif strategy == ConflictResolutionStrategy.DEFER:
            return self._resolve_defer(results)
        elif strategy == ConflictResolutionStrategy.VOTE:
            return self._resolve_vote(results)
        else:
            return self._resolve_highest_confidence(results)

    def _resolve_highest_confidence(
        self,
        results: list[StrategyResult],
    ) -> ConflictResult:
        """Pick the result with the highest confidence."""
        if not results:
            return ConflictResult(
                resolved_direction=None,
                confidence=0.0,
                resolution_method=ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
            )

        best = max(results, key=lambda r: r.confidence)
        return ConflictResult(
            resolved_direction=best.direction,
            confidence=best.confidence,
            resolution_method=ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
            winners=[best],
            losers=[r for r in results if r is not best],
            details={"best_strategy": best.strategy_id},
        )

    def _resolve_most_recent(
        self,
        results: list[StrategyResult],
    ) -> ConflictResult:
        """Pick the most recent result."""
        if not results:
            return ConflictResult(
                resolved_direction=None,
                confidence=0.0,
                resolution_method=ConflictResolutionStrategy.MOST_RECENT,
            )

        best = max(results, key=lambda r: r.timestamp)
        return ConflictResult(
            resolved_direction=best.direction,
            confidence=best.confidence,
            resolution_method=ConflictResolutionStrategy.MOST_RECENT,
            winners=[best],
            losers=[r for r in results if r is not best],
            details={"best_strategy": best.strategy_id},
        )

    def _resolve_defer(
        self,
        results: list[StrategyResult],
    ) -> ConflictResult:
        """Defer decision when conflict exists (return None)."""
        return ConflictResult(
            resolved_direction=None,
            confidence=0.0,
            resolution_method=ConflictResolutionStrategy.DEFER,
            winners=[],
            losers=list(results),
            details={"reason": "Conflict detected, decision deferred"},
        )

    def _resolve_vote(
        self,
        results: list[StrategyResult],
    ) -> ConflictResult:
        """Let the voting engine decide."""
        buy_count = sum(1 for r in results if r.direction == SignalDirection.BUY)
        sell_count = sum(1 for r in results if r.direction == SignalDirection.SELL)

        if buy_count > sell_count:
            winners = [r for r in results if r.direction == SignalDirection.BUY]
            avg_conf = sum(r.confidence for r in winners) / len(winners) if winners else 0
            return ConflictResult(
                resolved_direction=SignalDirection.BUY,
                confidence=round(avg_conf, 2),
                resolution_method=ConflictResolutionStrategy.VOTE,
                winners=winners,
                losers=[r for r in results if r.direction != SignalDirection.BUY],
            )
        elif sell_count > buy_count:
            winners = [r for r in results if r.direction == SignalDirection.SELL]
            avg_conf = sum(r.confidence for r in winners) / len(winners) if winners else 0
            return ConflictResult(
                resolved_direction=SignalDirection.SELL,
                confidence=round(avg_conf, 2),
                resolution_method=ConflictResolutionStrategy.VOTE,
                winners=winners,
                losers=[r for r in results if r.direction != SignalDirection.SELL],
            )
        else:
            return ConflictResult(
                resolved_direction=None,
                confidence=0.0,
                resolution_method=ConflictResolutionStrategy.VOTE,
                winners=[],
                losers=list(results),
                details={"reason": "Tie vote - no resolution"},
            )
