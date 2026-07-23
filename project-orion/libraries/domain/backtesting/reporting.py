"""Report generators for backtesting.

Generates comprehensive reports in JSON, CSV, and HTML formats
for research, strategy, portfolio, trade, and risk analysis.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from libraries.domain.backtesting.models import (
    EquitySnapshot,
    MonteCarloResult,
    PerformanceMetrics,
    PortfolioSnapshot,
    ScenarioResult,
    WalkForwardResult,
)


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """Comprehensive research report."""

    title: str = "Backtest Research Report"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performance: dict[str, Any] = field(default_factory=dict)
    portfolio: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    scenarios: dict[str, Any] = field(default_factory=dict)
    walk_forward: dict[str, Any] = field(default_factory=dict)
    monte_carlo: dict[str, Any] = field(default_factory=dict)
    optimization: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class JsonReportGenerator:
    """Generates JSON format reports."""

    def generate_research_report(self, report: ResearchReport) -> str:
        """Generate a research report in JSON format.

        Args:
            report: Research report data.

        Returns:
            JSON string.
        """
        return json.dumps(
            {
                "title": report.title,
                "generated_at": report.generated_at.isoformat(),
                "performance": report.performance,
                "portfolio": report.portfolio,
                "risk": report.risk,
                "execution": report.execution,
                "scenarios": report.scenarios,
                "walk_forward": report.walk_forward,
                "monte_carlo": report.monte_carlo,
                "optimization": report.optimization,
                "metadata": report.metadata,
            },
            indent=2,
            default=str,
        )

    def generate_performance_report(self, metrics: PerformanceMetrics) -> str:
        return json.dumps(
            {
                "trade_metrics": {
                    "total_trades": metrics.trade_metrics.total_trades,
                    "winning_trades": metrics.trade_metrics.winning_trades,
                    "losing_trades": metrics.trade_metrics.losing_trades,
                    "win_rate": metrics.trade_metrics.win_rate,
                    "profit_factor": metrics.trade_metrics.profit_factor,
                    "net_profit": metrics.trade_metrics.net_profit,
                    "gross_profit": metrics.trade_metrics.gross_profit,
                    "gross_loss": metrics.trade_metrics.gross_loss,
                    "average_win": metrics.trade_metrics.average_win,
                    "average_loss": metrics.trade_metrics.average_loss,
                    "largest_win": metrics.trade_metrics.largest_win,
                    "largest_loss": metrics.trade_metrics.largest_loss,
                    "expectancy": metrics.trade_metrics.expectancy,
                },
                "portfolio_metrics": {
                    "sharpe_ratio": metrics.portfolio_metrics.sharpe_ratio,
                    "sortino_ratio": metrics.portfolio_metrics.sortino_ratio,
                    "calmar_ratio": metrics.portfolio_metrics.calmar_ratio,
                    "return_pct": metrics.portfolio_metrics.return_pct,
                    "total_return_pct": metrics.portfolio_metrics.total_return_pct,
                },
                "risk_metrics": {
                    "sharpe_ratio": metrics.risk_metrics.sharpe_ratio,
                    "sortino_ratio": metrics.risk_metrics.sortino_ratio,
                    "calmar_ratio": metrics.risk_metrics.calmar_ratio,
                    "total_return_pct": metrics.risk_metrics.total_return_pct,
                    "max_drawdown_pct": metrics.risk_metrics.max_drawdown_pct,
                    "max_drawdown": metrics.risk_metrics.max_drawdown,
                },
            },
            indent=2,
            default=str,
        )

    def generate_trade_report(self, trades: list[dict[str, Any]]) -> str:
        return json.dumps({"trades": trades, "total": len(trades)}, indent=2, default=str)

    def generate_risk_report(self, risk_data: dict[str, Any]) -> str:
        return json.dumps(risk_data, indent=2, default=str)

    def generate_scenario_report(self, scenarios: dict[str, ScenarioResult]) -> str:
        data = {
            name: {
                "scenario_name": s.scenario_name,
                "effects": [e.value for e in s.effects],
                "survived": s.survived,
                "impact_score": s.impact_score,
                "max_drawdown_during_scenario": s.max_drawdown_during_scenario,
                "pnl_during_scenario": s.pnl_during_scenario,
            }
            for name, s in scenarios.items()
        }
        return json.dumps(data, indent=2, default=str)


class CsvReportGenerator:
    """Generates CSV format reports."""

    def generate_trade_report(self, trades: list[dict[str, Any]]) -> str:
        if not trades:
            return "No trades"
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
        return output.getvalue()

    def generate_equity_curve(self, snapshots: list[EquitySnapshot]) -> str:
        if not snapshots:
            return "No data"
        output = io.StringIO()
        fieldnames = ["timestamp", "equity", "balance", "unrealized_pnl", "currency"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for s in snapshots:
            writer.writerow(
                {
                    "timestamp": s.timestamp.isoformat(),
                    "equity": float(s.equity),
                    "balance": float(s.balance),
                    "unrealized_pnl": float(s.unrealized_pnl),
                    "currency": s.currency,
                }
            )
        return output.getvalue()

    def generate_portfolio_snapshots(self, snapshots: list[PortfolioSnapshot]) -> str:
        if not snapshots:
            return "No data"
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "timestamp",
                "balance",
                "equity",
                "margin_used",
                "free_margin",
                "margin_level_pct",
                "realized_pnl",
                "unrealized_pnl",
                "gross_exposure",
                "net_exposure",
                "position_count",
                "portfolio_heat",
            ],
        )
        writer.writeheader()
        for s in snapshots:
            writer.writerow(
                {
                    "timestamp": s.timestamp.isoformat(),
                    "balance": float(s.balance),
                    "equity": float(s.equity),
                    "margin_used": float(s.margin_used),
                    "free_margin": float(s.free_margin),
                    "margin_level_pct": (
                        s.margin_level_pct if s.margin_level_pct != float("inf") else "INF"
                    ),
                    "realized_pnl": float(s.realized_pnl),
                    "unrealized_pnl": float(s.unrealized_pnl),
                    "gross_exposure": float(s.gross_exposure),
                    "net_exposure": float(s.net_exposure),
                    "position_count": s.position_count,
                    "portfolio_heat": s.portfolio_heat,
                }
            )
        return output.getvalue()


class HtmlReportGenerator:
    """Generates HTML format reports."""

    def generate_research_report(self, report: ResearchReport) -> str:
        """Generate a comprehensive HTML research report.

        Args:
            report: Research report data.

        Returns:
            HTML string.
        """
        perf = report.performance
        risk = report.risk
        portfolio = report.portfolio

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{report.title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
h1, h2, h3 {{ color: #333; }}
.metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin: 20px 0; }}
.metric-card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.metric-card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #666; text-transform: uppercase; }}
.metric-card .value {{ font-size: 24px; font-weight: bold; color: #333; }}
.metric-card .value.positive {{ color: #22c55e; }}
.metric-card .value.negative {{ color: #ef4444; }}
.section {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.section h2 {{ margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f8f8f8; font-weight: 600; }}
.footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 40px; }}
</style>
</head>
<body>
<h1>{report.title}</h1>
<p>Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>

<div class="section">
<h2>Performance Summary</h2>
<div class="metrics-grid">
<div class="metric-card">
<h3>Net Profit</h3>
<div class="value {'positive' if perf.get('trade_metrics', {}).get('net_profit', 0) > 0 else 'negative'}">{perf.get('trade_metrics', {}).get('net_profit', 'N/A')}</div>
</div>
<div class="metric-card">
<h3>Win Rate</h3>
<div class="value">{perf.get('trade_metrics', {}).get('win_rate', 'N/A')}</div>
</div>
<div class="metric-card">
<h3>Profit Factor</h3>
<div class="value">{perf.get('trade_metrics', {}).get('profit_factor', 'N/A')}</div>
</div>
<div class="metric-card">
<h3>Sharpe Ratio</h3>
<div class="value">{risk.get('sharpe_ratio', 'N/A')}</div>
</div>
</div>
</div>

<div class="section">
<h2>Trade Statistics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total Trades</td><td>{perf.get('trade_metrics', {}).get('total_trades', 0)}</td></tr>
<tr><td>Winning Trades</td><td>{perf.get('trade_metrics', {}).get('winning_trades', 0)}</td></tr>
<tr><td>Losing Trades</td><td>{perf.get('trade_metrics', {}).get('losing_trades', 0)}</td></tr>
<tr><td>Win Rate</td><td>{perf.get('trade_metrics', {}).get('win_rate', 0)}</td></tr>
<tr><td>Profit Factor</td><td>{perf.get('trade_metrics', {}).get('profit_factor', 0)}</td></tr>
<tr><td>Gross Profit</td><td>{perf.get('trade_metrics', {}).get('gross_profit', 0)}</td></tr>
<tr><td>Gross Loss</td><td>{perf.get('trade_metrics', {}).get('gross_loss', 0)}</td></tr>
<tr><td>Average Win</td><td>{perf.get('trade_metrics', {}).get('average_win', 0)}</td></tr>
<tr><td>Average Loss</td><td>{perf.get('trade_metrics', {}).get('average_loss', 0)}</td></tr>
<tr><td>Largest Win</td><td>{perf.get('trade_metrics', {}).get('largest_win', 0)}</td></tr>
<tr><td>Largest Loss</td><td>{perf.get('trade_metrics', {}).get('largest_loss', 0)}</td></tr>
<tr><td>Expectancy</td><td>{perf.get('trade_metrics', {}).get('expectancy', 0)}</td></tr>
</table>
</div>

<div class="section">
<h2>Risk Metrics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Sharpe Ratio</td><td>{risk.get('sharpe_ratio', 0)}</td></tr>
<tr><td>Sortino Ratio</td><td>{risk.get('sortino_ratio', 0)}</td></tr>
<tr><td>Calmar Ratio</td><td>{risk.get('calmar_ratio', 0)}</td></tr>
<tr><td>Max Drawdown (%)</td><td>{risk.get('max_drawdown_pct', 0)}</td></tr>
<tr><td>Total Return (%)</td><td>{risk.get('total_return_pct', 0)}</td></tr>
<tr><td>Ulcer Index</td><td>{report.performance.get('ulcer_index', 0)}</td></tr>
</table>
</div>

<div class="section">
<h2>Portfolio Summary</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Initial Balance</td><td>{portfolio.get('initial_balance', 0)}</td></tr>
<tr><td>Final Balance</td><td>{portfolio.get('final_balance', 0)}</td></tr>
<tr><td>Net Profit</td><td>{portfolio.get('net_profit', 0)}</td></tr>
<tr><td>Peak Balance</td><td>{portfolio.get('peak_balance', 0)}</td></tr>
<tr><td>Max Drawdown (%)</td><td>{portfolio.get('max_drawdown_pct', 0)}</td></tr>
</table>
</div>

<div class="footer">
<p>Generated by ORION Backtesting & Quantitative Research Laboratory</p>
</div>
</body>
</html>"""
        return html


class ReportManager:
    """Manages report generation across all formats."""

    def __init__(self) -> None:
        self._json_gen = JsonReportGenerator()
        self._csv_gen = CsvReportGenerator()
        self._html_gen = HtmlReportGenerator()

    @property
    def json(self) -> JsonReportGenerator:
        return self._json_gen

    @property
    def csv(self) -> CsvReportGenerator:
        return self._csv_gen

    @property
    def html(self) -> HtmlReportGenerator:
        return self._html_gen
