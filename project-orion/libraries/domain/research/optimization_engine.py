"""Batch optimization execution engine evaluating strategy parameter candidates."""

from __future__ import annotations

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from libraries.domain.research.optimization_models import (
    FitnessObjective,
    OptimizationCandidate,
    ParameterSpaceDefinition,
    SensitivityHeatmapMatrix,
    SensitivityHeatmapPoint,
)
from libraries.domain.research.parameter_space_engine import normalize_strategy_id
from libraries.domain.strategy.registry import StrategyRegistry

logger = logging.getLogger("research.optimization_engine")


class OptimizationEngine:
    """Executes deterministic parameter sweeps and multi-objective ranking."""

    def __init__(self) -> None:
        self._is_cancelled = False

    def cancel(self) -> None:
        """Signal cooperative cancellation of the running sweep."""
        self._is_cancelled = True

    async def run_sweep(
        self,
        strategy_id: str,
        parameter_combinations: list[dict[str, Any]],
        candles: list[dict[str, Any]],
        symbol: str = "EUR/USD",
        timeframe: str = "H1",
        initial_capital: Decimal = Decimal("10000.00"),
        spread_pips: Decimal = Decimal("1.5"),
        slippage_pips: Decimal = Decimal("0.5"),
        commission_per_lot: Decimal = Decimal("7.00"),
        fitness_objective: FitnessObjective = FitnessObjective.SHARPE_RATIO,
        progress_callback: Callable[[int, int], None] | None = None,
        parameter_space: ParameterSpaceDefinition | None = None,
    ) -> tuple[list[OptimizationCandidate], SensitivityHeatmapMatrix | None]:
        """Execute backtest evaluations for all parameter combinations and rank them."""
        total = len(parameter_combinations)
        if total == 0:
            raise ValueError("No parameter combinations provided to optimize")
        if len(candles) < 10:
            raise ValueError(f"Insufficient historical candles ({len(candles)}) for optimization")

        canonical_id = normalize_strategy_id(strategy_id)
        raw_candidates: list[dict[str, Any]] = []

        for idx, params in enumerate(parameter_combinations):
            if self._is_cancelled:
                logger.info("Optimization sweep cancelled at index %d/%d", idx, total)
                break

            # 1. Instantiate strategy via StrategyRegistry factory
            strategy_inst = StrategyRegistry.create_strategy(
                strategy_id=canonical_id,
                parameters=params,
                symbols=[symbol],
            )

            # 2. Run deterministic backtest adapter with instant replay
            from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter

            adapter = StrategyBacktestAdapter(
                strategy=strategy_inst,
                symbol=symbol,
                timeframe=timeframe,
                initial_capital=initial_capital,
                spread_pips=spread_pips,
                adverse_slippage_pips=slippage_pips,
                commission_per_lot=commission_per_lot,
            )

            # Feed historical candles
            for c in candles:
                vol = c.get("volume", Decimal(0))
                vol_dec = Decimal(str(vol)) if not isinstance(vol, Decimal) else vol
                await adapter.on_candle(
                    symbol=symbol,
                    timestamp=c["timestamp"],
                    open_price=c["open"],
                    high_price=c["high"],
                    low_price=c["low"],
                    close_price=c["close"],
                    volume=vol_dec,
                )

            await adapter.finalize(
                final_timestamp=candles[-1]["timestamp"],
                final_close=candles[-1]["close"],
            )

            metrics = adapter.calculate_performance_metrics()

            raw_candidates.append({
                "params": params,
                "metrics": metrics,
            })

            if progress_callback:
                progress_callback(idx + 1, total)

        if not raw_candidates:
            raise RuntimeError("Optimization sweep produced 0 evaluated candidates")

        # 3. Calculate fitness scores
        candidates = self._score_and_rank_candidates(raw_candidates, fitness_objective)

        # 4. Generate 2D Heatmap Matrix if parameter space has at least 2 ranges
        heatmap = self._generate_heatmap(candidates, parameter_space)

        return candidates, heatmap

    def _score_and_rank_candidates(
        self,
        raw_candidates: list[dict[str, Any]],
        fitness_objective: FitnessObjective,
    ) -> list[OptimizationCandidate]:
        """Compute fitness scores and assign 1-indexed ranks."""
        scored: list[tuple[float, dict[str, Any]]] = []

        if fitness_objective == FitnessObjective.COMPOSITE:
            scored = self._calculate_composite_scores(raw_candidates)
        else:
            for item in raw_candidates:
                m = item["metrics"]
                m_calmar = float(getattr(m, "calmar_ratio", None) or getattr(m, "recovery_factor", 0.0))
                if fitness_objective == FitnessObjective.SHARPE_RATIO:
                    score = float(m.sharpe_ratio)
                elif fitness_objective == FitnessObjective.SORTINO_RATIO:
                    score = float(m.sortino_ratio)
                elif fitness_objective == FitnessObjective.CALMAR_RATIO:
                    score = m_calmar
                elif fitness_objective == FitnessObjective.PROFIT_FACTOR:
                    score = float(m.profit_factor)
                elif fitness_objective == FitnessObjective.TOTAL_RETURN:
                    score = float(m.total_return_pct)
                elif fitness_objective == FitnessObjective.WIN_RATE:
                    score = float(getattr(m, "win_rate", None) or getattr(m, "win_rate_pct", 0.0))
                elif fitness_objective == FitnessObjective.MIN_DRAWDOWN:
                    score = -float(m.max_drawdown_pct)
                else:
                    score = float(m.sharpe_ratio)

                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)

        ranked: list[OptimizationCandidate] = []
        for rank_idx, (fitness, item) in enumerate(scored, start=1):
            m = item["metrics"]
            m_calmar = float(getattr(m, "calmar_ratio", None) or getattr(m, "recovery_factor", 0.0))
            m_wr = float(getattr(m, "win_rate", None) or getattr(m, "win_rate_pct", 0.0))
            ranked.append(
                OptimizationCandidate(
                    rank=rank_idx,
                    parameters=item["params"],
                    fitness_score=fitness,
                    total_return=m.total_return_pct,
                    sharpe_ratio=float(m.sharpe_ratio),
                    sortino_ratio=float(m.sortino_ratio),
                    calmar_ratio=m_calmar,
                    max_drawdown=float(m.max_drawdown_pct),
                    win_rate=m_wr,
                    profit_factor=float(m.profit_factor),
                    total_trades=m.total_trades,
                    net_pnl=getattr(m, "net_pnl", None) or getattr(m, "net_profit", Decimal("0.00")),
                )
            )

        return ranked

    def _calculate_composite_scores(
        self,
        raw_candidates: list[dict[str, Any]],
    ) -> list[tuple[float, dict[str, Any]]]:
        """Normalize metrics and calculate weighted multi-objective composite score."""
        sharpes = [float(c["metrics"].sharpe_ratio) for c in raw_candidates]
        sortinos = [float(c["metrics"].sortino_ratio) for c in raw_candidates]
        calmars = [float(getattr(c["metrics"], "calmar_ratio", None) or getattr(c["metrics"], "recovery_factor", 0.0)) for c in raw_candidates]
        win_rates = [float(getattr(c["metrics"], "win_rate", None) or getattr(c["metrics"], "win_rate_pct", 0.0)) for c in raw_candidates]
        dds = [float(c["metrics"].max_drawdown_pct) for c in raw_candidates]

        def _norm(val: float, vals: list[float]) -> float:
            v_min = min(vals)
            v_max = max(vals)
            if abs(v_max - v_min) < 1e-9:
                return 0.5
            return (val - v_min) / (v_max - v_min)

        results: list[tuple[float, dict[str, Any]]] = []
        for c in raw_candidates:
            m = c["metrics"]
            m_calmar = float(getattr(m, "calmar_ratio", None) or getattr(m, "recovery_factor", 0.0))
            m_wr = float(getattr(m, "win_rate", None) or getattr(m, "win_rate_pct", 0.0))
            n_sharpe = _norm(float(m.sharpe_ratio), sharpes)
            n_sortino = _norm(float(m.sortino_ratio), sortinos)
            n_calmar = _norm(m_calmar, calmars)
            n_wr = _norm(m_wr, win_rates)
            n_dd = 1.0 - _norm(float(m.max_drawdown_pct), dds)

            composite = (
                0.30 * n_sharpe
                + 0.20 * n_sortino
                + 0.20 * n_calmar
                + 0.15 * n_wr
                + 0.15 * n_dd
            )
            results.append((round(composite, 4), c))

        return results

    def _generate_heatmap(
        self,
        candidates: list[OptimizationCandidate],
        space: ParameterSpaceDefinition | None,
    ) -> SensitivityHeatmapMatrix | None:
        """Construct 2D surface heatmap matrix for the first two parameters."""
        if not space or len(space.ranges) < 2 or not candidates:
            return None

        p1_name = space.ranges[0].name
        p2_name = space.ranges[1].name

        points: list[SensitivityHeatmapPoint] = []
        fitnesses = [c.fitness_score for c in candidates]
        min_fit = min(fitnesses) if fitnesses else 0.0
        max_fit = max(fitnesses) if fitnesses else 1.0

        for c in candidates:
            p1_val = c.parameters.get(p1_name)
            p2_val = c.parameters.get(p2_name)
            if p1_val is not None and p2_val is not None and isinstance(p1_val, (int, float)) and isinstance(p2_val, (int, float)):
                points.append(
                    SensitivityHeatmapPoint(
                        param1_value=p1_val,
                        param2_value=p2_val,
                        sharpe_ratio=c.sharpe_ratio,
                        total_return=float(c.total_return),
                        drawdown=c.max_drawdown,
                        fitness_score=c.fitness_score,
                    )
                )

        if not points:
            return None

        return SensitivityHeatmapMatrix(
            param1_name=p1_name,
            param2_name=p2_name,
            points=tuple(points),
            min_fitness=min_fit,
            max_fitness=max_fit,
        )
