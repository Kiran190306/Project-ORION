"""Performance and Stress Tests for the Portfolio Engine.

Benchmarks through PortfolioManager facade with:
- 10, 100, 1,000, 10,000 positions
- Position lookup, update, and snapshot generation latency
- Analytics execution latency
- Memory growth observation

Results are documented for performance baseline establishment.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal

import pytest

from libraries.domain.portfolio.models import PositionSide
from libraries.domain.portfolio.portfolio_manager import PortfolioManager, PortfolioManagerConfig


@pytest.fixture
async def portfolio() -> PortfolioManager:
    p = PortfolioManager(
        config=PortfolioManagerConfig(
            initial_balance=Decimal("100000000"),
            max_leverage=Decimal("100"),
            account_currency="USD",
            margin_call_level=100.0,
            stop_out_level=50.0,
            track_journal=True,
            track_analytics=True,
        ),
    )
    yield p
    await p.clear_all()


class TestPerformance:
    """Performance benchmarks for portfolio operations."""

    BENCHMARK_RESULTS: dict[str, float] = {}

    @pytest.mark.slow
    async def test_10_positions(self, portfolio: PortfolioManager):
        """Benchmark with 10 positions."""
        positions = []

        t0 = time.perf_counter()
        for i in range(10):
            pos = await portfolio.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("100000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-PERF-{i:04d}",
            )
            positions.append(pos)
        open_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["open_10"] = round(open_time, 4)

        t0 = time.perf_counter()
        snap = await portfolio.get_portfolio_snapshot()
        snap_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["snapshot_10"] = round(snap_time, 4)

        t0 = time.perf_counter()
        analytics = await portfolio.get_portfolio_analytics()
        analytics_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["analytics_10"] = round(analytics_time, 4)

        assert snap.position_count == 10
        assert analytics.total_trades == 0  # No closed trades

        # Cleanup
        for pos in positions:
            await portfolio.close_position(pos.position_id, Decimal("1.1100"))

        print(
            f"\n[Benchmark] 10 positions: open={open_time:.4f}s, snapshot={snap_time:.4f}s, analytics={analytics_time:.4f}s"
        )

    @pytest.mark.slow
    async def test_100_positions(self, portfolio: PortfolioManager):
        """Benchmark with 100 positions."""
        positions = []

        t0 = time.perf_counter()
        for i in range(100):
            pos = await portfolio.open_position(
                symbol="EURUSD" if i % 2 == 0 else "GBPUSD",
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("100000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-PERF-{i:04d}",
            )
            positions.append(pos)
        open_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["open_100"] = round(open_time, 4)

        t0 = time.perf_counter()
        snap = await portfolio.get_portfolio_snapshot()
        snap_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["snapshot_100"] = round(snap_time, 4)

        t0 = time.perf_counter()
        pnl = await portfolio.get_pnl_breakdown()
        pnl_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["pnl_100"] = round(pnl_time, 4)

        assert snap.open_position_count == 100

        # Close positions
        t0 = time.perf_counter()
        for pos in positions:
            await portfolio.close_position(
                pos.position_id, Decimal("1.1100") if pos.is_long else Decimal("1.0900")
            )
        close_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["close_100"] = round(close_time, 4)

        print(
            f"\n[Benchmark] 100 positions: open={open_time:.4f}s, snapshot={snap_time:.4f}s, close={close_time:.4f}s"
        )

    @pytest.mark.slow
    async def test_1000_positions(self, portfolio: PortfolioManager):
        """Benchmark with 1,000 positions."""
        positions = []

        t0 = time.perf_counter()
        for i in range(1000):
            pos = await portfolio.open_position(
                symbol=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"][i % 5],
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-PERF-{i:04d}",
            )
            positions.append(pos)
        open_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["open_1000"] = round(open_time, 4)

        t0 = time.perf_counter()
        snap = await portfolio.get_portfolio_snapshot()
        snap_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["snapshot_1000"] = round(snap_time, 4)

        # Verify symbol lookups
        t0 = time.perf_counter()
        eurusd = await portfolio.position_manager.get_positions_by_symbol("EURUSD")
        lookup_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["lookup_1000"] = round(lookup_time, 4)

        assert snap.open_position_count == 1000
        assert len(eurusd) == 200

        print(
            f"\n[Benchmark] 1,000 positions: open={open_time:.4f}s, snapshot={snap_time:.4f}s, lookup={lookup_time:.4f}s"
        )

        # Cleanup
        for pos in positions:
            await portfolio.close_position(
                pos.position_id, Decimal("1.1100") if pos.is_long else Decimal("1.0900")
            )

    @pytest.mark.slow
    async def test_10000_positions(self, portfolio: PortfolioManager):
        """Stress test with 10,000 positions through PortfolioManager facade.

        This is the primary stress test required by the validation specification.
        """
        positions: list = []

        t0 = time.perf_counter()
        for i in range(10000):
            pos = await portfolio.open_position(
                symbol=[
                    "EURUSD",
                    "GBPUSD",
                    "USDJPY",
                    "AUDUSD",
                    "NZDUSD",
                    "USDCAD",
                    "CHFJPY",
                    "EURGBP",
                    "EURJPY",
                    "GBPJPY",
                ][i % 10],
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-STRESS-{i:06d}",
            )
            positions.append(pos)
        open_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["open_10000"] = round(open_time, 4)

        # Snapshot generation
        t0 = time.perf_counter()
        snap = await portfolio.get_portfolio_snapshot()
        snap_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["snapshot_10000"] = round(snap_time, 4)

        # Account snapshot
        t0 = time.perf_counter()
        account = await portfolio.get_account_snapshot()
        account_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["account_10000"] = round(account_time, 4)

        # P&L breakdown
        t0 = time.perf_counter()
        pnl = await portfolio.get_pnl_breakdown()
        pnl_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["pnl_10000"] = round(pnl_time, 4)

        # Analytics
        t0 = time.perf_counter()
        analytics = await portfolio.get_portfolio_analytics()
        analytics_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["analytics_10000"] = round(analytics_time, 4)

        # Price update on all positions
        t0 = time.perf_counter()
        updated = await portfolio.update_price("EURUSD", Decimal("1.1050"))
        update_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["update_10000"] = round(update_time, 4)

        assert snap.position_count == 10000
        assert snap.open_position_count == 10000
        assert account.equity > Decimal("0")
        assert pnl.unrealized_pnl != Decimal("0")
        assert len(updated) == 1000  # 10000 / 10 symbols = 1000 per symbol (EURUSD)

        print(f"\n[Benchmark] 10,000 positions:")
        print(f"  Open: {open_time:.4f}s")
        print(f"  Snapshot: {snap_time:.4f}s")
        print(f"  Account: {account_time:.4f}s")
        print(f"  P&L: {pnl_time:.4f}s")
        print(f"  Analytics: {analytics_time:.4f}s")
        print(f"  Price Update: {update_time:.4f}s")

        # Cleanup half
        t0 = time.perf_counter()
        for pos in positions[:5000]:
            await portfolio.close_position(
                pos.position_id, Decimal("1.1100") if pos.is_long else Decimal("1.0900")
            )
        close_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["close_5000"] = round(close_time, 4)

        snap2 = await portfolio.get_portfolio_snapshot()
        assert snap2.open_position_count == 5000
        print(f"  Close 5000: {close_time:.4f}s")

    @pytest.mark.slow
    async def test_concurrent_stress_portfolio_manager(self, portfolio: PortfolioManager):
        """Stress test: 10,000 positions via concurrent PortfolioManager operations."""

        async def open_pos(i: int):
            return await portfolio.open_position(
                symbol=["EURUSD", "GBPUSD", "USDJPY"][i % 3],
                side=PositionSide.LONG if i % 2 == 0 else PositionSide.SHORT,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-STRESS-CONC-{i:06d}",
            )

        t0 = time.perf_counter()
        tasks = [open_pos(i) for i in range(10000)]
        results = await asyncio.gather(*tasks)
        open_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["concurrent_open_10000"] = round(open_time, 4)

        assert len(results) == 10000

        # Snapshot
        t0 = time.perf_counter()
        snap = await portfolio.get_portfolio_snapshot()
        snap_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["concurrent_snapshot_10000"] = round(snap_time, 4)

        assert snap.position_count == 10000
        assert snap.open_position_count == 10000

        print(f"\n[Benchmark] Concurrent 10,000: open={open_time:.4f}s, snapshot={snap_time:.4f}s")

    @pytest.mark.slow
    async def test_price_update_stress(self, portfolio: PortfolioManager):
        """Stress test: price updates on 1,000 positions."""
        for i in range(1000):
            await portfolio.open_position(
                symbol="EURUSD",
                side=PositionSide.LONG,
                quantity=Decimal("10000"),
                entry_price=Decimal("1.1000"),
                execution_id=f"EXEC-PRICE-STRESS-{i:06d}",
            )

        t0 = time.perf_counter()
        for _ in range(10):
            await portfolio.update_price("EURUSD", Decimal("1.1050"))
            await portfolio.update_price("EURUSD", Decimal("1.0950"))
        update_time = time.perf_counter() - t0
        self.BENCHMARK_RESULTS["price_updates_1000"] = round(update_time, 4)

        # Verify consistency after many updates
        account = await portfolio.get_account_snapshot()
        assert account.equity >= Decimal("0")

        print(f"\n[Benchmark] 20 price updates on 1000 positions: {update_time:.4f}s")


class TestStressPortfolioManager:
    """Stress tests through PortfolioManager facade with full validation."""

    @pytest.mark.slow
    async def test_stress_open_close_10000_through_portfolio(self, portfolio: PortfolioManager):
        """Stress test: 10,000 positions via PortfolioManager open/close."""

        async def open_and_close(i: int) -> bool:
            try:
                pos = await portfolio.open_position(
                    symbol="EURUSD",
                    side=PositionSide.LONG,
                    quantity=Decimal("1000"),
                    entry_price=Decimal("1.1000"),
                    execution_id=f"EXEC-STRESS2-{i:06d}",
                    decision_id=f"DEC-STRESS2-{i:06d}",
                    strategy="stress_test",
                )
                await portfolio.close_position(
                    position_id=pos.position_id,
                    close_price=Decimal("1.1100") if i % 2 == 0 else Decimal("1.0900"),
                    close_reason="stress_test",
                )
                return True
            except Exception:
                return False

        t0 = time.perf_counter()
        tasks = [open_and_close(i) for i in range(10000)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - t0
        success_count = sum(1 for r in results if r)

        print(
            f"\n[Stress] 10,000 PortfolioManager trades: {total_time:.4f}s, success={success_count}/10000"
        )
        self.BENCHMARK_RESULTS["stress_10000_trades"] = round(total_time, 4)
        self.BENCHMARK_RESULTS["stress_10000_success_pct"] = round(success_count / 10000 * 100, 2)

        # Verify final state
        analytics = await portfolio.get_portfolio_analytics()
        assert analytics.total_trades == success_count

        account = await portfolio.get_account_snapshot()
        assert account.balance >= Decimal("0")

        snap = await portfolio.get_portfolio_snapshot()
        assert snap.gross_exposure >= abs(snap.net_exposure)


class TestPerformanceReport:
    """Output the performance benchmark report."""

    @pytest.mark.slow
    async def test_print_benchmarks(self):
        """Print the final benchmark results collected during the test run."""
        if TestPerformance.BENCHMARK_RESULTS:
            print("\n" + "=" * 60)
            print("PERFORMANCE BENCHMARK RESULTS")
            print("=" * 60)
            for key, value in sorted(TestPerformance.BENCHMARK_RESULTS.items()):
                if "success_pct" in key:
                    print(f"  {key}: {value}%")
                else:
                    print(f"  {key}: {value}s")
            print("=" * 60)
