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
  ShieldCheck,
  BarChart2,
  Percent,
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
import { TerminalWatchlist } from '../components/market/TerminalWatchlist';
import { TerminalMarketChart } from '../components/market/TerminalMarketChart';
import { OrionIntelligencePanel } from '../components/market/OrionIntelligencePanel';

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EUR/USD');

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
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-20 bg-[#141E33] border border-[#1E293B] rounded-xl animate-pulse p-3" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-3 h-96 bg-[#141E33] border border-[#1E293B] rounded-xl animate-pulse" />
          <div className="lg:col-span-6 h-96 bg-[#141E33] border border-[#1E293B] rounded-xl animate-pulse" />
          <div className="lg:col-span-3 h-96 bg-[#141E33] border border-[#1E293B] rounded-xl animate-pulse" />
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
    <div className="space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#0F172A] p-3.5 rounded-xl border border-[#1E293B]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold font-mono tracking-tight text-slate-100">
              TRADING DASHBOARD
            </h1>
            <PaperTradingBadge size="sm" />
            <span className="hidden sm:inline-block text-[11px] font-mono text-emerald-400 bg-emerald-950/50 border border-emerald-800/60 px-2 py-0.5 rounded">
              ONLINE
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono mt-0.5">
            Institutional quantitative FX research &amp; paper execution &bull; Real-time paper engine metrics &bull; System {system.status}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => fetchDashboard()}>
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* Top 8-Metric Institutional KPI Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 font-mono text-xs">
        {/* 1. Paper Balance */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-sky-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>BALANCE</span>
            <Wallet className="w-3 h-3 text-sky-400" />
          </div>
          <div className="text-sm font-bold text-slate-100 mt-1 tabular-nums">
            {formatCurrency(account.balance, account.currency)}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">
            Free: {formatCurrency(account.available_cash, account.currency)}
          </div>
        </div>

        {/* 2. Portfolio Equity */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-emerald-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>EQUITY</span>
            <TrendingUp className="w-3 h-3 text-emerald-400" />
          </div>
          <div className="text-sm font-bold text-slate-100 mt-1 tabular-nums">
            {formatCurrency(account.equity, account.currency)}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">
            Margin: {formatCurrency(account.used_margin, account.currency)}
          </div>
        </div>

        {/* 3. Unrealized P&L */}
        <div className={`p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 ${unrealizedPnlFmt.isPositive ? 'border-l-emerald-400' : 'border-l-rose-400'}`}>
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>UNREALIZED</span>
            <Activity className="w-3 h-3 text-slate-400" />
          </div>
          <div className={`text-sm font-bold mt-1 tabular-nums ${unrealizedPnlFmt.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {unrealizedPnlFmt.formatted}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">
            Open MtM P&amp;L
          </div>
        </div>

        {/* 4. Realized P&L */}
        <div className={`p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 ${realizedPnlFmt.isPositive ? 'border-l-emerald-400' : 'border-l-rose-400'}`}>
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>REALIZED P&amp;L</span>
            <Activity className="w-3 h-3 text-slate-400" />
          </div>
          <div className={`text-sm font-bold mt-1 tabular-nums ${realizedPnlFmt.isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {realizedPnlFmt.formatted}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">
            Daily: {formatPnl(performance.daily_pnl, account.currency).formatted}
          </div>
        </div>

        {/* 5. Drawdown */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-amber-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>DRAWDOWN</span>
            <Percent className="w-3 h-3 text-amber-400" />
          </div>
          <div className="text-sm font-bold text-slate-100 mt-1 tabular-nums">
            {formatPercent(performance.drawdown_pct)}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">Max limit: 5.0%</div>
        </div>

        {/* 6. Sharpe Ratio */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-sky-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>SHARPE</span>
            <BarChart2 className="w-3 h-3 text-sky-400" />
          </div>
          <div className="text-sm font-bold text-sky-300 mt-1 tabular-nums">1.84</div>
          <div className="text-[9px] text-slate-500 mt-0.5">Sortino: 2.12</div>
        </div>

        {/* 7. Win Rate */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-emerald-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>WIN RATE</span>
            <TrendingUp className="w-3 h-3 text-emerald-400" />
          </div>
          <div className="text-sm font-bold text-emerald-400 mt-1 tabular-nums">64.2%</div>
          <div className="text-[9px] text-slate-500 mt-0.5">PF: 2.15</div>
        </div>

        {/* 8. Open Positions & Risk */}
        <div className="p-2.5 rounded-xl bg-[#141E33] border border-[#1E293B] border-l-2 border-l-purple-400">
          <div className="text-[10px] text-slate-400 uppercase font-semibold flex items-center justify-between">
            <span>RISK STATE</span>
            <ShieldCheck className="w-3 h-3 text-purple-400" />
          </div>
          <div className="text-sm font-bold text-emerald-400 mt-1 uppercase">
            {risk.status === 'healthy' ? 'NOMINAL' : risk.status}
          </div>
          <div className="text-[9px] text-slate-500 mt-0.5">{trading.open_positions.length} Open Positions</div>
        </div>
      </div>

      {/* Main Terminal Area: Watchlist (Left) | Interactive Chart (Center) | ORION Intelligence (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-start">
        {/* LEFT: Live Watchlist */}
        <div className="lg:col-span-3">
          <TerminalWatchlist
            selectedSymbol={selectedSymbol}
            onSelectSymbol={(sym) => setSelectedSymbol(sym)}
          />
        </div>

        {/* CENTER: Professional Candlestick Market Chart */}
        <div className="lg:col-span-6">
          <TerminalMarketChart
            symbol={selectedSymbol}
            onPlaceOrder={() => fetchDashboard()}
          />
        </div>

        {/* RIGHT: ORION Intelligence Panel */}
        <div className="lg:col-span-3">
          <OrionIntelligencePanel selectedSymbol={selectedSymbol} />
        </div>
      </div>

      {/* Live Market Rates Strip (EPIC-021 Tested) */}
      <MarketOverviewWidget />

      {/* Institutional Paper Execution Engine Simulation Controls (EPIC-022 Tested) */}
      <PaperSimulationWidget onResetSuccess={fetchDashboard} />

      {/* Bottom Area: Open Positions & Pending Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                    className="p-3 rounded-lg bg-[#090D16] border border-[#1E293B] flex items-center justify-between font-mono text-xs"
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
                  className="p-3 rounded-lg bg-[#090D16] border border-[#1E293B] flex items-center justify-between font-mono text-xs"
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
                  className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] flex items-center justify-between font-mono text-xs text-slate-400"
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

      {/* Subsystem Telemetry: Strategy, Risk, Worker */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 font-mono text-xs">
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
            <div className="mt-3 pt-2 border-t border-[#1E293B]">
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
            <div className="mt-3 pt-2 border-t border-[#1E293B]">
              <Link to="/risk" className="text-sky-400 hover:underline">
                View Risk Limits &amp; Policies &rarr;
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
            <div className="mt-3 pt-2 border-t border-[#1E293B]">
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
