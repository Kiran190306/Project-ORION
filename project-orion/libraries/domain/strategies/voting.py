"""Voting Engine for strategy consensus.

Supports multiple voting methods to aggregate strategy results:
- Majority Vote
- Weighted Vote (by priority)
- Confidence Weighted
- Priority Override
- Consensus Required
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.trading.signals import SignalDirection


class VotingMethod(StrEnum):
    """Available voting methods for aggregating strategy results."""

    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    PRIORITY_OVERRIDE = "priority_override"
    CONSENSUS = "consensus"


@dataclass(frozen=True, slots=True)
class VotingResult:
    """Result from the voting engine."""

    direction: SignalDirection | None
    confidence: float
    total_votes: int
    votes_for: int
    votes_against: int
    abstentions: int
    method_used: VotingMethod
    details: dict[str, Any] = field(default_factory=dict)


class VotingEngine:
    """Aggregates strategy results into a single trading decision.

    Supports multiple voting methods configurable per evaluation.
    """

    def __init__(self, default_method: VotingMethod = VotingMethod.CONFIDENCE_WEIGHTED) -> None:
        self._default_method = default_method

    async def vote(
        self,
        results: list[StrategyResult],
        method: VotingMethod | None = None,
        priority_map: dict[str, int] | None = None,
    ) -> VotingResult:
        """Aggregate strategy results using the specified voting method.

        Args:
            results: Strategy results to aggregate.
            method: Voting method (uses default if None).
            priority_map: Priority values for weighted voting (strategy_id -> priority).

        Returns:
            VotingResult with the aggregated decision.
        """
        if not results:
            return VotingResult(
                direction=None,
                confidence=0.0,
                total_votes=0,
                votes_for=0,
                votes_against=0,
                abstentions=0,
                method_used=method or self._default_method,
            )

        method = method or self._default_method

        if method == VotingMethod.MAJORITY:
            return await self._majority_vote(results)
        elif method == VotingMethod.WEIGHTED:
            return await self._weighted_vote(results, priority_map)
        elif method == VotingMethod.CONFIDENCE_WEIGHTED:
            return await self._confidence_weighted_vote(results)
        elif method == VotingMethod.PRIORITY_OVERRIDE:
            return await self._priority_override_vote(results, priority_map)
        elif method == VotingMethod.CONSENSUS:
            return await self._consensus_vote(results)
        else:
            return await self._confidence_weighted_vote(results)

    async def _majority_vote(self, results: list[StrategyResult]) -> VotingResult:
        """Simple majority vote - each strategy gets one vote."""
        buy_votes = sum(1 for r in results if r.direction == SignalDirection.BUY)
        sell_votes = sum(1 for r in results if r.direction == SignalDirection.SELL)
        total = len(results)
        abstentions = total - buy_votes - sell_votes

        if buy_votes > sell_votes and buy_votes > total / 2:
            confidence = (buy_votes / total) * 100
            return VotingResult(
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                total_votes=total,
                votes_for=buy_votes,
                votes_against=sell_votes,
                abstentions=abstentions,
                method_used=VotingMethod.MAJORITY,
            )
        elif sell_votes > buy_votes and sell_votes > total / 2:
            confidence = (sell_votes / total) * 100
            return VotingResult(
                direction=SignalDirection.SELL,
                confidence=round(confidence, 2),
                total_votes=total,
                votes_for=sell_votes,
                votes_against=buy_votes,
                abstentions=abstentions,
                method_used=VotingMethod.MAJORITY,
            )

        return VotingResult(
            direction=None,
            confidence=0.0,
            total_votes=total,
            votes_for=max(buy_votes, sell_votes),
            votes_against=min(buy_votes, sell_votes),
            abstentions=abstentions,
            method_used=VotingMethod.MAJORITY,
        )

    async def _weighted_vote(
        self,
        results: list[StrategyResult],
        priority_map: dict[str, int] | None = None,
    ) -> VotingResult:
        """Weighted vote by strategy priority."""
        if priority_map is None:
            priority_map = {}

        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0

        for result in results:
            weight = float(priority_map.get(result.strategy_id, 1))
            total_weight += weight
            if result.direction == SignalDirection.BUY:
                buy_weight += weight
            elif result.direction == SignalDirection.SELL:
                sell_weight += weight

        if buy_weight > sell_weight and buy_weight > total_weight / 2:
            confidence = (buy_weight / total_weight) * 100
            return VotingResult(
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                total_votes=len(results),
                votes_for=int(buy_weight),
                votes_against=int(sell_weight),
                abstentions=len(results)
                - sum(
                    1 for r in results if r.direction in (SignalDirection.BUY, SignalDirection.SELL)
                ),
                method_used=VotingMethod.WEIGHTED,
            )
        elif sell_weight > buy_weight and sell_weight > total_weight / 2:
            confidence = (sell_weight / total_weight) * 100
            return VotingResult(
                direction=SignalDirection.SELL,
                confidence=round(confidence, 2),
                total_votes=len(results),
                votes_for=int(sell_weight),
                votes_against=int(buy_weight),
                abstentions=len(results)
                - sum(
                    1 for r in results if r.direction in (SignalDirection.BUY, SignalDirection.SELL)
                ),
                method_used=VotingMethod.WEIGHTED,
            )

        return VotingResult(
            direction=None,
            confidence=0.0,
            total_votes=len(results),
            votes_for=int(max(buy_weight, sell_weight)),
            votes_against=int(min(buy_weight, sell_weight)),
            abstentions=len(results)
            - sum(1 for r in results if r.direction in (SignalDirection.BUY, SignalDirection.SELL)),
            method_used=VotingMethod.WEIGHTED,
        )

    async def _confidence_weighted_vote(
        self,
        results: list[StrategyResult],
    ) -> VotingResult:
        """Vote weighted by each strategy's confidence score."""
        buy_confidence = 0.0
        sell_confidence = 0.0
        total_confidence = 0.0

        for result in results:
            total_confidence += result.confidence
            if result.direction == SignalDirection.BUY:
                buy_confidence += result.confidence
            elif result.direction == SignalDirection.SELL:
                sell_confidence += result.confidence

        if total_confidence == 0:
            return VotingResult(
                direction=None,
                confidence=0.0,
                total_votes=len(results),
                votes_for=0,
                votes_against=0,
                abstentions=len(results),
                method_used=VotingMethod.CONFIDENCE_WEIGHTED,
            )

        if buy_confidence > sell_confidence:
            confidence = (buy_confidence / total_confidence) * 100
            return VotingResult(
                direction=SignalDirection.BUY,
                confidence=round(confidence, 2),
                total_votes=len(results),
                votes_for=sum(1 for r in results if r.direction == SignalDirection.BUY),
                votes_against=sum(1 for r in results if r.direction == SignalDirection.SELL),
                abstentions=sum(
                    1
                    for r in results
                    if r.direction not in (SignalDirection.BUY, SignalDirection.SELL)
                ),
                method_used=VotingMethod.CONFIDENCE_WEIGHTED,
                details={"buy_confidence": buy_confidence, "sell_confidence": sell_confidence},
            )
        elif sell_confidence > buy_confidence:
            confidence = (sell_confidence / total_confidence) * 100
            return VotingResult(
                direction=SignalDirection.SELL,
                confidence=round(confidence, 2),
                total_votes=len(results),
                votes_for=sum(1 for r in results if r.direction == SignalDirection.SELL),
                votes_against=sum(1 for r in results if r.direction == SignalDirection.BUY),
                abstentions=sum(
                    1
                    for r in results
                    if r.direction not in (SignalDirection.BUY, SignalDirection.SELL)
                ),
                method_used=VotingMethod.CONFIDENCE_WEIGHTED,
                details={"buy_confidence": buy_confidence, "sell_confidence": sell_confidence},
            )

        return VotingResult(
            direction=None,
            confidence=0.0,
            total_votes=len(results),
            votes_for=sum(1 for r in results if r.direction == SignalDirection.BUY),
            votes_against=sum(1 for r in results if r.direction == SignalDirection.SELL),
            abstentions=sum(
                1 for r in results if r.direction not in (SignalDirection.BUY, SignalDirection.SELL)
            ),
            method_used=VotingMethod.CONFIDENCE_WEIGHTED,
        )

    async def _priority_override_vote(
        self,
        results: list[StrategyResult],
        priority_map: dict[str, int] | None = None,
    ) -> VotingResult:
        """Highest priority strategy's result wins."""
        if not results:
            return VotingResult(
                direction=None,
                confidence=0.0,
                total_votes=0,
                votes_for=0,
                votes_against=0,
                abstentions=0,
                method_used=VotingMethod.PRIORITY_OVERRIDE,
            )

        priority_map = priority_map or {}
        best_result = max(
            results,
            key=lambda r: priority_map.get(r.strategy_id, 0),
        )

        return VotingResult(
            direction=best_result.direction,
            confidence=best_result.confidence,
            total_votes=len(results),
            votes_for=1,
            votes_against=len(results) - 1,
            abstentions=0,
            method_used=VotingMethod.PRIORITY_OVERRIDE,
            details={"winning_strategy": best_result.strategy_id},
        )

    async def _consensus_vote(self, results: list[StrategyResult]) -> VotingResult:
        """All strategies must agree on direction."""
        directions = {
            r.direction
            for r in results
            if r.direction in (SignalDirection.BUY, SignalDirection.SELL)
        }

        if len(directions) == 1:
            direction = directions.pop()
            avg_confidence = sum(r.confidence for r in results if r.direction == direction) / len(
                results
            )
            return VotingResult(
                direction=direction,
                confidence=round(avg_confidence, 2),
                total_votes=len(results),
                votes_for=sum(1 for r in results if r.direction == direction),
                votes_against=0,
                abstentions=sum(
                    1
                    for r in results
                    if r.direction not in (SignalDirection.BUY, SignalDirection.SELL)
                ),
                method_used=VotingMethod.CONSENSUS,
            )

        return VotingResult(
            direction=None,
            confidence=0.0,
            total_votes=len(results),
            votes_for=0,
            votes_against=sum(
                1 for r in results if r.direction in (SignalDirection.BUY, SignalDirection.SELL)
            ),
            abstentions=sum(
                1 for r in results if r.direction not in (SignalDirection.BUY, SignalDirection.SELL)
            ),
            method_used=VotingMethod.CONSENSUS,
        )
