import React, { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Wallet,
  TrendingUp,
  Activity,
  Layers,
  ClipboardList,
  History,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { dashboardApi } from '../api/endpoints';
import type { DashboardResponse } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import { Card } from '../components/common/Card';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { formatCurrency, formatPnl, formatPercent, formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';
import { MarketOverviewWidget } from '../components/market/MarketOverviewWidget';
import { PaperSimulationWidget } from '../components/paper/PaperSimulationWidget';

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await dashboardApi.get();
      setData(res);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Poll dashboard every 8 seconds with tab visibility check
  usePolling(fetchDashboard, 8000);

  if (isLoading && !data) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-6 bg-slate-800 rounded w-48 animate-pulse" />
          <div className="h-8 bg-slate-800 rounded w-28 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-900 border border-slate-800 rounded-xl animate-pulse p-4" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
          <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="py-16 text-center">
        <div className="inline-flex p-4 rounded-full bg-rose-950/60 border border-rose-800 text-rose-400 mb-4">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h2 className="text-base font-semibold text-slate-200 mb-2">Unable to Load Dashboard</h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto mb-6">{error}</p>
        <Button variant="secondary" onClick={() => { setIsLoading(true); fetchDashboard(); }}>
          <RefreshCw className="w-4 h-4 mr-1.5" />
          Retry Connection
        </Button>
      </div>
    );
  }

  const { account, performance, trading, strategy, risk, worker, system } = data!;

  const unrealizedPnlFmt = formatPnl(performance.unrealized_pnl, account.currency);
  const realizedPnlFmt = formatPnl(performance.realized_pnl, account.currency);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              TRADING DASHBOARD
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Institutional overview &bull; Real-time paper engine metrics &bull; System {system.status}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => fetchDashboard()}>
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Account Financial Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        <Card className="p-4 border-l-4 border-l-sky-500">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>TOTAL BALANCE</span>
            <Wallet className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            {formatCurrency(account.balance, account.currency)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Free Cash: {formatCurrency(account.available_cash, account.currency)}
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>PORTFOLIO EQUITY</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            {formatCurrency(account.equity, account.currency)}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Used Margin: {formatCurrency(account.used_margin, account.currency)}
          </div>
        </Card>

        <Card className={`p-4 border-l-4 ${unrealizedPnlFmt.isPositive ? 'border-l-emerald-500' : unrealizedPnlFmt.isNegative ? 'border-l-rose-500' : 'border-l-slate-600'}`}>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>UNREALIZED P&L</span>
            <Activity className="w-4 h-4 text-slate-400" />
          </div>
          <div className={`text-xl font-bold ${unrealizedPnlFmt.isPositive ? 'text-emerald-400' : unrealizedPnlFmt.isNegative ? 'text-rose-400' : 'text-slate-100'}`}>
            {unrealizedPnlFmt.formatted}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Drawdown: {formatPercent(performance.drawdown_pct)}
          </div>
        </Card>

        <Card className={`p-4 border-l-4 ${realizedPnlFmt.isPositive ? 'border-l-emerald-500' : realizedPnlFmt.isNegative ? 'border-l-rose-500' : 'border-l-slate-600'}`}>
          <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
            <span>REALIZED P&L</span>
            <Activity className="w-4 h-4 text-slate-400" />
          </div>
          <div className={`text-xl font-bold ${realizedPnlFmt.isPositive ? 'text-emerald-400' : realizedPnlFmt.isNegative ? 'text-rose-400' : 'text-slate-100'}`}>
            {realizedPnlFmt.formatted}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Daily P&L: {formatPnl(performance.daily_pnl, account.currency).formatted}
          </div>
        </Card>
      </div>

      {/* Live Market Feed (EPIC-021) */}
      <MarketOverviewWidget />

      {/* Institutional Paper Execution Engine Simulation Controls (EPIC-022) */}
      <PaperSimulationWidget onResetSuccess={fetchDashboard} />

      {/* Trading State: Open Positions & Pending Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Positions Card */}
        <Card
          title="Open Positions"
          badge={<Badge variant="info">{trading.open_positions.length}</Badge>}
          action={
            <Link to="/positions" className="text-xs text-sky-400 hover:underline flex items-center gap-1 font-mono">
              View All <Layers className="w-3.5 h-3.5" />
            </Link>
          }
        >
          {trading.open_positions.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No open positions. Use Orders page to place a trade.
            </div>
          ) : (
            <div className="space-y-2">
              {trading.open_positions.slice(0, 4).map((pos) => {
                const pnl = formatPnl(pos.unrealized_pnl);
                return (
                  <div
                    key={pos.id}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between font-mono text-xs"
                  >
                    <div className="flex items-center gap-2.5">
                      <Badge variant={pos.side === 'BUY' ? 'buy' : 'sell'}>{pos.side}</Badge>
                      <div>
                        <span className="font-bold text-slate-200">{pos.symbol}</span>
                        <span className="text-slate-500 ml-2">{pos.quantity} units</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-semibold ${pnl.isPositive ? 'text-emerald-400' : pnl.isNegative ? 'text-rose-400' : 'text-slate-300'}`}>
                        {pnl.formatted}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        @ {pos.open_price}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Pending Orders & Recent Trades */}
        <Card
          title="Pending Orders & Recent Fills"
          badge={<Badge variant="warning">{trading.pending_orders.length} pending</Badge>}
          action={
            <Link to="/orders" className="text-xs text-sky-400 hover:underline flex items-center gap-1 font-mono">
              Orders <ClipboardList className="w-3.5 h-3.5" />
            </Link>
          }
        >
          {trading.pending_orders.length === 0 && trading.recent_trades.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 font-mono">
              No active pending orders or recent fills.
            </div>
          ) : (
            <div className="space-y-2">
              {trading.pending_orders.slice(0, 3).map((ord) => (
                <div
                  key={ord.id}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between font-mono text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant={ord.side === 'BUY' ? 'buy' : 'sell'}>{ord.side}</Badge>
                    <span className="font-bold text-slate-200">{ord.symbol}</span>
                    <span className="text-slate-500">{ord.order_type}</span>
                  </div>
                  <div className="text-right">
                    <Badge variant="warning">{ord.status}</Badge>
                    <div className="text-[10px] text-slate-500 mt-0.5">{ord.quantity} units</div>
                  </div>
                </div>
              ))}
              {trading.recent_trades.slice(0, 2).map((t) => (
                <div
                  key={t.trade_id}
                  className="p-2.5 rounded-lg bg-slate-950/30 border border-slate-800/60 flex items-center justify-between font-mono text-xs text-slate-400"
                >
                  <div className="flex items-center gap-2">
                    <History className="w-3.5 h-3.5 text-slate-500" />
                    <span>FILL: {t.symbol} {t.side}</span>
                  </div>
                  <span>{t.quantity} @ {t.price}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Subsystem Telemetry: Strategy, Risk, Worker, System */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
        {/* Strategy Status */}
        <Card title="Strategy Engine" action={<Badge variant="default">{strategy.timeframe}</Badge>}>
          <div className="space-y-2 text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Active Strategy:</span>
              <span className="font-semibold text-slate-100">{strategy.active_strategy}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Target Pairs:</span>
              <span className="text-slate-200">{strategy.symbols.join(', ') || 'None'}</span>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800">
              <Link to="/strategies" className="text-sky-400 hover:underline">
                Configure Strategy Parameters &rarr;
              </Link>
            </div>
          </div>
        </Card>

        {/* Risk Status */}
        <Card title="Risk Controls" action={<Badge variant={risk.status === 'healthy' ? 'success' : 'danger'}>{risk.status}</Badge>}>
          <div className="space-y-2 text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Total Exposure:</span>
              <span>{formatCurrency(risk.total_exposure, account.currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Margin Level:</span>
              <span>{formatPercent(risk.margin_level)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Emergency Stop:</span>
              <span className={risk.emergency_stop_active ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                {risk.emergency_stop_active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800">
              <Link to="/risk" className="text-sky-400 hover:underline">
                View Risk Limits & Policies &rarr;
              </Link>
            </div>
          </div>
        </Card>

        {/* Worker Telemetry */}
        <Card title="Autonomous Worker" action={<Badge variant={worker.is_running ? 'success' : 'default'}>{worker.state}</Badge>}>
          <div className="space-y-2 text-slate-300">
            <div className="flex justify-between">
              <span className="text-slate-500">Execution Mode:</span>
              <span className="text-amber-300 font-bold">PAPER</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Last Cycle:</span>
              <span className="text-slate-400">{formatDateTime(worker.last_cycle_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Uptime:</span>
              <span className="text-slate-300">{Math.round(worker.uptime_seconds)}s</span>
            </div>
            <div className="mt-3 pt-2 border-t border-slate-800">
              <Link to="/worker" className="text-sky-400 hover:underline">
                Detailed Worker Metrics &rarr;
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
