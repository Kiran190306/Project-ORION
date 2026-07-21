"""Composite strategy - runs multiple strategies and aggregates results."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.strategies.conflict_resolver import (
    ConflictResolutionStrategy,
    ConflictResolver,
    ConflictResult,
)
from libraries.domain.strategies.context import StrategyContext
from libraries.domain.strategies.interfaces import (
    Strategy,
    StrategyCapabilities,
    StrategyMetadata,
)
from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.strategies.voting import (
    VotingEngine,
    VotingMethod,
    VotingResult,
)


@dataclass(frozen=True, slots=True)
class CompositeResult:
    """Result from composite strategy execution."""

    voting_result: VotingResult
    conflict_result: ConflictResult | None
    individual_results: list[StrategyResult]
    total_strategies: int
    executed_strategies: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CompositeStrategy:
    """Runs multiple strategies and aggregates their outputs.

    Supports:
    - Multiple strategies running simultaneously
    - Voting to aggregate results
    - Conflict resolution for conflicting signals
    - Forwarding final result to Decision Engine
    """

    def __init__(
        self,
        strategies: list[Strategy] | None = None,
        voting_engine: VotingEngine | None = None,
        conflict_resolver: ConflictResolver | None = None,
        default_voting_method: VotingMethod = VotingMethod.CONFIDENCE_WEIGHTED,
        default_conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
    ) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._voting_engine = voting_engine or VotingEngine(default_method=default_voting_method)
        self._conflict_resolver = conflict_resolver or ConflictResolver(
            default_strategy=default_conflict_strategy,
        )

        if strategies:
            for s in strategies:
                self._strategies[s.id] = s

    @property
    def strategy_count(self) -> int:
        return len(self._strategies)

    def add_strategy(self, strategy: Strategy) -> None:
        """Add a strategy to the composite."""
        self._strategies[strategy.id] = strategy

    def remove_strategy(self, strategy_id: str) -> None:
        """Remove a strategy from the composite."""
        self._strategies.pop(strategy_id, None)

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Get a strategy by ID."""
        return self._strategies.get(strategy_id)

    async def evaluate(
        self,
        symbol: str,
        context: StrategyContext,
        voting_method: VotingMethod | None = None,
        conflict_strategy: ConflictResolutionStrategy | None = None,
    ) -> CompositeResult:
        """Evaluate all strategies and aggregate results.

        Args:
            symbol: Trading symbol.
            context: Market context for evaluation.
            voting_method: Voting method (uses default if None).
            conflict_strategy: Conflict resolution strategy.

        Returns:
            CompositeResult with aggregated output.
        """
        if not self._strategies:
            empty_vote = await self._voting_engine.vote([], method=voting_method)
            return CompositeResult(
                voting_result=empty_vote,
                conflict_result=None,
                individual_results=[],
                total_strategies=0,
                executed_strategies=0,
            )

        # Run all strategies concurrently
        async def _evaluate_one(strategy: Strategy) -> StrategyResult | None:
            try:
                return await strategy.evaluate(symbol, context)
            except Exception:
                return None

        tasks = [_evaluate_one(s) for s in self._strategies.values()]
        raw_results = await asyncio.gather(*tasks)

        # Filter out None results (HOLDs)
        results = [r for r in raw_results if r is not None]

        # Check for conflicting directions
        directions = {r.direction for r in results}
        conflict_result: ConflictResult | None = None

        if len(directions) > 1 and not (len(directions) == 1 and None in directions):
            # Conflicts exist
            conflict_result = self._conflict_resolver.resolve(
                results,
                strategy=conflict_strategy,
            )

        # Run voting
        voting_result = await self._voting_engine.vote(
            results,
            method=voting_method,
        )

        return CompositeResult(
            voting_result=voting_result,
            conflict_result=conflict_result,
            individual_results=results,
            total_strategies=len(self._strategies),
            executed_strategies=len(results),
        )
