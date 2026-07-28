"""Tests for EPIC-010 report generators (JSON, CSV, HTML)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from libraries.domain.backtesting.models import (
    EquitySnapshot,
    MonteCarloResult,
    PerformanceMetrics,
    PortfolioMetrics,
    PortfolioSnapshot,
    RiskMetrics,
    ScenarioResult,
    StatisticalMetrics,
    TradeMetrics,
    WalkForwardResult,
)
from libraries.domain.backtesting.reporting import (
    CsvReportGenerator,
    HtmlReportGenerator,
    JsonReportGenerator,
    ReportManager,
    ResearchReport,
)


class TestResearchReport:
    """Test ResearchReport dataclass."""

    def test_default_report(self):
        report = ResearchReport()
        assert report.title == "Backtest Research Report"
        assert report.generated_at is not None
        assert report.performance == {}
        assert report.portfolio == {}

    def test_custom_report(self):
        report = ResearchReport(
            title="Custom Report",
            performance={"sharpe": 1.5},
            metadata={"version": "1.0"},
        )
        assert report.title == "Custom Report"
        assert report.performance["sharpe"] == 1.5
        assert report.metadata["version"] == "1.0"

    def test_report_frozen(self):
        report = ResearchReport()
        with pytest.raises(AttributeError):
            report.title = "New Title"  # type: ignore[misc]


class TestJsonReportGenerator:
    """Test JSON report generation."""

    def test_research_report_json(self):
        gen = JsonReportGenerator()
        report = ResearchReport(
            title="Test Report",
            performance={"net_profit": 1000.0},
            risk={"sharpe_ratio": 1.5},
        )
        json_str = gen.generate_research_report(report)
        data = json.loads(json_str)
        assert data["title"] == "Test Report"
        assert data["performance"]["net_profit"] == 1000.0
        assert data["risk"]["sharpe_ratio"] == 1.5
        assert "generated_at" in data

    def test_performance_report_json(self):
        gen = JsonReportGenerator()
        tm = TradeMetrics(
            total_trades=10, winning_trades=7, win_rate=0.7, profit_factor=2.5, net_profit=1000.0
        )
        pm = PortfolioMetrics(
            sharpe_ratio=1.5, sortino_ratio=2.0, calmar_ratio=1.0, return_pct=10.0
        )
        rm = RiskMetrics(
            sharpe_ratio=1.5, sortino_ratio=2.0, calmar_ratio=1.0, max_drawdown_pct=5.0
        )
        perf = PerformanceMetrics(trade_metrics=tm, portfolio_metrics=pm, risk_metrics=rm)

        json_str = gen.generate_performance_report(perf)
        data = json.loads(json_str)
        assert data["trade_metrics"]["total_trades"] == 10
        assert data["trade_metrics"]["win_rate"] == 0.7
        assert data["portfolio_metrics"]["sharpe_ratio"] == 1.5
        assert data["risk_metrics"]["max_drawdown_pct"] == 5.0

    def test_trade_report_json(self):
        gen = JsonReportGenerator()
        trades = [
            {"pnl": 100.0, "symbol": "EURUSD"},
            {"pnl": -50.0, "symbol": "GBPUSD"},
        ]
        json_str = gen.generate_trade_report(trades)
        data = json.loads(json_str)
        assert data["total"] == 2
        assert len(data["trades"]) == 2

    def test_empty_trade_report(self):
        gen = JsonReportGenerator()
        json_str = gen.generate_trade_report([])
        data = json.loads(json_str)
        assert data["total"] == 0
        assert data["trades"] == []

    def test_risk_report_json(self):
        gen = JsonReportGenerator()
        risk_data = {"var_95": 1000.0, "max_loss": 5000.0}
        json_str = gen.generate_risk_report(risk_data)
        data = json.loads(json_str)
        assert data["var_95"] == 1000.0

    def test_empty_risk_report(self):
        gen = JsonReportGenerator()
        json_str = gen.generate_risk_report({})
        data = json.loads(json_str)
        assert data == {}

    def test_scenario_report_json(self):
        gen = JsonReportGenerator()
        scenarios = {
            "crash": ScenarioResult(
                scenario_name="flash_crash",
                effects=(),
                survived=True,
                impact_score=0.5,
                max_drawdown_during_scenario=10.0,
                pnl_during_scenario=-500.0,
            ),
        }
        json_str = gen.generate_scenario_report(scenarios)
        data = json.loads(json_str)
        assert data["crash"]["scenario_name"] == "flash_crash"
        assert data["crash"]["survived"] is True
        assert data["crash"]["impact_score"] == 0.5

    def test_empty_scenario_report(self):
        gen = JsonReportGenerator()
        json_str = gen.generate_scenario_report({})
        data = json.loads(json_str)
        assert data == {}

    def test_json_indentation(self):
        gen = JsonReportGenerator()
        report = ResearchReport(title="Indent Test")
        json_str = gen.generate_research_report(report)
        # Verify it's properly indented
        lines = json_str.split("\n")
        assert any(line.startswith("  ") for line in lines)


class TestCsvReportGenerator:
    """Test CSV report generation."""

    def test_trade_report_csv(self):
        gen = CsvReportGenerator()
        trades = [
            {"pnl": 100.0, "symbol": "EURUSD", "qty": 1},
            {"pnl": -50.0, "symbol": "GBPUSD", "qty": 2},
        ]
        csv_str = gen.generate_trade_report(trades)
        assert "pnl" in csv_str
        assert "EURUSD" in csv_str
        assert "100.0" in csv_str

    def test_empty_trade_report_csv(self):
        gen = CsvReportGenerator()
        csv_str = gen.generate_trade_report([])
        assert csv_str == "No trades"

    def test_equity_curve_csv(self):
        gen = CsvReportGenerator()
        ts = datetime.now(timezone.utc)
        snapshots = [
            EquitySnapshot(
                timestamp=ts,
                equity=Decimal("10000"),
                balance=Decimal("10000"),
                unrealized_pnl=Decimal("0"),
                currency="USD",
            ),
            EquitySnapshot(
                timestamp=ts,
                equity=Decimal("11000"),
                balance=Decimal("10500"),
                unrealized_pnl=Decimal("500"),
                currency="USD",
            ),
        ]
        csv_str = gen.generate_equity_curve(snapshots)
        assert "timestamp" in csv_str
        assert "10000" in csv_str
        assert "11000" in csv_str

    def test_empty_equity_curve_csv(self):
        gen = CsvReportGenerator()
        csv_str = gen.generate_equity_curve([])
        assert csv_str == "No data"

    def test_portfolio_snapshots_csv(self):
        gen = CsvReportGenerator()
        ts = datetime.now(timezone.utc)
        snapshots = [
            PortfolioSnapshot(
                timestamp=ts,
                balance=Decimal("10000"),
                equity=Decimal("10000"),
                margin_used=Decimal("0"),
                free_margin=Decimal("10000"),
                realized_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                gross_exposure=Decimal("0"),
                net_exposure=Decimal("0"),
                position_count=0,
                portfolio_heat=0.0,
            ),
        ]
        csv_str = gen.generate_portfolio_snapshots(snapshots)
        assert "balance" in csv_str
        assert "10000" in csv_str

    def test_empty_portfolio_snapshots_csv(self):
        gen = CsvReportGenerator()
        csv_str = gen.generate_portfolio_snapshots([])
        assert csv_str == "No data"


class TestHtmlReportGenerator:
    """Test HTML report generation."""

    def test_research_report_html(self):
        gen = HtmlReportGenerator()
        report = ResearchReport(
            title="HTML Test",
            performance={
                "trade_metrics": {
                    "net_profit": 5000,
                    "win_rate": 0.65,
                    "profit_factor": 2.0,
                    "total_trades": 50,
                    "winning_trades": 33,
                    "losing_trades": 17,
                    "gross_profit": 10000,
                    "gross_loss": 5000,
                    "average_win": 303.03,
                    "average_loss": 294.12,
                    "largest_win": 1000,
                    "largest_loss": -500,
                    "expectancy": 150,
                },
            },
            risk={
                "sharpe_ratio": 1.5,
                "sortino_ratio": 2.0,
                "calmar_ratio": 1.0,
                "max_drawdown_pct": 10.0,
                "total_return_pct": 25.0,
            },
            portfolio={
                "initial_balance": 10000,
                "final_balance": 15000,
                "net_profit": 5000,
                "peak_balance": 16000,
                "max_drawdown_pct": 10.0,
            },
        )
        html = gen.generate_research_report(report)
        assert "<!DOCTYPE html>" in html
        assert "HTML Test" in html
        assert "Performance Summary" in html
        assert "Trade Statistics" in html
        assert "Risk Metrics" in html
        assert "Portfolio Summary" in html

    def test_html_empty_report(self):
        gen = HtmlReportGenerator()
        report = ResearchReport()
        html = gen.generate_research_report(report)
        assert "<!DOCTYPE html>" in html
        assert "Backtest Research Report" in html
        assert "N/A" in html  # Missing performance values

    def test_html_positive_negative_colors(self):
        gen = HtmlReportGenerator()
        report = ResearchReport(
            performance={"trade_metrics": {"net_profit": 5000}},
            risk={},
            portfolio={},
        )
        html = gen.generate_research_report(report)
        assert "positive" in html

        report_neg = ResearchReport(
            performance={"trade_metrics": {"net_profit": -1000}},
            risk={},
            portfolio={},
        )
        html_neg = gen.generate_research_report(report_neg)
        assert "negative" in html_neg


class TestReportManager:
    """Test the composite ReportManager."""

    def test_manager_initialization(self):
        mgr = ReportManager()
        assert mgr.json is not None
        assert mgr.csv is not None
        assert mgr.html is not None

    def test_json_generator_type(self):
        mgr = ReportManager()
        assert isinstance(mgr.json, JsonReportGenerator)

    def test_csv_generator_type(self):
        mgr = ReportManager()
        assert isinstance(mgr.csv, CsvReportGenerator)

    def test_html_generator_type(self):
        mgr = ReportManager()
        assert isinstance(mgr.html, HtmlReportGenerator)

    def test_json_from_manager(self):
        mgr = ReportManager()
        report = ResearchReport(title="Manager Test")
        json_str = mgr.json.generate_research_report(report)
        data = json.loads(json_str)
        assert data["title"] == "Manager Test"

    def test_csv_from_manager(self):
        mgr = ReportManager()
        ts = datetime.now(timezone.utc)
        snapshots = [
            EquitySnapshot(
                timestamp=ts,
                equity=Decimal("10000"),
                balance=Decimal("10000"),
                unrealized_pnl=Decimal("0"),
            ),
        ]
        csv_str = mgr.csv.generate_equity_curve(snapshots)
        assert "10000" in csv_str

    def test_html_from_manager(self):
        mgr = ReportManager()
        report = ResearchReport(title="Manager HTML")
        html = mgr.html.generate_research_report(report)
        assert "Manager HTML" in html
