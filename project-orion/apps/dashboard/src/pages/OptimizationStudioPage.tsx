import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Zap,
  Play,
  History,
  TrendingUp,
  Download,
  AlertTriangle,
  Info,
  BarChart3,
  RefreshCw,
  Sliders,
  ShieldCheck,
  Activity,
  XCircle,
  Layers,
  Rocket,
} from 'lucide-react';
import { optimizationApi, researchApi, deploymentApi } from '../api/endpoints';
import type {
  StrategyCatalogueItem,
  ParameterRangeConfig,
  OptimizationRunRequest,
  WalkForwardRunRequest,
  OptimizationJobSummary,
  OptimizationJobDetail,
} from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { useToast } from '../components/common/Toast';
import { getErrorMessage } from '../utils/errors';

export const OptimizationStudioPage: React.FC = () => {
  const toast = useToast();

  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'sweep' | 'leaderboard' | 'heatmap' | 'walkforward' | 'regimes' | 'history'>('sweep');

  // Catalogue & History state
  const [strategies, setStrategies] = useState<StrategyCatalogueItem[]>([]);
  const [jobs, setJobs] = useState<OptimizationJobSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExecuting, setIsExecuting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  // Active Job Detail State
  const [activeJob, setActiveJob] = useState<OptimizationJobDetail | null>(null);

  // Form State
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('TrendFollowing');
  const [optimizationMode, setOptimizationMode] = useState<'GRID_SEARCH' | 'RANDOM_SEARCH' | 'WALK_FORWARD'>('GRID_SEARCH');
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EUR/USD');
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('H1');
  const [startDate, setStartDate] = useState<string>('2025-01-01');
  const [endDate, setEndDate] = useState<string>('2025-01-31');
  const [initialCapital, setInitialCapital] = useState<number>(10000);
  const [fitnessObjective, setFitnessObjective] = useState<string>('SHARPE_RATIO');
  const [maxCombinations, setMaxCombinations] = useState<number>(100);
  const [nSamples, setNSamples] = useState<number>(40);
  const [nWindows, setNWindows] = useState<number>(4);
  const [inSampleRatio, setInSampleRatio] = useState<number>(0.70);
  const [isAnchored, setIsAnchored] = useState<boolean>(false);
  const [spreadPips, setSpreadPips] = useState<number>(1.5);
  const [slippagePips, setSlippagePips] = useState<number>(0.5);
  const [commission, setCommission] = useState<number>(7.0);

  // Parameter ranges editor state
  const [paramRanges, setParamRanges] = useState<ParameterRangeConfig[]>([]);

  // Load Initial Catalogue & Job History
  const loadInitialData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [strats, jobList] = await Promise.all([
        researchApi.listStrategies().catch(() => []),
        optimizationApi.listJobs().catch(() => []),
      ]);
      setStrategies(strats);
      setJobs(jobList);

      const defaultStrat = strats.length > 0 ? strats[0].strategy_id : 'TrendFollowing';
      setSelectedStrategyId(defaultStrat);

      // Fetch default parameter space
      const defaultSpace = await optimizationApi.getDefaultSpace(defaultStrat).catch(() => null);
      if (defaultSpace && defaultSpace.ranges) {
        setParamRanges(defaultSpace.ranges);
      }
    } catch (err) {
      toast.error(`Failed to load optimization studio: ${getErrorMessage(err)}`);
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Handle Strategy Selection Change
  const handleStrategyChange = async (strategyId: string) => {
    setSelectedStrategyId(strategyId);
    try {
      const space = await optimizationApi.getDefaultSpace(strategyId);
      if (space && space.ranges) {
        setParamRanges(space.ranges);
      }
    } catch (err) {
      toast.error(`Failed to fetch default parameters: ${getErrorMessage(err)}`);
    }
  };

  // Live estimated combinations calculation
  const estimatedCombinations = useMemo(() => {
    if (optimizationMode === 'RANDOM_SEARCH') {
      return nSamples;
    }
    let total = 1;
    for (const r of paramRanges) {
      if (r.param_type === 'choice' && r.choices && r.choices.length > 0) {
        total *= r.choices.length;
      } else if (r.step && Number(r.step) > 0) {
        const span = Number(r.max_value) - Number(r.min_value);
        const steps = Math.floor(span / Number(r.step)) + 1;
        total *= Math.max(1, steps);
      } else {
        total *= 1;
      }
    }
    return total;
  }, [paramRanges, optimizationMode, nSamples]);

  // Update a parameter range field
  const updateRangeField = (index: number, field: keyof ParameterRangeConfig, val: any) => {
    setParamRanges((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: val };
      return updated;
    });
  };

  // Launch Optimization or Walk-Forward Analysis
  const handleLaunchSweep = async () => {
    setIsExecuting(true);
    try {
      if (optimizationMode === 'WALK_FORWARD') {
        const req: WalkForwardRunRequest = {
          strategy_id: selectedStrategyId,
          symbol: selectedSymbol,
          timeframe: selectedTimeframe,
          start_date: new Date(startDate).toISOString(),
          end_date: new Date(endDate).toISOString(),
          initial_capital: initialCapital,
          n_windows: nWindows,
          in_sample_ratio: inSampleRatio,
          anchored: isAnchored,
          fitness_objective: fitnessObjective,
          parameter_space: {
            strategy_id: selectedStrategyId,
            ranges: paramRanges,
          },
          max_combinations_per_window: maxCombinations,
          spread_pips: spreadPips,
          slippage_pips: slippagePips,
          commission: commission,
        };
        const job = await optimizationApi.runWalkForward(req);
        setActiveJob(job);
        setActiveTab('walkforward');
        toast.success(`Walk-Forward Analysis completed successfully across ${nWindows} windows!`);
      } else {
        const req: OptimizationRunRequest = {
          strategy_id: selectedStrategyId,
          symbol: selectedSymbol,
          timeframe: selectedTimeframe,
          start_date: new Date(startDate).toISOString(),
          end_date: new Date(endDate).toISOString(),
          initial_capital: initialCapital,
          optimization_type: optimizationMode,
          fitness_objective: fitnessObjective,
          parameter_space: {
            strategy_id: selectedStrategyId,
            ranges: paramRanges,
          },
          max_combinations: maxCombinations,
          n_samples: nSamples,
          spread_pips: spreadPips,
          slippage_pips: slippagePips,
          commission: commission,
        };
        const job = await optimizationApi.runOptimization(req);
        setActiveJob(job);
        setActiveTab('leaderboard');
        toast.success(`Optimization sweep finished: ${job.completed_combinations} combinations evaluated!`);
      }

      // Refresh job history in background
      optimizationApi.listJobs().then(setJobs).catch(() => {});
    } catch (err) {
      toast.error(`Sweep failed: ${getErrorMessage(err)}`);
    } finally {
      setIsExecuting(false);
    }
  };

  // Cancel running job
  const handleCancelJob = async () => {
    if (!activeJob) return;
    setIsCancelling(true);
    try {
      await optimizationApi.cancelJob(activeJob.id);
      toast.info('Cancellation signal dispatched');
      const updated = await optimizationApi.getJob(activeJob.id);
      setActiveJob(updated);
    } catch (err) {
      toast.error(`Cancel failed: ${getErrorMessage(err)}`);
    } finally {
      setIsCancelling(false);
    }
  };

  // Load job details from history
  const handleSelectJob = async (jobId: string) => {
    setIsLoading(true);
    try {
      const detail = await optimizationApi.getJob(jobId);
      setActiveJob(detail);
      if (detail.optimization_type === 'WALK_FORWARD') {
        setActiveTab('walkforward');
      } else {
        setActiveTab('leaderboard');
      }
    } catch (err) {
      toast.error(`Failed to load job: ${getErrorMessage(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePromoteToPaper = async (rank: number) => {
    if (!activeJob) return;
    try {
      const res = await deploymentApi.promoteFromOptimization({
        optimization_job_id: activeJob.id,
        candidate_rank: rank,
      });
      toast.success(`Candidate #${rank} promoted to Deployment Pipeline (${res.status})!`);
    } catch (err) {
      toast.error(`Promotion failed: ${getErrorMessage(err)}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-slate-100 font-mono">
              OPTIMIZATION STUDIO
            </h1>
            <PaperTradingBadge />
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic Grid & Random Sweeps, Walk-Forward Analysis (WFA), and Market Regime Stress Testing
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeJob && activeJob.status === 'RUNNING' && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelJob}
              disabled={isCancelling}
              className="border-rose-500/40 text-rose-400 hover:bg-rose-500/10"
            >
              <XCircle className="w-4 h-4 mr-1.5" />
              {isCancelling ? 'Cancelling...' : 'Cancel Run'}
            </Button>
          )}

          {activeJob && (
            <div className="flex items-center gap-1.5">
              <a
                href={optimizationApi.getExportUrl(activeJob.id, 'csv')}
                download
                className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700 transition"
              >
                <Download className="w-3.5 h-3.5 mr-1" />
                CSV
              </a>
              <a
                href={optimizationApi.getExportUrl(activeJob.id, 'json')}
                download
                className="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700 transition"
              >
                <Download className="w-3.5 h-3.5 mr-1" />
                JSON
              </a>
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={loadInitialData}
            disabled={isLoading || isExecuting}
            className="border-slate-700 text-slate-300"
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Primary Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveTab('sweep')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'sweep'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          Sweep Config
        </button>

        <button
          onClick={() => setActiveTab('leaderboard')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'leaderboard'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Candidate Leaderboard
          {activeJob?.top_candidates && (
            <span className="ml-1 px-1.5 py-0.2 text-[10px] bg-sky-500/20 text-sky-300 rounded-full font-mono">
              {activeJob.top_candidates.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('heatmap')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'heatmap'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" />
          Sensitivity Surface
        </button>

        <button
          onClick={() => setActiveTab('walkforward')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'walkforward'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Walk-Forward Analysis (WFA)
          {activeJob?.walk_forward_result && (
            <span className={`ml-1 px-1.5 py-0.2 text-[10px] rounded-full font-mono ${
              activeJob.walk_forward_result.robustness_verdict === 'ROBUST'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-amber-500/20 text-amber-400'
            }`}>
              {activeJob.walk_forward_result.robustness_verdict}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('regimes')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'regimes'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Layers className="w-4 h-4" />
          Market Regimes
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          Job History
          {jobs.length > 0 && (
            <span className="ml-1 px-1.5 py-0.2 text-[10px] bg-slate-800 text-slate-400 rounded-full font-mono">
              {jobs.length}
            </span>
          )}
        </button>
      </div>

      {/* ─── TAB 1: SWEEP CONFIGURATION ────────────────────────────────────────── */}
      {activeTab === 'sweep' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sweep Parameters & Search Hypervolume */}
          <div className="lg:col-span-2 space-y-6">
            <Card className="p-6 bg-slate-900 border-slate-800 space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-amber-400" />
                  Search Hypervolume & Parameter Ranges
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  Adjust parameter boundaries and grid steps. All evaluations run chronologically without look-ahead bias.
                </p>
              </div>

              {/* Strategy Archetype Picker */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    STRATEGY ARCHETYPE
                  </label>
                  <select
                    value={selectedStrategyId}
                    onChange={(e) => handleStrategyChange(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-hidden focus:border-sky-500"
                  >
                    {strategies.map((s) => (
                      <option key={s.strategy_id} value={s.strategy_id}>
                        {s.name} ({s.strategy_id})
                      </option>
                    ))}
                    {strategies.length === 0 && (
                      <>
                        <option value="TrendFollowing">Trend Following (EMA Cross)</option>
                        <option value="MeanReversion">Mean Reversion (Bollinger + RSI)</option>
                        <option value="Breakout">Volatility Breakout (Donchian)</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-slate-400 mb-1">
                    OPTIMIZATION ENGINE
                  </label>
                  <select
                    value={optimizationMode}
                    onChange={(e) => setOptimizationMode(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-hidden focus:border-sky-500 font-mono"
                  >
                    <option value="GRID_SEARCH">Grid Search (Deterministic Cartesian)</option>
                    <option value="RANDOM_SEARCH">Random Search (Deterministic Seeded)</option>
                    <option value="WALK_FORWARD">Walk-Forward Analysis (IS/OOS AI Engine)</option>
                  </select>
                </div>
              </div>

              {/* Dynamic Parameter Ranges Table */}
              <div className="border border-slate-800 rounded-lg overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-800/60 border-b border-slate-800 text-xs font-mono font-medium text-slate-300 grid grid-cols-12 gap-2">
                  <div className="col-span-3">PARAMETER</div>
                  <div className="col-span-2">TYPE</div>
                  <div className="col-span-2">MIN</div>
                  <div className="col-span-2">MAX</div>
                  <div className="col-span-3">STEP / CHOICES</div>
                </div>

                <div className="divide-y divide-slate-800/60 bg-slate-900/40">
                  {paramRanges.map((range, idx) => (
                    <div key={range.name} className="px-4 py-3 grid grid-cols-12 gap-2 items-center text-xs">
                      <div className="col-span-3 font-mono font-medium text-sky-400">
                        {range.name}
                      </div>
                      <div className="col-span-2 font-mono text-slate-400">
                        {range.param_type}
                      </div>
                      <div className="col-span-2">
                        <input
                          type="number"
                          value={range.min_value}
                          onChange={(e) => updateRangeField(idx, 'min_value', Number(e.target.value))}
                          className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                        />
                      </div>
                      <div className="col-span-2">
                        <input
                          type="number"
                          value={range.max_value}
                          onChange={(e) => updateRangeField(idx, 'max_value', Number(e.target.value))}
                          className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                        />
                      </div>
                      <div className="col-span-3">
                        <input
                          type="number"
                          step="any"
                          value={range.step || 1}
                          onChange={(e) => updateRangeField(idx, 'step', Number(e.target.value))}
                          className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                          placeholder="Step"
                        />
                      </div>
                    </div>
                  ))}

                  {paramRanges.length === 0 && (
                    <div className="p-4 text-center text-xs text-slate-500">
                      No parameter ranges defined for this archetype.
                    </div>
                  )}
                </div>
              </div>

              {/* Combinatorial Protection Banner */}
              <div className="flex items-center justify-between p-3.5 bg-slate-800/40 border border-slate-800 rounded-lg">
                <div className="flex items-center gap-2.5">
                  <Info className="w-4 h-4 text-sky-400" />
                  <span className="text-xs text-slate-300">
                    Estimated Combinations: <strong className="font-mono text-sky-400">{estimatedCombinations}</strong>
                  </span>
                </div>
                {estimatedCombinations > maxCombinations && (
                  <Badge variant="warning" className="text-[10px]">
                    Capped at Max ({maxCombinations})
                  </Badge>
                )}
              </div>
            </Card>

            {/* Walk-Forward Settings (Visible when WALK_FORWARD is active) */}
            {optimizationMode === 'WALK_FORWARD' && (
              <Card className="p-6 bg-slate-900 border-amber-500/20 space-y-4">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-semibold text-slate-200 font-mono">
                    WALK-FORWARD SLICING CONFIGURATION
                  </h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      WINDOWS (N)
                    </label>
                    <input
                      type="number"
                      min={2}
                      max={10}
                      value={nWindows}
                      onChange={(e) => setNWindows(Math.max(2, Math.min(10, Number(e.target.value))))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      IN-SAMPLE RATIO (%)
                    </label>
                    <input
                      type="number"
                      step={0.05}
                      min={0.5}
                      max={0.85}
                      value={inSampleRatio}
                      onChange={(e) => setInSampleRatio(Number(e.target.value))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">
                      WINDOW TYPE
                    </label>
                    <select
                      value={isAnchored ? 'anchored' : 'rolling'}
                      onChange={(e) => setIsAnchored(e.target.value === 'anchored')}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono"
                    >
                      <option value="rolling">Rolling Window (Constant IS Length)</option>
                      <option value="anchored">Anchored Window (Expanding IS Length)</option>
                    </select>
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Right Column: Execution Controls & Institutional Simulation Setup */}
          <div className="space-y-6">
            <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-200 font-mono">
                EXECUTION & MARKET SETUP
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block font-mono text-slate-400 mb-1">CURRENCY PAIR</label>
                  <select
                    value={selectedSymbol}
                    onChange={(e) => setSelectedSymbol(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                  >
                    <option value="EUR/USD">EUR/USD (Major)</option>
                    <option value="GBP/USD">GBP/USD (Major)</option>
                    <option value="USD/JPY">USD/JPY (Major)</option>
                    <option value="AUD/USD">AUD/USD (Commodity)</option>
                    <option value="USD/CHF">USD/CHF (Safe Haven)</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block font-mono text-slate-400 mb-1">TIMEFRAME</label>
                    <select
                      value={selectedTimeframe}
                      onChange={(e) => setSelectedTimeframe(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                    >
                      <option value="M5">M5 (5 Minutes)</option>
                      <option value="M15">M15 (15 Minutes)</option>
                      <option value="H1">H1 (1 Hour)</option>
                      <option value="H4">H4 (4 Hours)</option>
                      <option value="D1">D1 (Daily)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-mono text-slate-400 mb-1">INITIAL CAPITAL</label>
                    <input
                      type="number"
                      value={initialCapital}
                      onChange={(e) => setInitialCapital(Number(e.target.value))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block font-mono text-slate-400 mb-1">START DATE</label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-slate-400 mb-1">END DATE</label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-mono text-slate-400 mb-1">FITNESS OBJECTIVE</label>
                  <select
                    value={fitnessObjective}
                    onChange={(e) => setFitnessObjective(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                  >
                    <option value="SHARPE_RATIO">Sharpe Ratio (Risk-Adjusted)</option>
                    <option value="SORTINO_RATIO">Sortino Ratio (Downside Risk)</option>
                    <option value="CALMAR_RATIO">Calmar Ratio (Drawdown Efficiency)</option>
                    <option value="PROFIT_FACTOR">Profit Factor (Gross Win / Gross Loss)</option>
                    <option value="TOTAL_RETURN">Total Return (%)</option>
                    <option value="WIN_RATE">Win Rate (%)</option>
                    <option value="MIN_DRAWDOWN">Minimum Peak Drawdown</option>
                    <option value="COMPOSITE">Multi-Objective Institutional Composite</option>
                  </select>
                </div>

                {optimizationMode === 'RANDOM_SEARCH' && (
                  <div>
                    <label className="block font-mono text-slate-400 mb-1">RANDOM SAMPLES (N)</label>
                    <input
                      type="number"
                      value={nSamples}
                      onChange={(e) => setNSamples(Number(e.target.value))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                    />
                  </div>
                )}

                <div>
                  <label className="block font-mono text-slate-400 mb-1">MAX COMBINATIONS CAP</label>
                  <input
                    type="number"
                    value={maxCombinations}
                    onChange={(e) => setMaxCombinations(Number(e.target.value))}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono"
                  />
                </div>

                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-500">ADVERSE MICROSTRUCTURE FRICTION</div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <span className="text-[10px] text-slate-400">Spread (pips)</span>
                      <input
                        type="number"
                        step={0.1}
                        value={spreadPips}
                        onChange={(e) => setSpreadPips(Number(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono text-xs"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Slippage (pips)</span>
                      <input
                        type="number"
                        step={0.1}
                        value={slippagePips}
                        onChange={(e) => setSlippagePips(Number(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono text-xs"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Comm ($/lot)</span>
                      <input
                        type="number"
                        step={0.5}
                        value={commission}
                        onChange={(e) => setCommission(Number(e.target.value))}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <Button
                  onClick={handleLaunchSweep}
                  disabled={isExecuting || isLoading}
                  className="w-full bg-sky-600 hover:bg-sky-500 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2"
                >
                  <Play className={`w-4 h-4 ${isExecuting ? 'animate-spin' : ''}`} />
                  {isExecuting ? 'Evaluating Candidates...' : 'Launch Optimization Run'}
                </Button>
              </div>
            </Card>

            {/* Zero Look-Ahead Safety Callout */}
            <Card className="p-4 bg-slate-900 border-sky-500/20 text-xs text-slate-400 flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-200 block mb-1">LeakageGuard Active</strong>
                Deterministic chronological bar-by-bar execution. Strict IS/OOS boundary guarantees out-of-sample data never contaminates model parameter selection.
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* ─── TAB 2: CANDIDATE LEADERBOARD ──────────────────────────────────────── */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-6">
          {activeJob ? (
            <>
              {/* Job Header Summary Card */}
              <Card className="p-5 bg-slate-900 border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-slate-400">JOB ID:</span>
                    <span className="font-mono text-xs text-sky-400 font-semibold">{activeJob.id}</span>
                    <Badge variant={activeJob.status === 'COMPLETED' ? 'success' : 'info'}>
                      {activeJob.status}
                    </Badge>
                  </div>
                  <div className="text-sm font-medium text-slate-200 mt-1">
                    {activeJob.strategy_id} &bull; {activeJob.symbol} &bull; {activeJob.timeframe} &bull; {activeJob.optimization_type}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div className="p-2.5 bg-slate-800/40 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 font-mono">EVALUATIONS</div>
                    <div className="text-base font-bold text-slate-100 font-mono">
                      {activeJob.completed_combinations} / {activeJob.total_combinations}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-800/40 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 font-mono">EXECUTION TIME</div>
                    <div className="text-base font-bold text-slate-100 font-mono">
                      {activeJob.execution_time_seconds.toFixed(2)}s
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-800/40 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 font-mono">BEST SHARPE</div>
                    <div className="text-base font-bold text-emerald-400 font-mono">
                      {activeJob.best_metrics?.sharpe_ratio?.toFixed(2) ?? '-'}
                    </div>
                  </div>
                  <div className="p-2.5 bg-slate-800/40 rounded-lg border border-slate-800">
                    <div className="text-[10px] text-slate-400 font-mono">BEST RETURN</div>
                    <div className="text-base font-bold text-sky-400 font-mono">
                      {activeJob.best_metrics?.total_return ? `${(activeJob.best_metrics.total_return * 100).toFixed(1)}%` : '-'}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Candidates Leaderboard Table */}
              <Card className="bg-slate-900 border-slate-800 overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-sky-400" />
                    RANKED CANDIDATES ({activeJob.top_candidates?.length || 0})
                  </h3>
                  <div className="text-xs text-slate-400 font-mono">
                    Objective: {activeJob.fitness_objective}
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">RANK</th>
                        <th className="px-4 py-3">PARAMETERS</th>
                        <th className="px-4 py-3 text-right">FITNESS</th>
                        <th className="px-4 py-3 text-right">SHARPE</th>
                        <th className="px-4 py-3 text-right">SORTINO</th>
                        <th className="px-4 py-3 text-right">RETURN</th>
                        <th className="px-4 py-3 text-right">DRAWDOWN</th>
                        <th className="px-4 py-3 text-right">WIN RATE</th>
                        <th className="px-4 py-3 text-right">TRADES</th>
                        <th className="px-4 py-3 text-right">NET PNL</th>
                        <th className="px-4 py-3 text-right">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {activeJob.top_candidates?.map((cand) => (
                        <tr key={cand.rank} className="hover:bg-slate-800/30 transition">
                          <td className="px-4 py-3 font-bold text-amber-400">
                            #{cand.rank}
                          </td>
                          <td className="px-4 py-3 font-mono text-slate-300">
                            {Object.entries(cand.parameters)
                              .map(([k, v]) => `${k}=${v}`)
                              .join(', ')}
                          </td>
                          <td className="px-4 py-3 text-right font-bold text-sky-400">
                            {cand.fitness_score.toFixed(3)}
                          </td>
                          <td className={`px-4 py-3 text-right font-bold ${
                            cand.sharpe_ratio >= 1.5 ? 'text-emerald-400' : cand.sharpe_ratio >= 0 ? 'text-slate-200' : 'text-rose-400'
                          }`}>
                            {cand.sharpe_ratio.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {cand.sortino_ratio.toFixed(2)}
                          </td>
                          <td className={`px-4 py-3 text-right font-medium ${
                            cand.total_return >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}>
                            {(cand.total_return * 100).toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-right text-rose-400">
                            {(cand.max_drawdown * 100).toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-right">
                            {(cand.win_rate * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-3 text-right text-slate-400">
                            {cand.total_trades}
                          </td>
                          <td className={`px-4 py-3 text-right font-semibold ${
                            cand.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}>
                            ${cand.net_pnl.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handlePromoteToPaper(cand.rank)}
                              className="px-2.5 py-1 text-[11px] bg-indigo-600/80 hover:bg-indigo-500 text-white rounded font-medium inline-flex items-center gap-1 transition cursor-pointer"
                            >
                              <Rocket className="w-3 h-3" /> Promote
                            </button>
                          </td>
                        </tr>
                      ))}

                      {(!activeJob.top_candidates || activeJob.top_candidates.length === 0) && (
                        <tr>
                          <td colSpan={11} className="px-4 py-8 text-center text-slate-500">
                            No candidates recorded for this job.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </>
          ) : (
            <Card className="p-12 text-center bg-slate-900 border-slate-800 space-y-3">
              <BarChart3 className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-medium text-slate-300">No Active Optimization Run</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Configure parameter search ranges and execute a sweep in the Sweep Config tab, or pick a past run from Job History.
              </p>
              <Button onClick={() => setActiveTab('sweep')} variant="outline" size="sm">
                Go to Sweep Config
              </Button>
            </Card>
          )}
        </div>
      )}

      {/* ─── TAB 3: SENSITIVITY SURFACE & HEATMAP ──────────────────────────────── */}
      {activeTab === 'heatmap' && (
        <div className="space-y-6">
          {activeJob?.heatmap ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <Card className="p-6 bg-slate-900 border-slate-800 lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <Activity className="w-4 h-4 text-sky-400" />
                    2D PARAMETER SENSITIVITY HEATMAP
                  </h3>
                  <div className="text-xs font-mono text-slate-400">
                    {activeJob.heatmap.param1_name} vs {activeJob.heatmap.param2_name}
                  </div>
                </div>

                {/* Heatmap Matrix Display */}
                <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800 flex flex-col items-center justify-center">
                  <div className="text-xs text-slate-400 mb-2 font-mono">
                    Fitness Score Surface (Min: {activeJob.heatmap.min_fitness.toFixed(2)}, Max: {activeJob.heatmap.max_fitness.toFixed(2)})
                  </div>

                  {/* SVG Heatmap Grid */}
                  <div className="grid grid-cols-6 sm:grid-cols-8 gap-1.5 p-2 bg-slate-900/80 rounded border border-slate-800 max-w-full overflow-x-auto">
                    {activeJob.heatmap.points.map((pt, idx) => {
                      const range = activeJob.heatmap!.max_fitness - activeJob.heatmap!.min_fitness;
                      const norm = range > 0.0001 ? (pt.fitness_score - activeJob.heatmap!.min_fitness) / range : 0.5;
                      // Color mapping: 0 -> rose, 0.5 -> yellow, 1 -> emerald
                      const bg = norm > 0.7
                        ? 'bg-emerald-500/80 text-slate-900 font-bold'
                        : norm > 0.4
                        ? 'bg-amber-500/70 text-slate-900'
                        : 'bg-rose-500/60 text-slate-100';

                      return (
                        <div
                          key={idx}
                          title={`${activeJob.heatmap!.param1_name}: ${pt.param1_value}, ${activeJob.heatmap!.param2_name}: ${pt.param2_value} -> Score: ${pt.fitness_score.toFixed(2)}`}
                          className={`p-2 rounded text-[10px] font-mono text-center cursor-pointer transition hover:scale-105 ${bg}`}
                        >
                          <div className="text-[9px] opacity-80">{pt.param1_value},{pt.param2_value}</div>
                          <div>{pt.fitness_score.toFixed(1)}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </Card>

              {/* Parameter Stability & Cliff Detection Side Panel */}
              <div className="space-y-6">
                <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    PLATEAU STABILITY VERDICT
                  </h3>

                  {activeJob.stability_analysis ? (
                    <div className="space-y-4">
                      <div>
                        <div className="text-xs text-slate-400 font-mono">PLATEAU SCORE</div>
                        <div className="text-2xl font-bold font-mono text-sky-400">
                          {activeJob.stability_analysis.plateau_stability_score.toFixed(1)} / 100
                        </div>
                      </div>

                      <div>
                        <div className="text-xs text-slate-400 font-mono">MAX NEIGHBOR DEGRADATION</div>
                        <div className="text-lg font-bold font-mono text-rose-400">
                          {activeJob.stability_analysis.max_neighbor_drop_pct.toFixed(1)}%
                        </div>
                      </div>

                      <div className="p-3 bg-slate-800/40 rounded-lg border border-slate-800">
                        <div className="flex items-center gap-2 mb-1">
                          {activeJob.stability_analysis.is_cliff ? (
                            <>
                              <AlertTriangle className="w-4 h-4 text-rose-400" />
                              <span className="text-xs font-bold text-rose-400">PARAMETER CLIFF DETECTED</span>
                            </>
                          ) : (
                            <>
                              <ShieldCheck className="w-4 h-4 text-emerald-400" />
                              <span className="text-xs font-bold text-emerald-400">ROBUST BROAD PLATEAU</span>
                            </>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {activeJob.stability_analysis.cliff_details}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-500">
                      Neighborhood stability analysis available for grid optimizations with &ge; 2 parameters.
                    </div>
                  )}
                </Card>
              </div>
            </div>
          ) : (
            <Card className="p-12 text-center bg-slate-900 border-slate-800 space-y-3">
              <Activity className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-medium text-slate-300">No Heatmap Data</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Run a 2-parameter Grid Search optimization sweep to generate interactive 2D fitness surfaces and cliff analyses.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─── TAB 4: WALK-FORWARD ANALYSIS (WFA) ─────────────────────────────────── */}
      {activeTab === 'walkforward' && (
        <div className="space-y-6">
          {activeJob?.walk_forward_result ? (
            <>
              {/* Aggregated WFA Header */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <Card className="p-4 bg-slate-900 border-slate-800">
                  <div className="text-xs font-mono text-slate-400">ROBUSTNESS VERDICT</div>
                  <div className="text-xl font-bold font-mono mt-1">
                    <Badge
                      variant={
                        activeJob.walk_forward_result.robustness_verdict === 'ROBUST'
                          ? 'success'
                          : activeJob.walk_forward_result.robustness_verdict === 'MODERATE'
                          ? 'warning'
                          : 'danger'
                      }
                      className="text-sm px-2.5 py-1"
                    >
                      {activeJob.walk_forward_result.robustness_verdict}
                    </Badge>
                  </div>
                </Card>

                <Card className="p-4 bg-slate-900 border-slate-800">
                  <div className="text-xs font-mono text-slate-400">MEAN WFE RATIO</div>
                  <div className={`text-xl font-bold font-mono mt-1 ${
                    (activeJob.walk_forward_result.mean_wfe || 0) >= 60 ? 'text-emerald-400' : 'text-amber-400'
                  }`}>
                    {activeJob.walk_forward_result.mean_wfe !== null && activeJob.walk_forward_result.mean_wfe !== undefined
                      ? `${activeJob.walk_forward_result.mean_wfe.toFixed(1)}%`
                      : 'N/A'}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Threshold: &ge; 60% for ROBUST</div>
                </Card>

                <Card className="p-4 bg-slate-900 border-slate-800">
                  <div className="text-xs font-mono text-slate-400">OOS ANNUALIZED RETURN</div>
                  <div className={`text-xl font-bold font-mono mt-1 ${
                    activeJob.walk_forward_result.annualized_oos_return >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {(activeJob.walk_forward_result.annualized_oos_return * 100).toFixed(2)}%
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Concatenated Out-of-Sample</div>
                </Card>

                <Card className="p-4 bg-slate-900 border-slate-800">
                  <div className="text-xs font-mono text-slate-400">OOS SHARPE RATIO</div>
                  <div className="text-xl font-bold font-mono text-sky-400 mt-1">
                    {activeJob.walk_forward_result.annualized_oos_sharpe.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">Mean forward efficiency</div>
                </Card>
              </div>

              {/* Windows Breakdown Table */}
              <Card className="bg-slate-900 border-slate-800 overflow-hidden">
                <div className="p-4 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-sky-400" />
                    IN-SAMPLE VS OUT-OF-SAMPLE WINDOW RESULTS
                  </h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">WINDOW</th>
                        <th className="px-4 py-3">IN-SAMPLE DATES</th>
                        <th className="px-4 py-3">OUT-OF-SAMPLE DATES</th>
                        <th className="px-4 py-3">OPTIMAL PARAMETERS</th>
                        <th className="px-4 py-3 text-right">IS RETURN</th>
                        <th className="px-4 py-3 text-right">OOS RETURN</th>
                        <th className="px-4 py-3 text-right">WFE (%)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300">
                      {activeJob.walk_forward_result.windows.map((win) => (
                        <tr key={win.window_index} className="hover:bg-slate-800/30">
                          <td className="px-4 py-3 font-bold text-sky-400">
                            Window {win.window_index + 1}
                          </td>
                          <td className="px-4 py-3 text-slate-400">
                            {new Date(win.is_start).toLocaleDateString()} &rarr; {new Date(win.is_end).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3 text-amber-300/80">
                            {new Date(win.oos_start).toLocaleDateString()} &rarr; {new Date(win.oos_end).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3 text-slate-200">
                            {Object.entries(win.optimal_parameters)
                              .map(([k, v]) => `${k}=${v}`)
                              .join(', ')}
                          </td>
                          <td className="px-4 py-3 text-right text-emerald-400 font-medium">
                            {(win.is_return * 100).toFixed(2)}%
                          </td>
                          <td className={`px-4 py-3 text-right font-medium ${
                            win.oos_return >= 0 ? 'text-emerald-400' : 'text-rose-400'
                          }`}>
                            {(win.oos_return * 100).toFixed(2)}%
                          </td>
                          <td className={`px-4 py-3 text-right font-bold ${
                            win.efficiency_ratio !== null && win.efficiency_ratio !== undefined && win.efficiency_ratio >= 60
                              ? 'text-emerald-400'
                              : 'text-amber-400'
                          }`}>
                            {win.efficiency_ratio !== null && win.efficiency_ratio !== undefined ? `${win.efficiency_ratio.toFixed(1)}%` : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Concatenated Out-of-Sample Equity Curve */}
              {activeJob.walk_forward_result.concatenated_oos_equity.length > 0 && (
                <Card className="p-6 bg-slate-900 border-slate-800 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
                    <Activity className="w-4 h-4 text-sky-400" />
                    CONCATENATED OUT-OF-SAMPLE EQUITY TRAJECTORY
                  </h3>
                  <div className="p-4 bg-slate-950/60 rounded-lg border border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
                    <div>
                      <span>Initial: <strong className="text-slate-200">${activeJob.initial_capital}</strong></span>
                      <span className="mx-2">&bull;</span>
                      <span>
                        Final OOS Equity:{' '}
                        <strong className="text-emerald-400">
                          ${activeJob.walk_forward_result.concatenated_oos_equity.slice(-1)[0]?.equity.toFixed(2)}
                        </strong>
                      </span>
                    </div>
                    <div>
                      <span>Points: <strong className="text-slate-200">{activeJob.walk_forward_result.concatenated_oos_equity.length}</strong></span>
                    </div>
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Card className="p-12 text-center bg-slate-900 border-slate-800 space-y-3">
              <TrendingUp className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-medium text-slate-300">No Walk-Forward Results</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Launch a Walk-Forward Analysis in the Sweep Config tab to partition historical data into rolling/anchored In-Sample and Out-of-Sample segments.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─── TAB 5: MARKET REGIMES BREAKDOWN ──────────────────────────────────── */}
      {activeTab === 'regimes' && (
        <div className="space-y-6">
          {activeJob?.regime_breakdowns && activeJob.regime_breakdowns.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {activeJob.regime_breakdowns.map((regime) => (
                <Card key={regime.regime_name} className="p-5 bg-slate-900 border-slate-800 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-sky-400" />
                      <h3 className="text-sm font-bold text-slate-100 font-mono">
                        {regime.regime_name.replace(/_/g, ' ')}
                      </h3>
                    </div>
                    <Badge variant={regime.win_rate >= 0.5 ? 'success' : 'default'} className="text-[10px]">
                      {regime.trade_count} Trades
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                    <div className="p-2.5 bg-slate-800/40 rounded border border-slate-800">
                      <div className="text-slate-400 text-[10px]">WIN RATE</div>
                      <div className="text-sm font-bold text-slate-100">
                        {(regime.win_rate * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="p-2.5 bg-slate-800/40 rounded border border-slate-800">
                      <div className="text-slate-400 text-[10px]">PROFIT FACTOR</div>
                      <div className="text-sm font-bold text-sky-400">
                        {regime.profit_factor.toFixed(2)}
                      </div>
                    </div>
                    <div className="p-2.5 bg-slate-800/40 rounded border border-slate-800">
                      <div className="text-slate-400 text-[10px]">TOTAL RETURN</div>
                      <div className={`text-sm font-bold ${regime.total_return >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {(regime.total_return * 100).toFixed(2)}%
                      </div>
                    </div>
                    <div className="p-2.5 bg-slate-800/40 rounded border border-slate-800">
                      <div className="text-slate-400 text-[10px]">SHARPE RATIO</div>
                      <div className="text-sm font-bold text-slate-200">
                        {regime.sharpe_ratio.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="p-12 text-center bg-slate-900 border-slate-800 space-y-3">
              <Layers className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-medium text-slate-300">No Regime Breakdown Available</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Execute an optimization or walk-forward run to inspect performance attribution across Trending Bull, Trending Bear, Low Volatility Range, and High Volatility Chop market regimes.
              </p>
            </Card>
          )}
        </div>
      )}

      {/* ─── TAB 6: JOB HISTORY ─────────────────────────────────────────────────── */}
      {activeTab === 'history' && (
        <Card className="bg-slate-900 border-slate-800 overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 font-mono flex items-center gap-2">
              <History className="w-4 h-4 text-sky-400" />
              ORGANIZATION OPTIMIZATION RUNS ({jobs.length})
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-800/60 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">JOB ID</th>
                  <th className="px-4 py-3">STRATEGY</th>
                  <th className="px-4 py-3">PAIR & TIMEFRAME</th>
                  <th className="px-4 py-3">TYPE</th>
                  <th className="px-4 py-3">STATUS</th>
                  <th className="px-4 py-3 text-right">COMBINATIONS</th>
                  <th className="px-4 py-3 text-right">BEST SHARPE</th>
                  <th className="px-4 py-3 text-right">TIME</th>
                  <th className="px-4 py-3 text-center">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-4 py-3 font-bold text-sky-400">
                      {job.id}
                    </td>
                    <td className="px-4 py-3 text-slate-200 font-medium">
                      {job.strategy_id}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {job.symbol} ({job.timeframe})
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="default" className="text-[10px]">
                        {job.optimization_type}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          job.status === 'COMPLETED'
                            ? 'success'
                            : job.status === 'FAILED'
                            ? 'danger'
                            : job.status === 'RUNNING'
                            ? 'info'
                            : 'default'
                        }
                        className="text-[10px]"
                      >
                        {job.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {job.completed_combinations} / {job.total_combinations}
                    </td>
                    <td className="px-4 py-3 text-right font-bold text-emerald-400">
                      {job.best_sharpe !== null && job.best_sharpe !== undefined ? job.best_sharpe.toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-400">
                      {job.execution_time_seconds.toFixed(1)}s
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSelectJob(job.id)}
                        className="text-[10px] py-1 px-2 border-slate-700 hover:bg-slate-800"
                      >
                        View Results
                      </Button>
                    </td>
                  </tr>
                ))}

                {jobs.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                      No optimization jobs found for this organization.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
export default OptimizationStudioPage;
