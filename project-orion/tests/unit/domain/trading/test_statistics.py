"""Tests for TradeStatistics."""

from __future__ import annotations

import asyncio

from libraries.domain.trading.signals import SignalDirection
from libraries.domain.trading.statistics import TradeOutcome, TradeStatistics, TradeStats


class TestTradeStatistics:
    def test_initial_empty_stats(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            result = await stats.get_stats()
            assert result.total_trades == 0
            assert result.win_rate == 0.0

        asyncio.run(exercise())

    def test_records_winning_trade(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(
                direction=SignalDirection.BUY,
                pnl=100.0,
                outcome=TradeOutcome.WIN,
                symbol="EUR/USD",
                strategy="swing",
            )
            result = await stats.get_stats()
            assert result.total_trades == 1
            assert result.winning_trades == 1
            assert result.win_rate == 1.0
            assert result.total_pnl == 100.0

        asyncio.run(exercise())

    def test_records_losing_trade(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(
                direction=SignalDirection.SELL,
                pnl=-50.0,
                outcome=TradeOutcome.LOSS,
                symbol="GBP/USD",
            )
            result = await stats.get_stats()
            assert result.total_trades == 1
            assert result.losing_trades == 1
            assert result.total_pnl == -50.0

        asyncio.run(exercise())

    def test_computes_win_rate(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.SELL, -50.0, TradeOutcome.LOSS)
            await stats.record_trade(SignalDirection.BUY, 200.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.BUY, 0.0, TradeOutcome.BREAK_EVEN)

            result = await stats.get_stats()
            assert result.total_trades == 4
            assert result.winning_trades == 2
            assert result.losing_trades == 1
            assert result.break_even_trades == 1
            assert result.win_rate == 0.5

        asyncio.run(exercise())

    def test_computes_profit_factor(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 300.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.SELL, -200.0, TradeOutcome.LOSS)

            result = await stats.get_stats()
            assert result.profit_factor == 2.0  # 400 / 200

        asyncio.run(exercise())

    def test_computes_average_win_loss(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.BUY, 200.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.SELL, -50.0, TradeOutcome.LOSS)
            await stats.record_trade(SignalDirection.SELL, -150.0, TradeOutcome.LOSS)

            result = await stats.get_stats()
            assert result.average_win == 150.0
            assert result.average_loss == -100.0

        asyncio.run(exercise())

    def test_clear_resets_all(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.clear()
            result = await stats.get_stats()
            assert result.total_trades == 0

        asyncio.run(exercise())

    def test_concurrent_trade_recording(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()

            async def record_win(i: int) -> None:
                await stats.record_trade(
                    SignalDirection.BUY, float(i * 10), TradeOutcome.WIN
                )

            await asyncio.gather(*[record_win(i) for i in range(10)])

            result = await stats.get_stats()
            assert result.total_trades == 10
            assert result.winning_trades == 10

        asyncio.run(exercise())

    def test_trade_outcome_enum(self) -> None:
        assert TradeOutcome.WIN == "win"
        assert TradeOutcome.LOSS == "loss"
        assert TradeOutcome.BREAK_EVEN == "break_even"
        assert TradeOutcome.OPEN == "open"

    def test_trade_stats_defaults(self) -> None:
        stats = TradeStats()
        assert stats.total_trades == 0
        assert stats.win_rate == 0.0

    def test_infinite_profit_factor(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            result = await stats.get_stats()
            assert result.profit_factor == float("inf")

        asyncio.run(exercise())

    def test_streak_tracking(self) -> None:
        async def exercise() -> None:
            stats = TradeStatistics()
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)
            await stats.record_trade(SignalDirection.SELL, -50.0, TradeOutcome.LOSS)
            await stats.record_trade(SignalDirection.BUY, 100.0, TradeOutcome.WIN)

            result = await stats.get_stats()
            assert result.best_streak >= 3
            assert result.worst_streak <= -1

        asyncio.run(exercise())
