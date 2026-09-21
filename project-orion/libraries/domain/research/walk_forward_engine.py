"""Institutional Walk-Forward Analysis (WFA) engine with strict chronological IS/OOS segregation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from libraries.domain.backtesting.leakage_guard import LeakageGuard
from libraries.domain.research.optimization_engine import OptimizationEngine
from libraries.domain.research.optimization_models import (
    FitnessObjective,
    ParameterSpaceDefinition,
    WalkForwardAnalysisResult,
    WalkForwardRobustness,
    WalkForwardWindowResult,
)
from libraries.domain.research.parameter_space_engine import normalize_strategy_id
from libraries.domain.strategy.registry import StrategyRegistry

logger = logging.getLogger("research.walk_forward_engine")


class WalkForwardEngine:
    """Orchestrates multi-window In-Sample optimization and Out-of-Sample validation."""

    def __init__(self, optimization_engine: OptimizationEngine | None = None) -> None:
        self.opt_engine = optimization_engine or OptimizationEngine()
        self._is_cancelled = False

    def cancel(self) -> None:
        """Cancel running walk-forward analysis."""
        self._is_cancelled = True
        self.opt_engine.cancel()

    async def run_analysis(
        self,
        strategy_id: str,
        space: ParameterSpaceDefinition,
        candidate_combinations: list[dict[str, Any]],
        candles: list[dict[str, Any]],
        symbol: str = "EUR/USD",
        timeframe: str = "H1",
        n_windows: int = 4,
        in_sample_ratio: float = 0.7,
        anchored: bool = False,
        initial_capital: Decimal = Decimal("10000.00"),
        spread_pips: Decimal = Decimal("1.5"),
        slippage_pips: Decimal = Decimal("0.5"),
        commission_per_lot: Decimal = Decimal("7.00"),
        fitness_objective: FitnessObjective = FitnessObjective.SHARPE_RATIO,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> WalkForwardAnalysisResult:
        """Execute chronological Walk-Forward Analysis across multiple windows."""
        self._is_cancelled = False
        timestamps = [c["timestamp"] for c in candles]
        LeakageGuard.assert_monotonic_timestamps(timestamps)

        total_candles = len(candles)
        min_required_candles = n_windows * 30
        if total_candles < min_required_candles:
            raise ValueError(
                f"Historical series has {total_candles} candles; need at least {min_required_candles} for {n_windows} windows"
            )
        if not 0.5 <= in_sample_ratio <= 0.85:
            raise ValueError(f"in_sample_ratio ({in_sample_ratio}) must be between 0.50 and 0.85")

        canonical_id = normalize_strategy_id(strategy_id)
        window_slices = self._partition_windows(candles, n_windows, in_sample_ratio, anchored)
        window_results: list[WalkForwardWindowResult] = []

        for w_idx, (is_candles, oos_candles) in enumerate(window_slices):
            if self._is_cancelled:
                logger.info("Walk-Forward analysis cancelled at window %d/%d", w_idx + 1, n_windows)
                break

            # 2. Strict In-Sample Optimization
            is_candidates, _ = await self.opt_engine.run_sweep(
                strategy_id=canonical_id,
                parameter_combinations=candidate_combinations,
                candles=is_candles,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital,
                spread_pips=spread_pips,
                slippage_pips=slippage_pips,
                commission_per_lot=commission_per_lot,
                fitness_objective=fitness_objective,
                parameter_space=space,
            )

            if not is_candidates:
                raise RuntimeError(f"Window {w_idx}: In-Sample optimization yielded 0 candidates")

            best_candidate = is_candidates[0]
            best_params = dict(best_candidate.parameters)

            # 3. Out-of-Sample Forward Validation
            from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter

            oos_strategy = StrategyRegistry.create_strategy(
                strategy_id=canonical_id,
                parameters=best_params,
                symbols=[symbol],
            )
            oos_adapter = StrategyBacktestAdapter(
                strategy=oos_strategy,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital,
                spread_pips=spread_pips,
                adverse_slippage_pips=slippage_pips,
                commission_per_lot=commission_per_lot,
            )

            for c in oos_candles:
                vol = c.get("volume", Decimal(0))
                vol_dec = Decimal(str(vol)) if not isinstance(vol, Decimal) else vol
                await oos_adapter.on_candle(
                    symbol=symbol,
                    timestamp=c["timestamp"],
                    open_price=c["open"],
                    high_price=c["high"],
                    low_price=c["low"],
                    close_price=c["close"],
                    volume=vol_dec,
                )

            await oos_adapter.finalize(
                final_timestamp=oos_candles[-1]["timestamp"],
                final_close=oos_candles[-1]["close"],
            )

            oos_metrics = oos_adapter.calculate_performance_metrics()
            oos_curve = oos_adapter.equity_curve

            # 4. Calculate Efficiency Ratio (WFE)
            is_ret = best_candidate.total_return
            oos_ret = oos_metrics.total_return_pct

            norm_is_ret = float(is_ret) / len(is_candles)
            norm_oos_ret = float(oos_ret) / len(oos_candles)

            if norm_is_ret > 0.00001:
                wfe: float | None = round((norm_oos_ret / norm_is_ret) * 100.0, 2)
            else:
                wfe = None

            is_metrics_dict = {
                "sharpe_ratio": best_candidate.sharpe_ratio,
                "sortino_ratio": best_candidate.sortino_ratio,
                "calmar_ratio": best_candidate.calmar_ratio,
                "win_rate": best_candidate.win_rate,
                "profit_factor": best_candidate.profit_factor,
                "max_drawdown": best_candidate.max_drawdown,
                "total_trades": best_candidate.total_trades,
                "total_return": float(is_ret),
            }

            oos_metrics_dict = {
                "sharpe_ratio": float(oos_metrics.sharpe_ratio),
                "sortino_ratio": float(oos_metrics.sortino_ratio),
                "calmar_ratio": float(getattr(oos_metrics, "calmar_ratio", None) or getattr(oos_metrics, "recovery_factor", 0.0)),
                "win_rate": float(getattr(oos_metrics, "win_rate", None) or getattr(oos_metrics, "win_rate_pct", 0.0)),
                "profit_factor": float(oos_metrics.profit_factor),
                "max_drawdown": float(oos_metrics.max_drawdown_pct),
                "total_trades": oos_metrics.total_trades,
                "total_return": float(oos_ret),
            }

            window_results.append(
                WalkForwardWindowResult(
                    window_index=w_idx,
                    is_start=is_candles[0]["timestamp"],
                    is_end=is_candles[-1]["timestamp"],
                    oos_start=oos_candles[0]["timestamp"],
                    oos_end=oos_candles[-1]["timestamp"],
                    optimal_parameters=best_params,
                    is_metrics=is_metrics_dict,
                    oos_metrics=oos_metrics_dict,
                    is_return=Decimal(str(is_ret)),
                    oos_return=Decimal(str(oos_ret)),
                    efficiency_ratio=wfe,
                    oos_equity_curve=tuple([
                        {
                            "timestamp": pt.timestamp.isoformat(),
                            "equity": float(pt.equity),
                            "drawdown": float(getattr(pt, "drawdown", None) if getattr(pt, "drawdown", None) is not None else getattr(pt, "drawdown_pct", 0.0)),
                        }
                        for pt in oos_curve
                    ]),
                )
            )

            if progress_callback:
                progress_callback(w_idx + 1, n_windows)

        return self._aggregate_wfa_results(window_results)

    def _partition_windows(
        self,
        candles: list[dict[str, Any]],
        n_windows: int,
        in_sample_ratio: float,
        anchored: bool,
    ) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
        """Split candles into chronological In-Sample and Out-of-Sample segments."""
        total = len(candles)
        step = total // (n_windows + 1)
        window_size = int(step * 2)

        partitions: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

        for i in range(n_windows):
            if anchored:
                start_idx = 0
            else:
                start_idx = i * step

            end_idx = min(total, start_idx + window_size)
            if end_idx > total or (end_idx - start_idx) < 30:
                break

            sub_candles = candles[start_idx:end_idx]
            split_point = int(len(sub_candles) * in_sample_ratio)

            is_candles = sub_candles[:split_point]
            oos_candles = sub_candles[split_point:]

            if len(is_candles) >= 15 and len(oos_candles) >= 10:
                partitions.append((is_candles, oos_candles))

        if not partitions:
            split_point = int(total * in_sample_ratio)
            partitions.append((candles[:split_point], candles[split_point:]))

        return partitions

    def _aggregate_wfa_results(
        self,
        windows: list[WalkForwardWindowResult],
    ) -> WalkForwardAnalysisResult:
        """Calculate mean WFE, annualized OOS metrics, and concatenated OOS equity curve."""
        if not windows:
            raise RuntimeError("No walk-forward windows were successfully evaluated")

        valid_wfes = [w.efficiency_ratio for w in windows if w.efficiency_ratio is not None]
        mean_wfe = sum(valid_wfes) / len(valid_wfes) if valid_wfes else None

        cum_oos_return = Decimal("0.0")
        oos_sharpes = []
        warnings: list[str] = []

        concatenated_oos_curve: list[dict[str, Any]] = []

        for w in windows:
            cum_oos_return += Decimal(str(w.oos_return))
            oos_sharpes.append(float(w.oos_metrics.get("sharpe_ratio", 0.0)))
            for pt in w.oos_equity_curve:
                concatenated_oos_curve.append({
                    "timestamp": pt["timestamp"],
                    "equity": pt["equity"],
                    "drawdown": pt["drawdown"],
                })

        mean_oos_sharpe = sum(oos_sharpes) / len(oos_sharpes) if oos_sharpes else 0.0

        if mean_wfe is None:
            verdict = WalkForwardRobustness.UNDEFINED
            warnings.append("Walk-Forward Efficiency is undefined because in-sample returns were non-positive.")
        elif mean_wfe >= 60.0 and mean_oos_sharpe >= 1.0:
            verdict = WalkForwardRobustness.ROBUST
        elif mean_wfe >= 40.0:
            verdict = WalkForwardRobustness.MODERATE
        else:
            verdict = WalkForwardRobustness.OVERFITTED
            warnings.append(f"Walk-Forward Efficiency is critically low ({mean_wfe:.1f}%); strategy exhibits severe curve-fitting.")

        if cum_oos_return < Decimal("0.0"):
            verdict = WalkForwardRobustness.OVERFITTED
            warnings.append("Cumulative Out-of-Sample return is negative; strategy failed out-of-sample forward verification.")

        return WalkForwardAnalysisResult(
            total_windows=len(windows),
            windows=tuple(windows),
            mean_wfe=mean_wfe,
            annualized_oos_return=cum_oos_return,
            annualized_oos_sharpe=round(mean_oos_sharpe, 2),
            robustness_verdict=verdict,
            concatenated_oos_equity=tuple(concatenated_oos_curve),
            warnings=tuple(warnings),
        )
