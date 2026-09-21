"""Institutional Quantitative Research & Strategy Lab Application Service.

Orchestrates strategy catalogue discovery, parameter validation, deterministic
backtesting replay, performance analytics, equity curve downsampling,
overfitting guards, multi-tenant persistence, experiment comparison, and data exports.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libraries.domain.backtesting.historical_data import (
    MarketDataServiceHistoricalProvider,
)
from libraries.domain.backtesting.models import Timeframe
from libraries.domain.backtesting.strategy_adapter import (
    StrategyBacktestAdapter,
    downsample_equity_curve,
)
from libraries.domain.market_data.normalization import (
    normalize_symbol,
    normalize_timeframe,
)
from libraries.domain.research.models import (
    ResearchExperimentStatus,
)
from libraries.domain.research.overfitting_guard import OverfittingGuard
from libraries.domain.strategy.registry import StrategyRegistry
from libraries.infrastructure.persistence.models import (
    AuditLogModel,
    ResearchExperimentModel,
)

from .entitlement_service import EntitlementService

logger = logging.getLogger("trading_engine.services.research")


class ResearchService:
    """Application service for institutional Strategy Lab and backtesting research."""

    def __init__(
        self,
        session: AsyncSession,
        entitlement_service: EntitlementService | None = None,
        market_data_service: Any | None = None,
    ) -> None:
        self.session = session
        self.entitlements = entitlement_service or EntitlementService(session)
        self.market_data_service = market_data_service
        self.historical_provider = MarketDataServiceHistoricalProvider(
            market_data_service=market_data_service
        )

    async def list_available_strategies(self) -> list[dict[str, Any]]:
        """Return the registered strategy catalogue with parameter schemas."""
        entries = StrategyRegistry.list_strategies()
        return [
            {
                "strategy_id": e.strategy_id,
                "name": e.name,
                "description": e.description,
                "category": e.category,
                "version": e.version,
                "is_deterministic": e.is_deterministic,
                "supported_instruments": list(e.supported_instruments),
                "supported_timeframes": list(e.supported_timeframes),
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.param_type,
                        "default": p.default,
                        "min": p.min_value,
                        "max": p.max_value,
                        "options": list(p.options) if p.options else None,
                        "description": p.description,
                    }
                    for p in e.parameters
                ],
            }
            for e in entries
        ]

    async def get_strategy_detail(self, strategy_id: str) -> dict[str, Any]:
        """Return detail specification for a single registered strategy."""
        entry = StrategyRegistry.get(strategy_id)
        return {
            "strategy_id": entry.strategy_id,
            "name": entry.name,
            "description": entry.description,
            "category": entry.category,
            "version": entry.version,
            "is_deterministic": entry.is_deterministic,
            "supported_instruments": list(entry.supported_instruments),
            "supported_timeframes": list(entry.supported_timeframes),
            "parameters": [
                {
                    "name": p.name,
                    "type": p.param_type,
                    "default": p.default,
                    "min": p.min_value,
                    "max": p.max_value,
                    "options": list(p.options) if p.options else None,
                    "description": p.description,
                }
                for p in entry.parameters
            ],
        }

    async def create_and_run_experiment(
        self,
        organization_id: str,
        user_id: str | None,
        strategy_id: str,
        symbol: str,
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: Decimal = Decimal("10000.00"),
        parameters: dict[str, Any] | None = None,
        spread_pips: Decimal = Decimal("1.5"),
        adverse_slippage_pips: Decimal = Decimal("0.5"),
        commission_per_lot: Decimal = Decimal("7.00"),
    ) -> ResearchExperimentModel:
        """Create, validate, execute, and persist a complete deterministic backtest experiment."""
        # 1. Validation of parameters and canonical symbols/timeframes
        canonical_sym = normalize_symbol(symbol)
        tf_enum = normalize_timeframe(timeframe)
        validated_params = StrategyRegistry.validate_parameters(strategy_id, parameters)

        if start_date >= end_date:
            raise ValueError(f"Start date ({start_date}) must precede end date ({end_date})")

        requested_days = (end_date - start_date).days
        if requested_days <= 0:
            requested_days = 1

        # 2. Entitlement Quota Enforcement
        await self.entitlements.check_daily_research_quota(
            organization_id=organization_id,
            requested_days=requested_days,
        )

        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)

        sim_config = {
            "spread_pips": float(spread_pips),
            "adverse_slippage_pips": float(adverse_slippage_pips),
            "commission_per_lot": float(commission_per_lot),
            "initial_capital": float(initial_capital),
            "deterministic": True,
        }

        experiment_id = f"exp-{uuid.uuid4().hex[:12]}"
        model = ResearchExperimentModel(
            id=experiment_id,
            organization_id=organization_id,
            created_by=user_id,
            strategy_id=strategy_id,
            strategy_version="1.0.0",
            symbol=canonical_sym,
            timeframe=tf_enum.value,
            start_date=start_dt,
            end_date=end_dt,
            initial_capital=initial_capital,
            parameters=validated_params,
            simulation_config=sim_config,
            status=ResearchExperimentStatus.RUNNING.value,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(model)
        await self.session.flush()

        # Audit event
        audit_entry = AuditLogModel(
            id=f"aud-{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            event_type="RESEARCH_EXPERIMENT_STARTED",
            component="ResearchService",
            actor=user_id,
            details={"experiment_id": experiment_id, "strategy_id": strategy_id, "symbol": canonical_sym},
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(audit_entry)

        start_wall = time.time()

        try:
            # 3. Instantiate Strategy and Adapter
            strategy = StrategyRegistry.create_strategy(
                strategy_id=strategy_id,
                parameters=validated_params,
                symbols=[canonical_sym],
            )

            adapter = StrategyBacktestAdapter(
                strategy=strategy,
                symbol=canonical_sym,
                timeframe=tf_enum.value,
                initial_capital=initial_capital,
                spread_pips=spread_pips,
                adverse_slippage_pips=adverse_slippage_pips,
                commission_per_lot=commission_per_lot,
            )

            # 4. Load Historical Market Data
            tf_domain = Timeframe(tf_enum.value) if tf_enum.value in [t.value for t in Timeframe] else Timeframe.H1
            candles = await self.historical_provider.load_candles(
                symbol=canonical_sym,
                timeframe=tf_domain,
                start_date=start_date,
                end_date=end_date,
            )

            if not candles:
                raise RuntimeError(f"No historical market data available for {canonical_sym} in selected period")

            # 5. Replay Bars Through Strategy & Accounting Engine
            for c in candles:
                await adapter.on_candle(
                    symbol=canonical_sym,
                    timestamp=c["timestamp"],
                    open_price=c["open"],
                    high_price=c["high"],
                    low_price=c["low"],
                    close_price=c["close"],
                    volume=c["volume"],
                )

            # Finalize positions at end of dataset
            await adapter.finalize(
                final_timestamp=candles[-1]["timestamp"],
                final_close=candles[-1]["close"],
            )

            # 6. Calculate Metrics & Evaluate Warnings
            perf = adapter.calculate_performance_metrics()
            warnings = OverfittingGuard.evaluate(
                metrics=perf,
                duration_days=float(requested_days),
                parameter_count=len(validated_params),
            )

            downsampled_curve = downsample_equity_curve(adapter.equity_curve, max_points=300)

            elapsed = time.time() - start_wall

            # 7. Persist Results in Model
            model.status = ResearchExperimentStatus.COMPLETED.value
            model.execution_time_seconds = round(elapsed, 3)
            model.completed_at = datetime.now(timezone.utc)
            model.metrics = {
                "initial_capital": float(perf.initial_capital),
                "final_balance": float(perf.final_balance),
                "net_profit": float(perf.net_profit),
                "total_return_pct": perf.total_return_pct,
                "gross_profit": float(perf.gross_profit),
                "gross_loss": float(perf.gross_loss),
                "profit_factor": perf.profit_factor,
                "win_rate_pct": perf.win_rate_pct,
                "loss_rate_pct": perf.loss_rate_pct,
                "total_trades": perf.total_trades,
                "winning_trades": perf.winning_trades,
                "losing_trades": perf.losing_trades,
                "avg_trade_pnl": float(perf.avg_trade_pnl),
                "largest_win": float(perf.largest_win),
                "largest_loss": float(perf.largest_loss),
                "sharpe_ratio": perf.sharpe_ratio,
                "sortino_ratio": perf.sortino_ratio,
                "max_drawdown_pct": perf.max_drawdown_pct,
                "recovery_factor": perf.recovery_factor,
                "expectancy": float(perf.expectancy),
            }
            model.equity_curve = [
                {
                    "timestamp": pt.timestamp.isoformat(),
                    "balance": float(pt.balance),
                    "equity": float(pt.equity),
                    "drawdown_pct": pt.drawdown_pct,
                }
                for pt in downsampled_curve
            ]
            model.trades = [
                {
                    "trade_id": t.trade_id,
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                    "entry_price": float(t.entry_price),
                    "exit_price": float(t.exit_price),
                    "quantity": float(t.quantity),
                    "gross_pnl": float(t.gross_pnl),
                    "fees": float(t.fees),
                    "net_pnl": float(t.net_pnl),
                    "duration_seconds": t.duration_seconds,
                    "exit_reason": t.exit_reason,
                }
                for t in adapter.trades
            ]
            model.warnings = [
                {
                    "code": w.code,
                    "title": w.title,
                    "description": w.description,
                    "severity": w.severity.value,
                }
                for w in warnings
            ]

            completion_audit = AuditLogModel(
                id=f"aud-{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                event_type="RESEARCH_EXPERIMENT_COMPLETED",
                component="ResearchService",
                actor=user_id,
                details={
                    "experiment_id": experiment_id,
                    "total_trades": perf.total_trades,
                    "net_profit": float(perf.net_profit),
                    "sharpe": perf.sharpe_ratio,
                },
                timestamp=datetime.now(timezone.utc),
            )
            self.session.add(completion_audit)

        except Exception as exc:  # noqa: BLE001
            model.status = ResearchExperimentStatus.FAILED.value
            model.error_message = str(exc)
            model.completed_at = datetime.now(timezone.utc)
            model.execution_time_seconds = round(time.time() - start_wall, 3)
            logger.error("Research experiment %s failed: %s", experiment_id, exc)

        await self.session.commit()
        await self.session.refresh(model)
        return model

    async def get_experiment(
        self,
        experiment_id: str,
        organization_id: str,
    ) -> ResearchExperimentModel:
        """Retrieve a single experiment enforcing tenant isolation."""
        stmt = select(ResearchExperimentModel).where(
            ResearchExperimentModel.id == experiment_id,
            ResearchExperimentModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        exp = result.scalar_one_or_none()
        if exp is None:
            raise KeyError(f"Research experiment '{experiment_id}' not found or inaccessible")
        return exp

    async def list_experiments(
        self,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[list[ResearchExperimentModel], int]:
        """List tenant experiments with pagination and optional status filter."""
        base_query = select(ResearchExperimentModel).where(
            ResearchExperimentModel.organization_id == organization_id
        )
        count_query = select(func.count(ResearchExperimentModel.id)).where(
            ResearchExperimentModel.organization_id == organization_id
        )

        if status:
            base_query = base_query.where(ResearchExperimentModel.status == status.upper())
            count_query = count_query.where(ResearchExperimentModel.status == status.upper())

        total_res = await self.session.execute(count_query)
        total = int(total_res.scalar() or 0)

        query = base_query.order_by(desc(ResearchExperimentModel.created_at)).offset(offset).limit(min(limit, 100))
        result = await self.session.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def cancel_experiment(
        self,
        experiment_id: str,
        organization_id: str,
        user_id: str | None = None,
    ) -> ResearchExperimentModel:
        """Cancel a running experiment."""
        exp = await self.get_experiment(experiment_id, organization_id)
        if exp.status in (ResearchExperimentStatus.COMPLETED.value, ResearchExperimentStatus.CANCELLED.value):
            return exp

        exp.status = ResearchExperimentStatus.CANCELLED.value
        exp.completed_at = datetime.now(timezone.utc)

        audit = AuditLogModel(
            id=f"aud-{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            event_type="RESEARCH_EXPERIMENT_CANCELLED",
            component="ResearchService",
            actor=user_id,
            details={"experiment_id": experiment_id},
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(audit)
        await self.session.commit()
        await self.session.refresh(exp)
        return exp

    async def compare_experiments(
        self,
        experiment_ids: list[str],
        organization_id: str,
    ) -> dict[str, Any]:
        """Compare 2-5 completed experiments side-by-side."""
        if len(experiment_ids) < 2:
            raise ValueError("Comparison requires at least 2 experiment IDs")
        if len(experiment_ids) > 5:
            raise ValueError("Comparison is limited to a maximum of 5 experiments")

        stmt = select(ResearchExperimentModel).where(
            ResearchExperimentModel.id.in_(experiment_ids),
            ResearchExperimentModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        experiments = list(result.scalars().all())

        if len(experiments) != len(set(experiment_ids)):
            raise KeyError("One or more experiment IDs not found or belonging to another organization")

        comparison_matrix = []
        normalized_equity_curves = {}

        for exp in experiments:
            metrics = exp.metrics or {}
            init_cap = float(exp.initial_capital)
            comparison_matrix.append(
                {
                    "experiment_id": exp.id,
                    "strategy_id": exp.strategy_id,
                    "symbol": exp.symbol,
                    "timeframe": exp.timeframe,
                    "status": exp.status,
                    "initial_capital": init_cap,
                    "final_balance": metrics.get("final_balance", init_cap),
                    "net_profit": metrics.get("net_profit", 0.0),
                    "total_return_pct": metrics.get("total_return_pct", 0.0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                    "sortino_ratio": metrics.get("sortino_ratio", 0.0),
                    "max_drawdown_pct": metrics.get("max_drawdown_pct", 0.0),
                    "profit_factor": metrics.get("profit_factor", 0.0),
                    "win_rate_pct": metrics.get("win_rate_pct", 0.0),
                    "total_trades": metrics.get("total_trades", 0),
                    "expectancy": metrics.get("expectancy", 0.0),
                    "parameters": exp.parameters,
                }
            )

            # Normalize equity curve to percentage return for overlay chart
            if exp.equity_curve:
                normalized_points = []
                for pt in exp.equity_curve:
                    eq = pt.get("equity", init_cap)
                    pct = ((eq - init_cap) / init_cap * 100) if init_cap > 0 else 0.0
                    normalized_points.append(
                        {
                            "timestamp": pt.get("timestamp"),
                            "return_pct": round(pct, 2),
                        }
                    )
                normalized_equity_curves[exp.id] = normalized_points

        return {
            "comparison": comparison_matrix,
            "normalized_curves": normalized_equity_curves,
        }

    async def export_experiment(
        self,
        experiment_id: str,
        organization_id: str,
        export_format: str = "json",
    ) -> tuple[str, str, str]:
        """Export experiment data in CSV or JSON format. Returns (content, media_type, filename)."""
        exp = await self.get_experiment(experiment_id, organization_id)
        fmt = export_format.lower()

        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            # Write Summary
            writer.writerow(["EXPERIMENT SUMMARY"])
            writer.writerow(["Experiment ID", exp.id])
            writer.writerow(["Strategy ID", exp.strategy_id])
            writer.writerow(["Symbol", exp.symbol])
            writer.writerow(["Timeframe", exp.timeframe])
            writer.writerow(["Initial Capital", str(exp.initial_capital)])
            writer.writerow([])

            # Write Metrics
            writer.writerow(["PERFORMANCE METRICS"])
            if exp.metrics:
                for k, v in exp.metrics.items():
                    writer.writerow([k, v])
            writer.writerow([])

            # Write Trades
            writer.writerow(["TRADE LEDGER"])
            trades = exp.trades or []
            if trades:
                headers = list(trades[0].keys())
                writer.writerow(headers)
                for t in trades:
                    writer.writerow([t.get(h) for h in headers])
            else:
                writer.writerow(["No trades recorded"])

            filename = f"experiment_{exp.id}.csv"
            return output.getvalue(), "text/csv", filename

        elif fmt == "json":
            data = {
                "id": exp.id,
                "organization_id": exp.organization_id,
                "strategy_id": exp.strategy_id,
                "strategy_version": exp.strategy_version,
                "symbol": exp.symbol,
                "timeframe": exp.timeframe,
                "start_date": exp.start_date.isoformat(),
                "end_date": exp.end_date.isoformat(),
                "initial_capital": float(exp.initial_capital),
                "parameters": exp.parameters,
                "simulation_config": exp.simulation_config,
                "status": exp.status,
                "execution_time_seconds": exp.execution_time_seconds,
                "metrics": exp.metrics,
                "equity_curve": exp.equity_curve,
                "trades": exp.trades,
                "warnings": exp.warnings,
                "created_at": exp.created_at.isoformat(),
                "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
            }
            filename = f"experiment_{exp.id}.json"
            return json.dumps(data, indent=2), "application/json", filename

        else:
            raise ValueError(f"Unsupported export format '{export_format}'. Must be 'csv' or 'json'")
