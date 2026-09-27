import React, { useState, useCallback } from 'react';
import { RefreshCw, AlertCircle, PieChart, TrendingUp, DollarSign, Layers } from 'lucide-react';
import { portfolioApi } from '../api/endpoints';
import type {
  PortfolioOverviewResponse,
  EquityCurveResponse,
  PnLBreakdownResponse,
  ExposureResponse,
  MultiStrategyPortfolioResponse,
  StrategyPortfolioItem,
} from '../api/types';
import { usePolling } from '../hooks/usePolling';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { EquityCurveChart } from '../components/charts/EquityCurveChart';
import { ExposureBarChart } from '../components/charts/ExposureBarChart';
import { Table, Column } from '../components/common/Table';
import { formatCurrency, formatPnl, formatPercent } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';
import type { CurrencyExposure } from '../api/types';

export const PortfolioPage: React.FC = () => {
  const [overview, setOverview] = useState<PortfolioOverviewResponse | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurveResponse | null>(null);
  const [pnl, setPnl] = useState<PnLBreakdownResponse | null>(null);
  const [exposure, setExposure] = useState<ExposureResponse | null>(null);
  const [strategyBreakdown, setStrategyBreakdown] = useState<MultiStrategyPortfolioResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPortfolio = useCallback(async () => {
    try {
      const [o, eq, p, exp, sb] = await Promise.all([
        portfolioApi.getOverview(),
        portfolioApi.getEquityCurve(),
        portfolioApi.getPnL(),
        portfolioApi.getExposure(),
        portfolioApi.getStrategyBreakdown().catch(() => null),
      ]);
      setOverview(o);
      setEquityCurve(eq);
      setPnl(p);
      setExposure(exp);
      setStrategyBreakdown(sb || null);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  usePolling(fetchPortfolio, 10000);

  if (isLoading && !overview) {
    return (
      <div className="space-y-6">
        <div className="h-6 bg-slate-800 rounded w-48 animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-900 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-slate-900 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="py-16 text-center">
        <AlertCircle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h2 className="text-base font-semibold text-slate-200">Portfolio Data Unavailable</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto mb-6">{error}</p>
        <Button variant="secondary" onClick={() => { setIsLoading(true); fetchPortfolio(); }}>
          <RefreshCw className="w-4 h-4 mr-1.5" />
          Retry
        </Button>
      </div>
    );
  }

  const currencyColumns: Column<CurrencyExposure>[] = [
    {
      header: 'Currency',
      accessor: 'currency',
      className: 'font-bold font-mono text-slate-200',
    },
    {
      header: 'Long Exposure',
      render: (item) => formatCurrency(item.long_exposure, item.currency, 0),
      className: 'font-mono text-emerald-400',
    },
    {
      header: 'Short Exposure',
      render: (item) => formatCurrency(item.short_exposure, item.currency, 0),
      className: 'font-mono text-rose-400',
    },
    {
      header: 'Net Exposure',
      render: (item) => {
        const net = typeof item.net_exposure === 'string' ? parseFloat(item.net_exposure) : item.net_exposure;
        return (
          <span className={net >= 0 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
            {net >= 0 ? '+' : ''}
            {formatCurrency(net, item.currency, 0)}
          </span>
        );
      },
      className: 'font-mono',
    },
    {
      header: 'Positions',
      accessor: 'position_count',
      className: 'font-mono text-slate-400',
    },
  ];

  const strategyColumns: Column<StrategyPortfolioItem>[] = [
    {
      header: 'Strategy',
      render: (item) => (
        <div>
          <div className="font-bold text-slate-100">{item.strategy_name || item.strategy_id}</div>
          <div className="text-[10px] text-slate-500 font-mono">{item.strategy_id}</div>
        </div>
      ),
    },
    {
      header: 'Lifecycle State',
      render: (item) => {
        switch (item.deployment_status) {
          case 'PROMOTION_CANDIDATE':
            return <Badge variant="success">PROMOTION CANDIDATE</Badge>;
          case 'PAPER_VALIDATED':
            return <Badge variant="success">PAPER VALIDATED</Badge>;
          case 'INCUBATING':
            return <Badge variant="info">INCUBATING</Badge>;
          case 'GATES_PASSED':
            return <Badge variant="info">GATES PASSED</Badge>;
          case 'PENDING_GATES':
            return <Badge variant="warning">PENDING GATES</Badge>;
          default:
            return <Badge variant="buy">ACTIVE</Badge>;
        }
      },
    },
    {
      header: 'Open Positions',
      render: (item) => <span className="font-mono">{item.open_positions_count}</span>,
    },
    {
      header: 'Orders',
      render: (item) => <span className="font-mono">{item.total_orders_count}</span>,
    },
    {
      header: 'Gross Exposure',
      render: (item) => (
        <span className="font-mono">
          {formatCurrency(item.gross_exposure, strategyBreakdown?.currency || 'USD')}
        </span>
      ),
    },
    {
      header: 'Unrealized P&L',
      render: (item) => {
        const pnl = formatPnl(item.unrealized_pnl, strategyBreakdown?.currency || 'USD');
        return (
          <span
            className={`font-mono font-semibold ${
              pnl.isPositive ? 'text-emerald-400' : pnl.isNegative ? 'text-rose-400' : 'text-slate-300'
            }`}
          >
            {pnl.formatted}
          </span>
        );
      },
    },
    {
      header: 'Realized P&L',
      render: (item) => {
        const pnl = formatPnl(item.realized_pnl, strategyBreakdown?.currency || 'USD');
        return (
          <span
            className={`font-mono font-semibold ${
              pnl.isPositive ? 'text-emerald-400' : pnl.isNegative ? 'text-rose-400' : 'text-slate-300'
            }`}
          >
            {pnl.formatted}
          </span>
        );
      },
    },
    {
      header: 'Win Rate',
      render: (item) => (
        <span className="font-mono">
          {item.win_rate !== null && item.win_rate !== undefined ? (
            `${(item.win_rate * (item.win_rate <= 1.0 ? 100 : 1)).toFixed(1)}%`
          ) : (
            <span className="text-slate-500">N/A</span>
          )}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              PORTFOLIO ANALYTICS
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Realized/unrealized accounting &bull; Equity drawdowns &bull; Currency exposures
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchPortfolio()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Account Balances Grid */}
      {overview && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
          <Card className="p-4 border-l-4 border-l-sky-500">
            <div className="text-slate-400 mb-1">ACCOUNT BALANCE</div>
            <div className="text-xl font-bold text-slate-100">
              {formatCurrency(overview.balance, overview.currency)}
            </div>
            <div className="text-slate-500 text-[11px] mt-1">
              Free Margin: {formatCurrency(overview.free_margin, overview.currency)}
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-emerald-500">
            <div className="text-slate-400 mb-1">CURRENT EQUITY</div>
            <div className="text-xl font-bold text-slate-100">
              {formatCurrency(overview.equity, overview.currency)}
            </div>
            <div className="text-slate-500 text-[11px] mt-1">
              Used Margin: {formatCurrency(overview.used_margin, overview.currency)}
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-purple-500">
            <div className="text-slate-400 mb-1">MARGIN LEVEL</div>
            <div className="text-xl font-bold text-slate-100">
              {formatPercent(overview.margin_level)}
            </div>
            <div className="text-slate-500 text-[11px] mt-1">
              Open Positions: {overview.open_positions_count}
            </div>
          </Card>

          <Card className="p-4 border-l-4 border-l-amber-500">
            <div className="text-slate-400 mb-1">GROSS EXPOSURE</div>
            <div className="text-xl font-bold text-slate-100">
              {formatCurrency(overview.gross_exposure, overview.currency)}
            </div>
            <div className="text-slate-500 text-[11px] mt-1">
              Net Exposure: {formatCurrency(overview.net_exposure, overview.currency)}
            </div>
          </Card>
        </div>
      )}

      {/* Equity Curve Visualization */}
      {equityCurve && (
        <Card
          title={
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-sky-400" />
              <span>Equity Curve & Drawdown Analysis</span>
            </div>
          }
        >
          <EquityCurveChart
            balance={equityCurve.balance}
            equity={equityCurve.equity}
            peakEquity={equityCurve.peak_equity}
            drawdownPct={equityCurve.current_drawdown}
            currency={equityCurve.currency}
          />
        </Card>
      )}

      {/* Multi-Strategy Portfolio Allocation & Attribution */}
      {strategyBreakdown && Array.isArray(strategyBreakdown.strategies) && (
        <Card
          title={
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-400" />
                <span>Multi-Strategy Portfolio Allocation & Attribution</span>
              </div>
              <span className="text-xs font-mono text-slate-400 font-normal">
                {strategyBreakdown.total_active_strategies || strategyBreakdown.strategies.length} Active{' '}
                {(strategyBreakdown.total_active_strategies || strategyBreakdown.strategies.length) === 1
                  ? 'Strategy'
                  : 'Strategies'}
              </span>
            </div>
          }
        >
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-950/60 border border-slate-800 rounded-lg font-mono text-xs">
              <div>
                <span className="text-slate-500 block">Total Strategy Exposure:</span>
                <span className="font-bold text-slate-100">
                  {formatCurrency(
                    strategyBreakdown.total_gross_exposure ??
                      strategyBreakdown.strategies.reduce(
                        (acc, s) =>
                          acc +
                          (typeof s.gross_exposure === 'number'
                            ? s.gross_exposure
                            : parseFloat(String(s.gross_exposure)) || 0),
                        0
                      ),
                    strategyBreakdown.currency || 'USD'
                  )}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Total Unrealized Strategy P&L:</span>
                <span
                  className={`font-bold ${
                    formatPnl(strategyBreakdown.total_unrealized_pnl, strategyBreakdown.currency || 'USD').isPositive
                      ? 'text-emerald-400'
                      : 'text-rose-400'
                  }`}
                >
                  {formatPnl(strategyBreakdown.total_unrealized_pnl, strategyBreakdown.currency || 'USD').formatted}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Total Realized Strategy P&L:</span>
                <span
                  className={`font-bold ${
                    formatPnl(strategyBreakdown.total_realized_pnl, strategyBreakdown.currency || 'USD').isPositive
                      ? 'text-emerald-400'
                      : 'text-rose-400'
                  }`}
                >
                  {formatPnl(strategyBreakdown.total_realized_pnl, strategyBreakdown.currency || 'USD').formatted}
                </span>
              </div>
            </div>

            <Table
              columns={strategyColumns}
              data={strategyBreakdown.strategies}
              emptyMessage="No active strategy deployments found in paper account."
              keyExtractor={(item) => item.strategy_id}
            />
          </div>
        </Card>
      )}

      {/* PnL Breakdown & Currency Exposure */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detailed P&L Breakdown Card */}
        {pnl && (
          <Card
            title={
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                <span>P&L Breakdown</span>
              </div>
            }
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Gross Profit:</span>
                <span className="text-emerald-400 font-semibold">{formatCurrency(pnl.gross_profit, pnl.currency)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Gross Loss:</span>
                <span className="text-rose-400 font-semibold">{formatCurrency(pnl.gross_loss, pnl.currency)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Total Commissions:</span>
                <span className="text-slate-300">{formatCurrency(pnl.commission, pnl.currency)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Financing / Swaps:</span>
                <span className="text-slate-300">{formatCurrency(pnl.swap, pnl.currency)}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-slate-800">
                <span className="text-slate-400">Broker Fees:</span>
                <span className="text-slate-300">{formatCurrency(pnl.fees, pnl.currency)}</span>
              </div>
              <div className="flex justify-between py-2 border-t border-slate-700 text-sm font-bold">
                <span className="text-slate-200">Net Realized P&L:</span>
                <span className={formatPnl(pnl.net_pnl, pnl.currency).isPositive ? 'text-emerald-400' : 'text-rose-400'}>
                  {formatPnl(pnl.net_pnl, pnl.currency).formatted}
                </span>
              </div>
            </div>
          </Card>
        )}

        {/* Currency Exposure Breakdown Card */}
        {exposure && (
          <Card
            title={
              <div className="flex items-center gap-2">
                <PieChart className="w-4 h-4 text-purple-400" />
                <span>Currency Exposure Breakdown</span>
              </div>
            }
          >
            <ExposureBarChart exposures={exposure.currency_exposures} />
          </Card>
        )}
      </div>

      {/* Currency Exposures Table */}
      {exposure && exposure.currency_exposures.length > 0 && (
        <Card title="Currency Exposure Table">
          <Table
            columns={currencyColumns}
            data={exposure.currency_exposures}
            keyExtractor={(item) => item.currency}
          />
        </Card>
      )}
    </div>
  );
};
