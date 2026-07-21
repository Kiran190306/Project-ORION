"""Tests for ConflictResolver."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.strategies.conflict_resolver import (
    ConflictResolutionStrategy,
    ConflictResolver,
    ConflictResult,
)
from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.trading.signals import SignalDirection, SignalStrength


def make_result(
    strategy_id: str,
    direction: SignalDirection,
    confidence: float = 50.0,
) -> StrategyResult:
    return StrategyResult(
        strategy_id=strategy_id,
        symbol="EUR/USD",
        direction=direction,
        confidence=confidence,
        strength=SignalStrength.MODERATE,
        price=Decimal("1.1000"),
    )


class TestConflictResolver:
    def test_empty_results(self) -> None:
        resolver = ConflictResolver()
        result = resolver.resolve([])
        assert result.resolved_direction is None
        assert result.confidence == 0.0

    def test_exit_always_wins(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.BUY, confidence=90.0),
            make_result("s2", SignalDirection.EXIT, confidence=10.0),
        ]
        result = resolver.resolve(results)
        assert result.resolved_direction == SignalDirection.EXIT
        assert result.resolution_method == ConflictResolutionStrategy.EXIT_WINS

    def test_highest_confidence_wins(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.BUY, confidence=30.0),
            make_result("s2", SignalDirection.SELL, confidence=80.0),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
        )
        assert result.resolved_direction == SignalDirection.SELL
        assert len(result.winners) == 1
        assert result.winners[0].strategy_id == "s2"

    def test_most_recent_wins(self) -> None:
        resolver = ConflictResolver()
        now = datetime.now(timezone.utc)
        results = [
            StrategyResult(
                strategy_id="s1",
                symbol="EUR/USD",
                direction=SignalDirection.BUY,
                confidence=50.0,
                strength=SignalStrength.MODERATE,
                price=Decimal("1.1000"),
                timestamp=now,
            ),
            StrategyResult(
                strategy_id="s2",
                symbol="EUR/USD",
                direction=SignalDirection.SELL,
                confidence=80.0,
                strength=SignalStrength.STRONG,
                price=Decimal("1.1000"),
                timestamp=now.replace(year=now.year + 1),  # Future
            ),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.MOST_RECENT,
        )
        assert result.resolved_direction == SignalDirection.SELL

    def test_defer_on_conflict(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.BUY),
            make_result("s2", SignalDirection.SELL),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.DEFER,
        )
        assert result.resolved_direction is None

    def test_vote_resolution_buy_wins(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.BUY),
            make_result("s2", SignalDirection.BUY),
            make_result("s3", SignalDirection.SELL),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.VOTE,
        )
        assert result.resolved_direction == SignalDirection.BUY

    def test_vote_resolution_sell_wins(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.SELL),
            make_result("s2", SignalDirection.SELL),
            make_result("s3", SignalDirection.BUY),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.VOTE,
        )
        assert result.resolved_direction == SignalDirection.SELL

    def test_vote_tie_no_resolution(self) -> None:
        resolver = ConflictResolver()
        results = [
            make_result("s1", SignalDirection.BUY),
            make_result("s2", SignalDirection.SELL),
        ]
        result = resolver.resolve(
            results,
            strategy=ConflictResolutionStrategy.VOTE,
        )
        assert result.resolved_direction is None

    def test_default_strategy_used(self) -> None:
        resolver = ConflictResolver(
            default_strategy=ConflictResolutionStrategy.HIGHEST_CONFIDENCE,
        )
        results = [
            make_result("s1", SignalDirection.BUY, confidence=20.0),
            make_result("s2", SignalDirection.SELL, confidence=90.0),
        ]
        result = resolver.resolve(results)  # No strategy specified
        assert result.resolved_direction == SignalDirection.SELL
