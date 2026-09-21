import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  FlaskConical,
  Play,
  History,
  TrendingUp,
  Download,
  AlertTriangle,
  Info,
  BarChart3,
  Columns,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import { researchApi } from '../api/endpoints';
import type {
  StrategyCatalogueItem,
  ExperimentSummary,
  ExperimentDetail,
  EquityPoint,
  ResearchTradeRecord,
  ExperimentComparisonResponse,
} from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { useToast } from '../components/common/Toast';
import { formatCurrency } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const ResearchLabPage: React.FC = () => {
  const toast = useToast();

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'builder' | 'history' | 'results' | 'compare'>('builder');

  // Catalogue & History state
  const [strategies, setStrategies] = useState<StrategyCatalogueItem[]>([]);
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);

  // Builder Form State
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EUR/USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('H1');
  const [startDate, setStartDate] = useState<string>('2025-01-01');
  const [endDate, setEndDate] = useState<string>('2025-01-31');
  const [initialCapital, setInitialCapital] = useState<number>(10000);
  const [spreadPips, setSpreadPips] = useState<number>(1.5);
  const [slippagePips, setSlippagePips] = useState<number>(0.5);
  const [commission, setCommission] = useState<number>(7.0);
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({});

  // Active Experiment Result State
  const [activeExperiment, setActiveExperiment] = useState<ExperimentDetail | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [trades, setTrades] = useState<ResearchTradeRecord[]>([]);

  // Comparison State
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<ExperimentComparisonResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  // Selected strategy metadata
  const currentStrategy = useMemo(() => {
    return strategies.find((s) => s.strategy_id === selectedStrategyId) || null;
  }, [strategies, selectedStrategyId]);

  // Load Initial Catalogue and Experiment History
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [strats, exps] = await Promise.all([
        researchApi.listStrategies(),
        researchApi.listExperiments({ limit: 50 }),
      ]);
      setStrategies(strats);
      setExperiments(exps);

      if (strats.length > 0 && !selectedStrategyId) {
        setSelectedStrategyId(strats[0].strategy_id);
        const defaults: Record<string, any> = {};
        strats[0].parameters.forEach((p) => {
          defaults[p.name] = p.default;
        });
        setStrategyParams(defaults);
      }
    } catch (err) {
      toast.error(`Failed to load research lab: ${getErrorMessage(err)}`);
    } finally {
      setIsLoading(false);
    }
  }, [selectedStrategyId, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Strategy change handler
  const handleStrategyChange = (newStratId: string) => {
    setSelectedStrategyId(newStratId);
    const strat = strategies.find((s) => s.strategy_id === newStratId);
    if (strat) {
      const defaults: Record<string, any> = {};
      strat.parameters.forEach((p) => {
        defaults[p.name] = p.default;
      });
      setStrategyParams(defaults);
      if (strat.supported_instruments.length > 0 && !strat.supported_instruments.includes(selectedSymbol)) {
        setSelectedSymbol(strat.supported_instruments[0]);
      }
    }
  };

  // Run Backtest
  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStrategyId) {
      toast.error('Please select a strategy archetype.');
      return;
    }

    setIsExecuting(true);
    try {
      toast.info('Initiating deterministic backtest simulation...');
      const summary = await researchApi.createExperiment({
        strategy_id: selectedStrategyId,
        symbol: selectedSymbol,
        timeframe: selectedTimeframe,
        start_date: startDate,
        end_date: endDate,
        initial_capital: initialCapital,
        spread_pips: spreadPips,
        adverse_slippage_pips: slippagePips,
        commission_per_lot: commission,
        parameters: strategyParams,
      });

      toast.success(`Backtest completed in ${summary.execution_time_seconds.toFixed(2)}s`);
      await loadData();
      await inspectExperiment(summary.id);
    } catch (err) {
      toast.error(`Backtest failed: ${getErrorMessage(err)}`);
    } finally {
      setIsExecuting(false);
    }
  };

  // Inspect Single Experiment Details
  const inspectExperiment = async (experimentId: string) => {
    try {
      const [detail, eqRes, trRes] = await Promise.all([
        researchApi.getExperiment(experimentId),
        researchApi.getEquityCurve(experimentId),
        researchApi.getTrades(experimentId),
      ]);
      setActiveExperiment(detail);
      setEquityCurve(eqRes.points || []);
      setTrades(trRes.trades || []);
      setActiveTab('results');
    } catch (err) {
      toast.error(`Failed to load experiment results: ${getErrorMessage(err)}`);
    }
  };

  // Run Comparison
  const handleCompare = async () => {
    if (selectedForCompare.length < 2) {
      toast.error('Please select at least 2 experiments to compare.');
      return;
    }
    setIsComparing(true);
    try {
      const result = await researchApi.compare({ experiment_ids: selectedForCompare });
      setComparisonData(result);
      setActiveTab('compare');
    } catch (err) {
      toast.error(`Comparison failed: ${getErrorMessage(err)}`);
    } finally {
      setIsComparing(false);
    }
  };

  // Toggle selection for comparison
  const toggleCompareSelection = (id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 5) {
        toast.warning('Maximum 5 experiments can be compared at once.');
        return prev;
      }
      return [...prev, id];
    });
  };

  // SVG Equity Curve Calculation
  const svgChart = useMemo(() => {
    if (!equityCurve || equityCurve.length < 2) return null;
    const width = 800;
    const height = 240;
    const padding = 35;

    const equities = equityCurve.map((p) => p.equity);
    const minEq = Math.min(...equities);
    const maxEq = Math.max(...equities);
    const range = maxEq - minEq || 1;

    const pointsStr = equityCurve
      .map((p, i) => {
        const x = padding + (i / (equityCurve.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((p.equity - minEq) / range) * (height - 2 * padding);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

    return { pointsStr, width, height, minEq, maxEq };
  }, [equityCurve]);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold font-mono text-slate-100 flex items-center gap-2">
              <FlaskConical className="w-6 h-6 text-sky-400" />
              Institutional Strategy Lab & Research
            </h1>
            <PaperTradingBadge />
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Zero look-ahead bias • Deterministic tick simulation • Quant overfitting safeguards
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('builder')}
          className={`px-4 py-2 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'builder'
              ? 'border-sky-500 text-sky-400 bg-sky-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-3.5 h-3.5" />
          Lab Builder
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-sky-500 text-sky-400 bg-sky-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-3.5 h-3.5" />
          Experiments ({experiments.length})
        </button>

        {activeExperiment && (
          <button
            onClick={() => setActiveTab('results')}
            className={`px-4 py-2 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'results'
                ? 'border-sky-500 text-sky-400 bg-sky-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            Results: {activeExperiment.id}
          </button>
        )}

        {comparisonData && (
          <button
            onClick={() => setActiveTab('compare')}
            className={`px-4 py-2 text-xs font-mono font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'compare'
                ? 'border-sky-500 text-sky-400 bg-sky-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            Comparison ({comparisonData.comparison.length})
          </button>
        )}
      </div>

      {/* ─── TAB 1: LAB BUILDER ──────────────────────────────────────────────── */}
      {activeTab === 'builder' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6 bg-slate-900 border-slate-800">
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2 mb-4 font-mono">
                <Sliders className="w-4 h-4 text-sky-400" />
                Strategy & Simulation Parameters
              </h2>

              <form onSubmit={handleRunBacktest} className="space-y-5">
                {/* Strategy Selector */}
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">Strategy Archetype</label>
                  <select
                    value={selectedStrategyId}
                    onChange={(e) => handleStrategyChange(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                  >
                    {strategies.map((s) => (
                      <option key={s.strategy_id} value={s.strategy_id}>
                        {s.name} ({s.category.toUpperCase()})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Instrument and Timeframe */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Trading Instrument</label>
                    <select
                      value={selectedSymbol}
                      onChange={(e) => setSelectedSymbol(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    >
                      {(currentStrategy?.supported_instruments || ['EUR/USD', 'GBP/USD', 'USD/JPY']).map((sym) => (
                        <option key={sym} value={sym}>
                          {sym}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Bar Timeframe</label>
                    <select
                      value={selectedTimeframe}
                      onChange={(e) => setSelectedTimeframe(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    >
                      {(currentStrategy?.supported_timeframes || ['M15', 'H1', 'H4', 'D1']).map((tf) => (
                        <option key={tf} value={tf}>
                          {tf}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Date Range */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Historical Start Date</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Historical End Date</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                </div>

                {/* Capital & Execution Friction */}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2 border-t border-slate-800/60">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Initial Capital ($)</label>
                    <input
                      type="number"
                      step="100"
                      min="100"
                      value={initialCapital}
                      onChange={(e) => setInitialCapital(parseFloat(e.target.value) || 10000)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Spread (pips)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={spreadPips}
                      onChange={(e) => setSpreadPips(parseFloat(e.target.value) || 0)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Adverse Slippage (pips)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={slippagePips}
                      onChange={(e) => setSlippagePips(parseFloat(e.target.value) || 0)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Fee ($ / lot)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      value={commission}
                      onChange={(e) => setCommission(parseFloat(e.target.value) || 0)}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                    />
                  </div>
                </div>

                {/* Dynamic Strategy Parameters */}
                {currentStrategy && currentStrategy.parameters.length > 0 && (
                  <div className="space-y-3 pt-3 border-t border-slate-800/60">
                    <h3 className="text-xs font-semibold text-slate-300 font-mono uppercase tracking-wider">
                      Strategy Tunable Parameters
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {currentStrategy.parameters.map((p) => (
                        <div key={p.name}>
                          <div className="flex justify-between items-center mb-1">
                            <label className="text-xs font-mono text-slate-400">{p.name}</label>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {p.min !== undefined && p.max !== undefined ? `[${p.min}..${p.max}]` : p.type}
                            </span>
                          </div>
                          {p.type === 'integer' || p.type === 'float' ? (
                            <input
                              type="number"
                              step={p.type === 'integer' ? '1' : '0.1'}
                              min={p.min}
                              max={p.max}
                              value={strategyParams[p.name] ?? p.default}
                              onChange={(e) =>
                                setStrategyParams({
                                  ...strategyParams,
                                  [p.name]:
                                    p.type === 'integer'
                                      ? parseInt(e.target.value, 10) || p.default
                                      : parseFloat(e.target.value) || p.default,
                                })
                              }
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                            />
                          ) : p.type === 'boolean' ? (
                            <select
                              value={strategyParams[p.name] ? 'true' : 'false'}
                              onChange={(e) =>
                                setStrategyParams({
                                  ...strategyParams,
                                  [p.name]: e.target.value === 'true',
                                })
                              }
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                            >
                              <option value="true">True</option>
                              <option value="false">False</option>
                            </select>
                          ) : (
                            <input
                              type="text"
                              value={strategyParams[p.name] ?? p.default}
                              onChange={(e) =>
                                setStrategyParams({
                                  ...strategyParams,
                                  [p.name]: e.target.value,
                                })
                              }
                              className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:border-sky-500 focus:outline-hidden font-mono"
                            />
                          )}
                          {p.description && (
                            <p className="text-[10px] text-slate-500 mt-0.5">{p.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-4 flex justify-end">
                  <Button
                    type="submit"
                    disabled={isExecuting}
                    className="bg-sky-600 hover:bg-sky-500 text-white font-mono flex items-center gap-2 px-6"
                  >
                    <Play className={`w-4 h-4 ${isExecuting ? 'animate-spin' : ''}`} />
                    {isExecuting ? 'Executing Backtest...' : 'Run Simulation'}
                  </Button>
                </div>
              </form>
            </Card>
          </div>

          {/* Strategy Info Sidebar Card */}
          <div className="space-y-6">
            <Card className="p-6 bg-slate-900 border-slate-800">
              <h3 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-sky-400" />
                Archetype Specification
              </h3>
              {currentStrategy ? (
                <div className="space-y-3 text-xs font-mono">
                  <div>
                    <span className="text-slate-500">ID: </span>
                    <span className="text-slate-300">{currentStrategy.strategy_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Category: </span>
                    <span className="text-sky-400 uppercase font-semibold">{currentStrategy.category}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Engine Version: </span>
                    <span className="text-slate-300">{currentStrategy.version}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Execution Mode: </span>
                    <span className="text-emerald-400">Strictly Deterministic</span>
                  </div>
                  <div className="pt-2 border-t border-slate-800 text-slate-400 leading-relaxed">
                    {currentStrategy.description}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-500">Select a strategy archetype</p>
              )}
            </Card>

            <Card className="p-6 bg-slate-900 border-slate-800">
              <h3 className="text-sm font-semibold text-slate-100 font-mono flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Quant Methodological Rules
              </h3>
              <ul className="space-y-2 text-xs text-slate-400 list-disc list-inside leading-relaxed">
                <li>Zero look-ahead bias enforced via strict LeakageGuard slice [0..T].</li>
                <li>Adverse slippage applied symmetrically on every market execution.</li>
                <li>Fixed $7.00 per standard lot commission accounted continuously.</li>
                <li>Statistical warnings emit if closed trade count is under 30.</li>
              </ul>
            </Card>
          </div>
        </div>
      )}

      {/* ─── TAB 2: EXPERIMENT HISTORY ───────────────────────────────────────── */}
      {activeTab === 'history' && (
        <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-semibold text-slate-100 font-mono flex items-center gap-2">
                <History className="w-4 h-4 text-sky-400" />
                Research Experiment Ledger
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Select 2 to 5 experiments to perform side-by-side comparative analytics
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCompare}
                disabled={selectedForCompare.length < 2 || isComparing}
                className="font-mono text-xs flex items-center gap-1.5"
              >
                <Columns className="w-3.5 h-3.5" />
                Compare Selected ({selectedForCompare.length})
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="border-b border-slate-800 text-slate-500">
                <tr>
                  <th className="py-2.5 px-3 w-8">#</th>
                  <th className="py-2.5 px-3">Experiment ID</th>
                  <th className="py-2.5 px-3">Strategy</th>
                  <th className="py-2.5 px-3">Pair / TF</th>
                  <th className="py-2.5 px-3">Net Profit</th>
                  <th className="py-2.5 px-3">Return %</th>
                  <th className="py-2.5 px-3">Sharpe</th>
                  <th className="py-2.5 px-3">Max DD%</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {experiments.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="py-8 text-center text-slate-500">
                      No research backtests recorded yet. Run a simulation in the Lab Builder!
                    </td>
                  </tr>
                ) : (
                  experiments.map((exp) => {
                    const m = exp.metrics;
                    const isSelected = selectedForCompare.includes(exp.id);
                    const isProfit = (m?.net_profit ?? 0) >= 0;

                    return (
                      <tr
                        key={exp.id}
                        className={`hover:bg-slate-800/30 transition-colors ${
                          isSelected ? 'bg-sky-950/20' : ''
                        }`}
                      >
                        <td className="py-3 px-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleCompareSelection(exp.id)}
                            className="rounded border-slate-700 text-sky-500 focus:ring-0"
                          />
                        </td>
                        <td className="py-3 px-3 font-semibold text-slate-200">{exp.id}</td>
                        <td className="py-3 px-3 text-slate-300">{exp.strategy_id}</td>
                        <td className="py-3 px-3 text-slate-400">
                          {exp.symbol} <span className="text-slate-600">/</span> {exp.timeframe}
                        </td>
                        <td className={`py-3 px-3 font-semibold ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {m ? formatCurrency(m.net_profit) : '—'}
                        </td>
                        <td className={`py-3 px-3 ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {m ? `${m.total_return_pct.toFixed(2)}%` : '—'}
                        </td>
                        <td className="py-3 px-3 text-slate-200">{m ? m.sharpe_ratio.toFixed(2) : '—'}</td>
                        <td className="py-3 px-3 text-amber-400">{m ? `${m.max_drawdown_pct.toFixed(1)}%` : '—'}</td>
                        <td className="py-3 px-3">
                          <Badge
                            variant={
                              exp.status === 'COMPLETED'
                                ? 'success'
                                : exp.status === 'RUNNING'
                                ? 'warning'
                                : 'danger'
                            }
                          >
                            {exp.status}
                          </Badge>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => inspectExperiment(exp.id)}
                            className="text-sky-400 hover:text-sky-300 font-mono text-xs"
                          >
                            View Results
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ─── TAB 3: RESULTS & METRICS ────────────────────────────────────────── */}
      {activeTab === 'results' && activeExperiment && (
        <div className="space-y-6">
          {/* Header & Export Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-lg">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-bold font-mono text-slate-100">{activeExperiment.id}</h2>
                <Badge variant="success">{activeExperiment.status}</Badge>
                <span className="text-xs text-slate-500 font-mono">
                  Execution runtime: {activeExperiment.execution_time_seconds.toFixed(2)}s
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Strategy: {activeExperiment.strategy_id} • Symbol: {activeExperiment.symbol} • TF:{' '}
                {activeExperiment.timeframe} • Range: {activeExperiment.start_date.substring(0, 10)} to{' '}
                {activeExperiment.end_date.substring(0, 10)}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <a
                href={researchApi.getExportUrl(activeExperiment.id, 'csv')}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded border border-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export CSV
              </a>
              <a
                href={researchApi.getExportUrl(activeExperiment.id, 'json')}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono rounded border border-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export JSON
              </a>
            </div>
          </div>

          {/* Quant Overfitting Advisories */}
          {activeExperiment.warnings && activeExperiment.warnings.length > 0 && (
            <div className="space-y-2">
              {activeExperiment.warnings.map((w) => (
                <div
                  key={w.code}
                  className={`p-3.5 rounded-lg border text-xs font-mono flex items-start gap-3 ${
                    w.severity === 'CRITICAL'
                      ? 'bg-rose-950/30 border-rose-800/80 text-rose-300'
                      : w.severity === 'WARNING'
                      ? 'bg-amber-950/30 border-amber-800/80 text-amber-300'
                      : 'bg-sky-950/30 border-sky-800/80 text-sky-300'
                  }`}
                >
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold tracking-wide">[{w.code}] {w.title}: </span>
                    <span className="opacity-90">{w.description}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Key Metrics Grid */}
          {activeExperiment.metrics && (
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Net Profit</p>
                <p
                  className={`text-lg font-bold font-mono ${
                    activeExperiment.metrics.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {formatCurrency(activeExperiment.metrics.net_profit)}
                </p>
              </Card>

              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Total Return</p>
                <p
                  className={`text-lg font-bold font-mono ${
                    activeExperiment.metrics.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {activeExperiment.metrics.total_return_pct.toFixed(2)}%
                </p>
              </Card>

              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Sharpe Ratio</p>
                <p className="text-lg font-bold font-mono text-sky-400">
                  {activeExperiment.metrics.sharpe_ratio.toFixed(2)}
                </p>
              </Card>

              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Max Drawdown</p>
                <p className="text-lg font-bold font-mono text-amber-400">
                  {activeExperiment.metrics.max_drawdown_pct.toFixed(1)}%
                </p>
              </Card>

              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Win Rate</p>
                <p className="text-lg font-bold font-mono text-slate-200">
                  {activeExperiment.metrics.win_rate_pct.toFixed(1)}%
                </p>
              </Card>

              <Card className="p-3.5 bg-slate-900 border-slate-800">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Profit Factor</p>
                <p className="text-lg font-bold font-mono text-slate-200">
                  {activeExperiment.metrics.profit_factor.toFixed(2)}
                </p>
              </Card>
            </div>
          )}

          {/* SVG Equity Curve Chart */}
          <Card className="p-6 bg-slate-900 border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold font-mono text-slate-200 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-sky-400" />
                Simulated Equity Curve ($)
              </h3>
              {svgChart && (
                <div className="text-[11px] font-mono text-slate-400 flex items-center gap-4">
                  <span>Min: {formatCurrency(svgChart.minEq)}</span>
                  <span>Max: {formatCurrency(svgChart.maxEq)}</span>
                </div>
              )}
            </div>

            {svgChart ? (
              <div className="w-full overflow-hidden bg-slate-950/60 rounded border border-slate-800/80 p-2">
                <svg viewBox={`0 0 ${svgChart.width} ${svgChart.height}`} className="w-full h-56 stroke-sky-400">
                  {/* Background Grid Lines */}
                  <line x1="35" y1="35" x2="765" y2="35" stroke="#1e293b" strokeDasharray="3 3" />
                  <line x1="35" y1="120" x2="765" y2="120" stroke="#1e293b" strokeDasharray="3 3" />
                  <line x1="35" y1="205" x2="765" y2="205" stroke="#1e293b" strokeDasharray="3 3" />

                  {/* Equity Polyline */}
                  <polyline
                    fill="none"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={svgChart.pointsStr}
                  />
                </svg>
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono py-8 text-center">No equity points available</p>
            )}
          </Card>

          {/* Trade Execution Ledger */}
          <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold font-mono text-slate-200 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-sky-400" />
              Simulated Trade Execution Ledger ({trades.length} trades)
            </h3>

            <div className="overflow-x-auto max-h-96">
              <table className="w-full text-left text-xs font-mono">
                <thead className="border-b border-slate-800 text-slate-500 sticky top-0 bg-slate-900">
                  <tr>
                    <th className="py-2 px-3">Trade ID</th>
                    <th className="py-2 px-3">Side</th>
                    <th className="py-2 px-3">Entry Time</th>
                    <th className="py-2 px-3">Exit Time</th>
                    <th className="py-2 px-3">Entry Price</th>
                    <th className="py-2 px-3">Exit Price</th>
                    <th className="py-2 px-3">Gross P&L</th>
                    <th className="py-2 px-3">Fees</th>
                    <th className="py-2 px-3">Net P&L</th>
                    <th className="py-2 px-3">Exit Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {trades.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="py-6 text-center text-slate-500">
                        Zero trade executions triggered in this backtest period.
                      </td>
                    </tr>
                  ) : (
                    trades.map((t) => (
                      <tr key={t.trade_id} className="hover:bg-slate-800/30">
                        <td className="py-2 px-3 font-semibold text-slate-300">{t.trade_id}</td>
                        <td className="py-2 px-3">
                          <span
                            className={`font-semibold ${
                              t.side === 'BUY' ? 'text-sky-400' : 'text-amber-400'
                            }`}
                          >
                            {t.side}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-slate-400">{t.entry_time.replace('T', ' ').substring(0, 16)}</td>
                        <td className="py-2 px-3 text-slate-400">{t.exit_time.replace('T', ' ').substring(0, 16)}</td>
                        <td className="py-2 px-3 text-slate-300">{t.entry_price.toFixed(5)}</td>
                        <td className="py-2 px-3 text-slate-300">{t.exit_price.toFixed(5)}</td>
                        <td className="py-2 px-3 text-slate-400">{formatCurrency(t.gross_pnl)}</td>
                        <td className="py-2 px-3 text-rose-400/80">{formatCurrency(t.fees)}</td>
                        <td
                          className={`py-2 px-3 font-semibold ${
                            t.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}
                        >
                          {formatCurrency(t.net_pnl)}
                        </td>
                        <td className="py-2 px-3 text-slate-400">{t.exit_reason}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ─── TAB 4: EXPERIMENT COMPARISON ────────────────────────────────────── */}
      {activeTab === 'compare' && comparisonData && (
        <div className="space-y-6">
          <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
            <h2 className="text-base font-semibold font-mono text-slate-100 flex items-center gap-2">
              <Columns className="w-4 h-4 text-sky-400" />
              Side-by-Side Experiment Comparison Matrix
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="border-b border-slate-800 text-slate-500">
                  <tr>
                    <th className="py-2.5 px-3">Metric</th>
                    {comparisonData.comparison.map((exp) => (
                      <th key={exp.experiment_id} className="py-2.5 px-3 text-sky-400">
                        {exp.experiment_id} ({exp.strategy_id})
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Symbol / TF</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3">
                        {exp.symbol} / {exp.timeframe}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Net Profit ($)</td>
                    {comparisonData.comparison.map((exp) => (
                      <td
                        key={exp.experiment_id}
                        className={`py-2.5 px-3 font-bold ${
                          exp.net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {formatCurrency(exp.net_profit)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Return (%)</td>
                    {comparisonData.comparison.map((exp) => (
                      <td
                        key={exp.experiment_id}
                        className={`py-2.5 px-3 ${
                          exp.total_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {exp.total_return_pct.toFixed(2)}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Sharpe Ratio</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3 text-sky-400 font-semibold">
                        {exp.sharpe_ratio.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Max Drawdown (%)</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3 text-amber-400">
                        {exp.max_drawdown_pct.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Win Rate (%)</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3">
                        {exp.win_rate_pct.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Total Trades</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3">
                        {exp.total_trades}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-semibold text-slate-400">Profit Factor</td>
                    {comparisonData.comparison.map((exp) => (
                      <td key={exp.experiment_id} className="py-2.5 px-3">
                        {exp.profit_factor.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
