"""Application service orchestrating quantitative strategy optimization and walk-forward research."""

from __future__ import annotations

import csv
import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.backtesting.historical_data import (
    MarketDataServiceHistoricalProvider,
)
from libraries.domain.backtesting.leakage_guard import LeakageGuard
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import StrategyBacktestAdapter
from libraries.domain.research.optimization_engine import OptimizationEngine
from libraries.domain.research.optimization_models import (
    FitnessObjective,
    OptimizationStatus,
    OptimizationType,
    ParameterRange,
    ParameterSpaceDefinition,
    ParameterType,
)
from libraries.domain.research.parameter_space_engine import (
    ParameterSpaceEngine,
    normalize_strategy_id,
)
from libraries.domain.research.parameter_stability_analyzer import (
    ParameterStabilityAnalyzer,
)
from libraries.domain.research.regime_analyzer import RegimeAnalyzer
from libraries.domain.research.walk_forward_engine import WalkForwardEngine
from libraries.domain.strategy.registry import StrategyRegistry
from libraries.infrastructure.persistence.models.audit import AuditLogModel
from libraries.infrastructure.persistence.models.optimization import (
    OptimizationJobModel,
)

from ..schemas_optimization import (
    OptimizationCandidateResponse,
    OptimizationJobDetailResponse,
    OptimizationJobSummaryResponse,
    OptimizationRunRequest,
    ParameterRangeSchema,
    ParameterStabilityResponse,
    RegimeBreakdownResponse,
    SensitivityHeatmapResponse,
    StrategyDefaultSpaceResponse,
    WalkForwardAnalysisResponse,
    WalkForwardRunRequest,
    WalkForwardWindowResponse,
)
from .entitlement_service import EntitlementService

logger = logging.getLogger("trading_engine.services.optimization")


