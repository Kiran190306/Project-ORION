"""Tests for VotingEngine."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.strategies.strategy import StrategyResult
from libraries.domain.strategies.voting import (
    VotingEngine,
    VotingMethod,
    VotingResult,
)
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


class TestVotingEngine:
    def test_empty_results(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            result = await engine.vote([])
            assert result.direction is None
            assert result.total_votes == 0

        asyncio.run(exercise())

    def test_majority_vote_buy_wins(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine(default_method=VotingMethod.MAJORITY)
            results = [
                make_result("s1", SignalDirection.BUY),
                make_result("s2", SignalDirection.BUY),
                make_result("s3", SignalDirection.SELL),
            ]
            result = await engine.vote(results, method=VotingMethod.MAJORITY)
            assert result.direction == SignalDirection.BUY
            assert result.total_votes == 3
            assert result.votes_for == 2

        asyncio.run(exercise())

    def test_majority_vote_sell_wins(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.SELL),
                make_result("s2", SignalDirection.SELL),
                make_result("s3", SignalDirection.BUY),
            ]
            result = await engine.vote(results, method=VotingMethod.MAJORITY)
            assert result.direction == SignalDirection.SELL

        asyncio.run(exercise())

    def test_majority_vote_no_clear_winner(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.BUY),
                make_result("s2", SignalDirection.SELL),
                make_result("s3", SignalDirection.BUY),
            ]
            result = await engine.vote(results, method=VotingMethod.MAJORITY)
            # 2 buy, 1 sell = buy wins (but buy > total/2 = 3/2 = 1.5)
            assert result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_weighted_vote(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.BUY, confidence=80.0),
                make_result("s2", SignalDirection.SELL, confidence=90.0),
            ]
            priority_map = {"s1": 5, "s2": 1}
            result = await engine.vote(
                results,
                method=VotingMethod.WEIGHTED,
                priority_map=priority_map,
            )
            # s1 has higher weight (5) vs s2 (1), so BUY should win
            assert result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_confidence_weighted_vote(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.BUY, confidence=90.0),
                make_result("s2", SignalDirection.SELL, confidence=10.0),
            ]
            result = await engine.vote(
                results,
                method=VotingMethod.CONFIDENCE_WEIGHTED,
            )
            # BUY has higher total confidence
            assert result.direction == SignalDirection.BUY
            assert result.method_used == VotingMethod.CONFIDENCE_WEIGHTED

        asyncio.run(exercise())

    def test_priority_override(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("low_priority", SignalDirection.SELL, confidence=90.0),
                make_result("high_priority", SignalDirection.BUY, confidence=10.0),
            ]
            priority_map = {"low_priority": 1, "high_priority": 10}
            result = await engine.vote(
                results,
                method=VotingMethod.PRIORITY_OVERRIDE,
                priority_map=priority_map,
            )
            # High priority strategy's direction wins
            assert result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_consensus_required_all_agree(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.BUY),
                make_result("s2", SignalDirection.BUY),
                make_result("s3", SignalDirection.BUY),
            ]
            result = await engine.vote(results, method=VotingMethod.CONSENSUS)
            assert result.direction == SignalDirection.BUY

        asyncio.run(exercise())

    def test_consensus_required_fails_on_disagreement(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine()
            results = [
                make_result("s1", SignalDirection.BUY),
                make_result("s2", SignalDirection.SELL),
            ]
            result = await engine.vote(results, method=VotingMethod.CONSENSUS)
            assert result.direction is None

        asyncio.run(exercise())

    def test_default_method_used(self) -> None:
        async def exercise() -> None:
            engine = VotingEngine(default_method=VotingMethod.MAJORITY)
            results = [
                make_result("s1", SignalDirection.BUY),
                make_result("s2", SignalDirection.BUY),
            ]
            result = await engine.vote(results)
            assert result.method_used == VotingMethod.MAJORITY

        asyncio.run(exercise())