class OptimizationService:
    """Orchestrates strategy optimization, walk-forward analysis, quota checks, and persistence."""

    def __init__(
        self,
        session: AsyncSession,
        historical_provider: MarketDataServiceHistoricalProvider | None = None,
        entitlement_service: EntitlementService | None = None,
    ) -> None:
        self.session = session
        self.provider = historical_provider or MarketDataServiceHistoricalProvider()
        self.entitlement_service = entitlement_service or EntitlementService(session)
        self.opt_engine = OptimizationEngine()
        self.wfa_engine = WalkForwardEngine(self.opt_engine)

    def get_default_space(self, strategy_id: str) -> StrategyDefaultSpaceResponse:
        """Retrieve canonical default parameter space and bounds for an archetype."""
        try:
            space = ParameterSpaceEngine.get_default_space(strategy_id)
            est_combos = ParameterSpaceEngine.count_combinations(space)
            ranges_schema = [
                ParameterRangeSchema(
                    name=r.name,
                    param_type=r.param_type.value,
                    min_value=r.min_value,
                    max_value=r.max_value,
                    step=r.step,
                    choices=list(r.choices) if r.choices else None,
                )
                for r in space.ranges
            ]
            return StrategyDefaultSpaceResponse(
                strategy_id=strategy_id,
                ranges=ranges_schema,
                estimated_combinations=est_combos,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    async def run_optimization(
        self,
        request: OptimizationRunRequest,
        organization_id: str,
        user_id: str | None = None,
    ) -> OptimizationJobDetailResponse:
        """Launch and execute a deterministic parameter optimization sweep."""
        start_time = time.monotonic()
        job_id = f"opt-{uuid.uuid4().hex[:12]}"

        # 1. Validate Strategy
        canonical_id = normalize_strategy_id(request.strategy_id)
        try:
            StrategyRegistry.get(canonical_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy archetype '{request.strategy_id}' not found in registry",
            ) from exc

        # 2. Build and Validate Parameter Space
        space = self._resolve_parameter_space(canonical_id, request.parameter_space)
        try:
            ParameterSpaceEngine.validate_space(space)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        # 3. Generate Parameter Combinations
        opt_type = request.optimization_type.upper()
        try:
            if opt_type == "RANDOM_SEARCH":
                combos = ParameterSpaceEngine.generate_random(
                    space=space,
                    n_samples=request.n_samples,
                    random_seed=request.random_seed,
                )
            else:
                opt_type = "GRID_SEARCH"
                combos = ParameterSpaceEngine.generate_grid(
                    space=space,
                    max_combinations=request.max_combinations,
                )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        # 4. Enforce Tenant Subscription Quotas
        try:
            await self.entitlement_service.check_optimization_quota(organization_id, len(combos))
        except Exception as exc:
            from libraries.domain.subscription.exceptions import (
                DailyOptimizationQuotaExceededError,
                OptimizationCombinationLimitExceededError,
            )
            if isinstance(exc, (OptimizationCombinationLimitExceededError, DailyOptimizationQuotaExceededError)):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            raise

        # 5. Fetch Historical Candles & Enforce LeakageGuard
        try:
            try:
                tf = Timeframe(request.timeframe.lower())
            except ValueError:
                tf = Timeframe.H1

            start_d = request.start_date.date() if isinstance(request.start_date, datetime) else request.start_date
            end_d = request.end_date.date() if isinstance(request.end_date, datetime) else request.end_date

            candles = await self.provider.load_candles(
                symbol=request.symbol,
                timeframe=tf,
                start_date=start_d,
                end_date=end_d,
            )
            LeakageGuard.assert_monotonic_timestamps([c["timestamp"] for c in candles])
        except Exception as exc:
            logger.error("Historical data fetch or LeakageGuard assertion failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Historical data preparation failed: {exc}",
            ) from exc

        # 6. Parse Objective
        try:
            objective = FitnessObjective(request.fitness_objective.upper())
        except ValueError:
            objective = FitnessObjective.SHARPE_RATIO

        # 7. Record initial Job in DB
        space_dict = {
            "strategy_id": space.strategy_id,
            "ranges": [
                {
                    "name": r.name,
                    "param_type": r.param_type.value,
                    "min_value": r.min_value,
                    "max_value": r.max_value,
                    "step": r.step,
                }
                for r in space.ranges
            ],
        }
        config_dict = {
            "max_combinations": request.max_combinations,
            "n_samples": request.n_samples,
            "random_seed": request.random_seed,
            "spread_pips": float(request.spread_pips),
            "slippage_pips": float(request.slippage_pips),
            "commission": float(request.commission),
        }

        job_model = OptimizationJobModel(
            id=job_id,
            organization_id=organization_id,
            created_by=user_id,
            strategy_id=canonical_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            optimization_type=opt_type,
            fitness_objective=objective.value,
            parameter_space=space_dict,
            optimization_config=config_dict,
            status=OptimizationStatus.RUNNING.value,
            total_combinations=len(combos),
            completed_combinations=0,
            execution_time_seconds=0.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(job_model)
        await self.session.commit()

        # 8. Execute Optimization Sweep
        try:
            candidates, heatmap = await self.opt_engine.run_sweep(
                strategy_id=canonical_id,
                parameter_combinations=combos,
                candles=candles,
                symbol=request.symbol,
                timeframe=request.timeframe,
                initial_capital=request.initial_capital,
                spread_pips=request.spread_pips,
                slippage_pips=request.slippage_pips,
                commission_per_lot=request.commission,
                fitness_objective=objective,
                parameter_space=space,
            )

            # 9. Neighborhood Parameter Stability Analysis
            stability = ParameterStabilityAnalyzer.analyze_stability(
                best_candidate=candidates[0],
                all_candidates=candidates,
                space=space,
            )

            # 10. Market Regime Breakdown for Best Candidate
            best_strategy = StrategyRegistry.create_strategy(
                strategy_id=canonical_id,
                parameters=candidates[0].parameters,
                symbols=[request.symbol],
            )
            adapter = StrategyBacktestAdapter(
                strategy=best_strategy,
                symbol=request.symbol,
                timeframe=request.timeframe,
                initial_capital=request.initial_capital,
                spread_pips=request.spread_pips,
                adverse_slippage_pips=request.slippage_pips,
                commission_per_lot=request.commission,
            )
            for c in candles:
                vol = c.get("volume", Decimal(0))
                vol_dec = Decimal(str(vol)) if not isinstance(vol, Decimal) else vol
                await adapter.on_candle(
                    symbol=request.symbol,
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
            best_trades = adapter.trades
            regime_breakdowns = RegimeAnalyzer.analyze_regimes(
                candles=candles,
                trades=best_trades,
                initial_capital=request.initial_capital,
            )

            elapsed = round(time.monotonic() - start_time, 3)

            # 11. Format Payload for DB Persistence
            best_candidate = candidates[0]
            top_candidates_json = [
                {
                    "rank": c.rank,
                    "parameters": dict(c.parameters),
                    "fitness_score": c.fitness_score,
                    "total_return": float(c.total_return),
                    "sharpe_ratio": c.sharpe_ratio,
                    "sortino_ratio": c.sortino_ratio,
                    "calmar_ratio": c.calmar_ratio,
                    "max_drawdown": c.max_drawdown,
                    "win_rate": c.win_rate,
                    "profit_factor": c.profit_factor,
                    "total_trades": c.total_trades,
                    "net_pnl": float(c.net_pnl),
                }
                for c in candidates[:25]  # Persist top 25
            ]

            stability_json = {
                "optimal_parameters": dict(stability.optimal_parameters),
                "plateau_stability_score": stability.plateau_stability_score,
                "max_neighbor_drop_pct": stability.max_neighbor_drop_pct,
                "is_cliff": stability.is_cliff,
                "cliff_details": stability.cliff_details,
                "adjacent_evaluations": list(stability.adjacent_evaluations),
            }

            regimes_json = [
                {
                    "regime_name": r.regime_name,
                    "trade_count": r.trade_count,
                    "win_rate": r.win_rate,
                    "profit_factor": r.profit_factor,
                    "total_return": float(r.total_return),
                    "sharpe_ratio": r.sharpe_ratio,
                    "drawdown": r.drawdown,
                }
                for r in regime_breakdowns
            ]

            heatmap_json = (
                {
                    "param1_name": heatmap.param1_name,
                    "param2_name": heatmap.param2_name,
                    "min_fitness": heatmap.min_fitness,
                    "max_fitness": heatmap.max_fitness,
                    "points": [
                        {
                            "param1_value": p.param1_value,
                            "param2_value": p.param2_value,
                            "sharpe_ratio": p.sharpe_ratio,
                            "total_return": p.total_return,
                            "drawdown": p.drawdown,
                            "fitness_score": p.fitness_score,
                        }
                        for p in heatmap.points
                    ],
                }
                if heatmap
                else None
            )

            warnings_list = []
            if stability.is_cliff:
                warnings_list.append("PARAMETER_CLIFF: Strategy performance collapses sharply on parameter boundaries.")

            job_model.status = OptimizationStatus.COMPLETED.value
            job_model.completed_combinations = len(combos)
            job_model.execution_time_seconds = elapsed
            job_model.best_parameters = dict(best_candidate.parameters)
            job_model.best_metrics = {
                "fitness_score": best_candidate.fitness_score,
                "sharpe_ratio": best_candidate.sharpe_ratio,
                "total_return": float(best_candidate.total_return),
                "max_drawdown": best_candidate.max_drawdown,
                "profit_factor": best_candidate.profit_factor,
                "win_rate": best_candidate.win_rate,
                "total_trades": best_candidate.total_trades,
            }
            job_model.top_candidates = top_candidates_json
            job_model.stability_report = stability_json
            job_model.regime_breakdown = regimes_json
            job_model.heatmap = heatmap_json
            job_model.warnings = warnings_list
            job_model.completed_at = datetime.now(timezone.utc)
            job_model.updated_at = datetime.now(timezone.utc)

            # Audit log event
            audit = AuditLogModel(
                id=f"aud-{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                actor=user_id,
                event_type="OPTIMIZATION_EXECUTE",
                component="optimization",
                details={
                    "strategy_id": canonical_id,
                    "symbol": request.symbol,
                    "total_combinations": len(combos),
                    "best_sharpe": best_candidate.sharpe_ratio,
                },
                timestamp=datetime.now(timezone.utc),
            )
            self.session.add(audit)
            await self.session.commit()

            return self._build_job_detail_response(job_model)

        except Exception as exc:
            logger.error("Optimization execution failed for %s: %s", job_id, exc)
            job_model.status = OptimizationStatus.FAILED.value
            job_model.error_message = str(exc)
            job_model.completed_at = datetime.now(timezone.utc)
            job_model.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Optimization sweep failed: {exc}",
            ) from exc

    async def run_walk_forward(
        self,
        request: WalkForwardRunRequest,
        organization_id: str,
        user_id: str | None = None,
    ) -> OptimizationJobDetailResponse:
        """Launch and execute chronological Walk-Forward Analysis (WFA)."""
        start_time = time.monotonic()
        job_id = f"wfa-{uuid.uuid4().hex[:12]}"

        # 1. Validate Strategy
        canonical_id = normalize_strategy_id(request.strategy_id)
        try:
            StrategyRegistry.get(canonical_id)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy archetype '{request.strategy_id}' not found in registry",
            ) from exc

        # 2. Build and Validate Parameter Space
        space = self._resolve_parameter_space(canonical_id, request.parameter_space)
        try:
            ParameterSpaceEngine.validate_space(space)
            combos = ParameterSpaceEngine.generate_grid(
                space=space,
                max_combinations=request.max_combinations_per_window,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

        # 3. Enforce Quota
        try:
            await self.entitlement_service.check_optimization_quota(organization_id, len(combos))
        except Exception as exc:
            from libraries.domain.subscription.exceptions import (
                DailyOptimizationQuotaExceededError,
                OptimizationCombinationLimitExceededError,
            )
            if isinstance(exc, (OptimizationCombinationLimitExceededError, DailyOptimizationQuotaExceededError)):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
            raise

        # 4. Fetch Historical Candles & Enforce LeakageGuard
        try:
            try:
                tf = Timeframe(request.timeframe.lower())
            except ValueError:
                tf = Timeframe.H1

            start_d = request.start_date.date() if isinstance(request.start_date, datetime) else request.start_date
            end_d = request.end_date.date() if isinstance(request.end_date, datetime) else request.end_date

            candles = await self.provider.load_candles(
                symbol=request.symbol,
                timeframe=tf,
                start_date=start_d,
                end_date=end_d,
            )
            LeakageGuard.assert_monotonic_timestamps([c["timestamp"] for c in candles])
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Historical data preparation failed: {exc}",
            ) from exc

        # 5. Objective
        try:
            objective = FitnessObjective(request.fitness_objective.upper())
        except ValueError:
            objective = FitnessObjective.SHARPE_RATIO

        # 6. Record Initial DB Model
        space_dict = {
            "strategy_id": space.strategy_id,
            "ranges": [
                {"name": r.name, "param_type": r.param_type.value, "min_value": r.min_value, "max_value": r.max_value, "step": r.step}
                for r in space.ranges
            ],
        }
        config_dict = {
            "n_windows": request.n_windows,
            "in_sample_ratio": request.in_sample_ratio,
            "anchored": request.anchored,
            "max_combinations_per_window": request.max_combinations_per_window,
            "spread_pips": float(request.spread_pips),
            "slippage_pips": float(request.slippage_pips),
            "commission": float(request.commission),
        }

        job_model = OptimizationJobModel(
            id=job_id,
            organization_id=organization_id,
            created_by=user_id,
            strategy_id=canonical_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            optimization_type=OptimizationType.WALK_FORWARD.value,
            fitness_objective=objective.value,
            parameter_space=space_dict,
            optimization_config=config_dict,
            status=OptimizationStatus.RUNNING.value,
            total_combinations=len(combos) * request.n_windows,
            completed_combinations=0,
            execution_time_seconds=0.0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.session.add(job_model)
        await self.session.commit()

        # 7. Execute Walk-Forward Analysis
        try:
            wfa_result = await self.wfa_engine.run_analysis(
                strategy_id=canonical_id,
                space=space,
                candidate_combinations=combos,
                candles=candles,
                symbol=request.symbol,
                timeframe=request.timeframe,
                n_windows=request.n_windows,
                in_sample_ratio=request.in_sample_ratio,
                anchored=request.anchored,
                initial_capital=request.initial_capital,
                spread_pips=request.spread_pips,
                slippage_pips=request.slippage_pips,
                commission_per_lot=request.commission,
                fitness_objective=objective,
            )

            elapsed = round(time.monotonic() - start_time, 3)

            wfa_json = {
                "total_windows": wfa_result.total_windows,
                "mean_wfe": wfa_result.mean_wfe,
                "annualized_oos_return": float(wfa_result.annualized_oos_return),
                "annualized_oos_sharpe": wfa_result.annualized_oos_sharpe,
                "robustness_verdict": wfa_result.robustness_verdict.value,
                "concatenated_oos_equity": list(wfa_result.concatenated_oos_equity),
                "warnings": list(wfa_result.warnings),
                "windows": [
                    {
                        "window_index": w.window_index,
                        "is_start": w.is_start.isoformat(),
                        "is_end": w.is_end.isoformat(),
                        "oos_start": w.oos_start.isoformat(),
                        "oos_end": w.oos_end.isoformat(),
                        "optimal_parameters": dict(w.optimal_parameters),
                        "is_metrics": dict(w.is_metrics),
                        "oos_metrics": dict(w.oos_metrics),
                        "is_return": float(w.is_return),
                        "oos_return": float(w.oos_return),
                        "efficiency_ratio": w.efficiency_ratio,
                        "oos_equity_curve": list(w.oos_equity_curve),
                    }
                    for w in wfa_result.windows
                ],
            }

            best_w_params = dict(wfa_result.windows[-1].optimal_parameters)

            job_model.status = OptimizationStatus.COMPLETED.value
            job_model.completed_combinations = len(combos) * request.n_windows
            job_model.execution_time_seconds = elapsed
            job_model.best_parameters = best_w_params
            job_model.best_metrics = {
                "mean_wfe": wfa_result.mean_wfe,
                "oos_sharpe": wfa_result.annualized_oos_sharpe,
                "oos_return": float(wfa_result.annualized_oos_return),
                "verdict": wfa_result.robustness_verdict.value,
            }
            job_model.walk_forward_result = wfa_json
            job_model.warnings = list(wfa_result.warnings)
            job_model.completed_at = datetime.now(timezone.utc)
            job_model.updated_at = datetime.now(timezone.utc)

            audit = AuditLogModel(
                id=f"aud-{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                actor=user_id,
                event_type="OPTIMIZATION_WALK_FORWARD",
                component="optimization",
                details={
                    "strategy_id": canonical_id,
                    "n_windows": request.n_windows,
                    "verdict": wfa_result.robustness_verdict.value,
                    "mean_wfe": wfa_result.mean_wfe,
                },
                timestamp=datetime.now(timezone.utc),
            )
            self.session.add(audit)
            await self.session.commit()

            return self._build_job_detail_response(job_model)

        except Exception as exc:
            logger.error("Walk-Forward analysis failed for %s: %s", job_id, exc)
            job_model.status = OptimizationStatus.FAILED.value
            job_model.error_message = str(exc)
            job_model.completed_at = datetime.now(timezone.utc)
            job_model.updated_at = datetime.now(timezone.utc)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Walk-Forward analysis failed: {exc}",
            ) from exc

    async def list_jobs(
        self,
        organization_id: str,
        strategy_id: str | None = None,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OptimizationJobSummaryResponse]:
        """List optimization jobs for an organization with fail-closed tenant scoping."""
        stmt = select(OptimizationJobModel).where(OptimizationJobModel.organization_id == organization_id)
        if strategy_id:
            stmt = stmt.where(OptimizationJobModel.strategy_id == strategy_id)
        if status_filter:
            stmt = stmt.where(OptimizationJobModel.status == status_filter)

        stmt = stmt.order_by(OptimizationJobModel.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        summaries: list[OptimizationJobSummaryResponse] = []
        for r in rows:
            best_fit = None
            best_sh = None
            best_ret = None
            if r.best_metrics:
                best_fit = r.best_metrics.get("fitness_score")
                best_sh = r.best_metrics.get("sharpe_ratio") or r.best_metrics.get("oos_sharpe")
                best_ret = r.best_metrics.get("total_return") or r.best_metrics.get("oos_return")

            summaries.append(
                OptimizationJobSummaryResponse(
                    id=r.id,
                    organization_id=r.organization_id,
                    strategy_id=r.strategy_id,
                    symbol=r.symbol,
                    timeframe=r.timeframe,
                    optimization_type=r.optimization_type,
                    fitness_objective=r.fitness_objective,
                    status=r.status,
                    total_combinations=r.total_combinations,
                    completed_combinations=r.completed_combinations,
                    execution_time_seconds=r.execution_time_seconds,
                    best_parameters=r.best_parameters,
                    best_fitness_score=best_fit,
                    best_sharpe=best_sh,
                    best_return=best_ret,
                    created_at=r.created_at,
                    completed_at=r.completed_at,
                )
            )

        return summaries

    async def get_job(self, job_id: str, organization_id: str) -> OptimizationJobDetailResponse:
        """Fetch full job details with fail-closed IDOR prevention."""
        stmt = select(OptimizationJobModel).where(
            OptimizationJobModel.id == job_id,
            OptimizationJobModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Optimization job not found")

        return self._build_job_detail_response(job)

    async def cancel_job(self, job_id: str, organization_id: str) -> bool:
        """Cancel a running optimization job."""
        stmt = select(OptimizationJobModel).where(
            OptimizationJobModel.id == job_id,
            OptimizationJobModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Optimization job not found")

        if job.status not in (OptimizationStatus.CREATED.value, OptimizationStatus.RUNNING.value):
            return False

        self.opt_engine.cancel()
        self.wfa_engine.cancel()
        job.status = OptimizationStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    async def export_job(self, job_id: str, organization_id: str, format_type: str = "json") -> str:
        """Export optimization results to JSON or CSV."""
        job = await self.get_job(job_id, organization_id)
        if format_type.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "rank", "parameters", "fitness_score", "sharpe_ratio", "sortino_ratio",
                "calmar_ratio", "total_return_pct", "max_drawdown_pct", "win_rate",
                "profit_factor", "total_trades", "net_pnl",
            ])
            if job.top_candidates:
                for c in job.top_candidates:
                    writer.writerow([
                        c.rank,
                        json.dumps(c.parameters),
                        c.fitness_score,
                        c.sharpe_ratio,
                        c.sortino_ratio,
                        c.calmar_ratio,
                        c.total_return,
                        c.max_drawdown,
                        c.win_rate,
                        c.profit_factor,
                        c.total_trades,
                        c.net_pnl,
                    ])
            return output.getvalue()

        return job.model_dump_json(indent=2)

    def _resolve_parameter_space(
        self,
        strategy_id: str,
        custom_space: Any | None,
    ) -> ParameterSpaceDefinition:
        """Resolve parameter space from request or fall back to strategy defaults."""
        if custom_space and getattr(custom_space, "ranges", None):
            ranges = []
            for r in custom_space.ranges:
                p_type = ParameterType(r.param_type.lower())
                ranges.append(
                    ParameterRange(
                        name=r.name,
                        param_type=p_type,
                        min_value=r.min_value,
                        max_value=r.max_value,
                        step=r.step,
                        choices=tuple(r.choices) if r.choices else (),
                    )
                )
            return ParameterSpaceDefinition(strategy_id=strategy_id, ranges=tuple(ranges))

        return ParameterSpaceEngine.get_default_space(strategy_id)

    def _build_job_detail_response(self, job: OptimizationJobModel) -> OptimizationJobDetailResponse:
        """Map SQLAlchemy entity to strict Pydantic response."""
        candidates_schema = None
        if job.top_candidates:
            candidates_schema = [
                OptimizationCandidateResponse(
                    rank=c["rank"],
                    parameters=c["parameters"],
                    fitness_score=c["fitness_score"],
                    total_return=c["total_return"],
                    sharpe_ratio=c["sharpe_ratio"],
                    sortino_ratio=c["sortino_ratio"],
                    calmar_ratio=c["calmar_ratio"],
                    max_drawdown=c["max_drawdown"],
                    win_rate=c["win_rate"],
                    profit_factor=c["profit_factor"],
                    total_trades=c["total_trades"],
                    net_pnl=c["net_pnl"],
                )
                for c in job.top_candidates
            ]

        wfa_schema = None
        if job.walk_forward_result:
            wf_data = job.walk_forward_result
            windows = [
                WalkForwardWindowResponse(
                    window_index=w["window_index"],
                    is_start=datetime.fromisoformat(w["is_start"]),
                    is_end=datetime.fromisoformat(w["is_end"]),
                    oos_start=datetime.fromisoformat(w["oos_start"]),
                    oos_end=datetime.fromisoformat(w["oos_end"]),
                    optimal_parameters=w["optimal_parameters"],
                    is_metrics=w["is_metrics"],
                    oos_metrics=w["oos_metrics"],
                    is_return=w["is_return"],
                    oos_return=w["oos_return"],
                    efficiency_ratio=w["efficiency_ratio"],
                    oos_equity_curve=w.get("oos_equity_curve", []),
                )
                for w in wf_data.get("windows", [])
            ]
            wfa_schema = WalkForwardAnalysisResponse(
                total_windows=wf_data["total_windows"],
                windows=windows,
                mean_wfe=wf_data.get("mean_wfe"),
                annualized_oos_return=wf_data["annualized_oos_return"],
                annualized_oos_sharpe=wf_data["annualized_oos_sharpe"],
                robustness_verdict=wf_data["robustness_verdict"],
                concatenated_oos_equity=wf_data.get("concatenated_oos_equity", []),
                warnings=wf_data.get("warnings", []),
            )

        regimes_schema = None
        if job.regime_breakdown:
            regimes_schema = [
                RegimeBreakdownResponse(
                    regime_name=r["regime_name"],
                    trade_count=r["trade_count"],
                    win_rate=r["win_rate"],
                    profit_factor=r["profit_factor"],
                    total_return=r["total_return"],
                    sharpe_ratio=r["sharpe_ratio"],
                    drawdown=r["drawdown"],
                )
                for r in job.regime_breakdown
            ]

        stability_schema = None
        if job.stability_report:
            s_data = job.stability_report
            stability_schema = ParameterStabilityResponse(
                optimal_parameters=s_data["optimal_parameters"],
                plateau_stability_score=s_data["plateau_stability_score"],
                max_neighbor_drop_pct=s_data["max_neighbor_drop_pct"],
                is_cliff=s_data["is_cliff"],
                cliff_details=s_data["cliff_details"],
                adjacent_evaluations=s_data.get("adjacent_evaluations", []),
            )

        heatmap_schema = None
        if job.heatmap:
            h_data = job.heatmap
            heatmap_schema = SensitivityHeatmapResponse(
                param1_name=h_data["param1_name"],
                param2_name=h_data["param2_name"],
                min_fitness=h_data["min_fitness"],
                max_fitness=h_data["max_fitness"],
                points=h_data.get("points", []),
            )

        return OptimizationJobDetailResponse(
            id=job.id,
            organization_id=job.organization_id,
            strategy_id=job.strategy_id,
            symbol=job.symbol,
            timeframe=job.timeframe,
            start_date=job.start_date,
            end_date=job.end_date,
            initial_capital=float(job.initial_capital),
            optimization_type=job.optimization_type,
            fitness_objective=job.fitness_objective,
            parameter_space=job.parameter_space,
            optimization_config=job.optimization_config,
            status=job.status,
            total_combinations=job.total_combinations,
            completed_combinations=job.completed_combinations,
            execution_time_seconds=job.execution_time_seconds,
            best_parameters=job.best_parameters,
            best_metrics=job.best_metrics,
            top_candidates=candidates_schema,
            walk_forward_result=wfa_schema,
            regime_breakdowns=regimes_schema,
            stability_analysis=stability_schema,
            heatmap=heatmap_schema,
            warnings=job.warnings,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
