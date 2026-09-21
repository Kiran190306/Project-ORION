import React, { useEffect, useState, useMemo } from 'react';
import {
  Rocket,
  ShieldCheck,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Pause,
  Play,
  RotateCcw,
  Clock,
  BarChart2,
  TrendingUp,
  FileText,
  Lock,
} from 'lucide-react';
import { deploymentApi } from '../api/endpoints';
import type {
  DeploymentDetail,
  DeploymentSummary,
} from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { useOrganization } from '../auth/OrganizationContext';
import { Permission, hasPermission } from '../auth/permissions';
import { useToast } from '../components/common/Toast';

export const DeploymentPipelinePage: React.FC = () => {
  const { user } = useAuth();
  const { currentRole } = useOrganization();
  const toast = useToast();

  const canExecute = hasPermission(currentRole, Permission.DEPLOYMENT_EXECUTE, user?.is_superuser);
  const canCancel = hasPermission(currentRole, Permission.DEPLOYMENT_CANCEL, user?.is_superuser);
  const canPromote = hasPermission(currentRole, Permission.DEPLOYMENT_PROMOTE, user?.is_superuser);

  const [activeTab, setActiveTab] = useState<'pipeline' | 'incubator' | 'quality_gates' | 'history'>('pipeline');
  const [deployments, setDeployments] = useState<DeploymentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<DeploymentDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchDeployments = async () => {
    try {
      setLoading(true);
      const res = await deploymentApi.listDeployments({ limit: 50 });
      setDeployments(res.items);
      if (res.items.length > 0 && !selectedId) {
        setSelectedId(res.items[0].id);
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to fetch deployments');
    } finally {
      setLoading(false);
    }
  };

  const fetchDetail = async (id: string) => {
    try {
      const detail = await deploymentApi.getDeployment(id);
      setSelectedDetail(detail);
    } catch (err: any) {
      toast.error(err.message || 'Failed to fetch deployment details');
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  useEffect(() => {
    if (selectedId) {
      fetchDetail(selectedId);
    }
  }, [selectedId]);

  // Derived metrics
  const activeCount = useMemo(
    () => deployments.filter((d) => ['PENDING_GATES', 'GATES_PASSED', 'INCUBATING', 'PAUSED'].includes(d.status)).length,
    [deployments]
  );
  const incubatingCount = useMemo(
    () => deployments.filter((d) => d.status === 'INCUBATING').length,
    [deployments]
  );
  const validatedCount = useMemo(
    () => deployments.filter((d) => d.status === 'PAPER_VALIDATED').length,
    [deployments]
  );
  const candidateCount = useMemo(
    () => deployments.filter((d) => d.status === 'PROMOTION_CANDIDATE').length,
    [deployments]
  );

  const filteredDeployments = useMemo(() => {
    if (statusFilter === 'ALL') return deployments;
    return deployments.filter((d) => d.status === statusFilter);
  }, [deployments, statusFilter]);

  // Actions
  const handlePause = async (id: string) => {
    try {
      setActionLoading(true);
      await deploymentApi.pauseDeployment(id, 'Paused via dashboard');
      toast.info('Deployment paused');
      await fetchDeployments();
      await fetchDetail(id);
    } catch (err: any) {
      toast.error(err.message || 'Failed to pause deployment');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResume = async (id: string) => {
    try {
      setActionLoading(true);
      await deploymentApi.resumeDeployment(id, 'Resumed via dashboard');
      toast.success('Deployment resumed to INCUBATING');
      await fetchDeployments();
      await fetchDetail(id);
    } catch (err: any) {
      toast.error(err.message || 'Failed to resume deployment');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    if (!window.confirm('Are you sure you want to cancel this deployment? This is terminal.')) return;
    try {
      setActionLoading(true);
      await deploymentApi.cancelDeployment(id, 'Cancelled via dashboard');
      toast.warning('Deployment cancelled');
      await fetchDeployments();
      await fetchDetail(id);
    } catch (err: any) {
      toast.error(err.message || 'Failed to cancel deployment');
    } finally {
      setActionLoading(false);
    }
  };

  const handleValidate = async (id: string) => {
    try {
      setActionLoading(true);
      const res = await deploymentApi.validateDeployment(id, 'Manual validation evaluation');
      if (res.status === 'PAPER_VALIDATED') {
        toast.success('Incubation PASSED: Deployment marked as PAPER_VALIDATED');
      } else {
        toast.error('Incubation FAILED: Policy criteria breached');
      }
      await fetchDeployments();
      await fetchDetail(id);
    } catch (err: any) {
      toast.error(err.message || 'Validation evaluation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePromoteCandidate = async (id: string) => {
    if (!window.confirm('Mark this validated strategy as a PROMOTION CANDIDATE for governance review? (EPIC-025 Terminal State)')) return;
    try {
      setActionLoading(true);
      await deploymentApi.promoteToCandidate(id, 'Advanced to promotion candidate review');
      toast.success('Strategy marked as PROMOTION_CANDIDATE (Paper Review)');
      await fetchDeployments();
      await fetchDetail(id);
    } catch (err: any) {
      toast.error(err.message || 'Promotion candidate review failed');
    } finally {
      setActionLoading(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'INCUBATING':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-900/60 text-blue-300 border border-blue-700/50 flex items-center gap-1"><Activity className="w-3 h-3 animate-pulse" /> INCUBATING</span>;
      case 'PAPER_VALIDATED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> PAPER_VALIDATED</span>;
      case 'PROMOTION_CANDIDATE':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-900/60 text-purple-300 border border-purple-700/50 flex items-center gap-1"><Rocket className="w-3 h-3" /> PROMOTION_CANDIDATE</span>;
      case 'GATES_PASSED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-900/60 text-cyan-300 border border-cyan-700/50">GATES_PASSED</span>;
      case 'PAUSED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-900/60 text-amber-300 border border-amber-700/50 flex items-center gap-1"><Pause className="w-3 h-3" /> PAUSED</span>;
      case 'GATES_FAILED':
      case 'INCUBATION_FAILED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-900/60 text-rose-300 border border-rose-700/50 flex items-center gap-1"><XCircle className="w-3 h-3" /> {status}</span>;
      case 'CANCELLED':
      case 'SUSPENDED':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">{status}</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300">{status}</span>;
    }
  };

  const renderVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case 'PASS':
        return <span className="text-emerald-400 font-semibold flex items-center gap-1 text-sm"><CheckCircle2 className="w-4 h-4" /> PASS</span>;
      case 'FAIL':
        return <span className="text-rose-400 font-semibold flex items-center gap-1 text-sm"><XCircle className="w-4 h-4" /> FAIL</span>;
      case 'INCONCLUSIVE':
        return <span className="text-amber-400 font-semibold flex items-center gap-1 text-sm"><AlertTriangle className="w-4 h-4" /> INCONCLUSIVE</span>;
      case 'INSUFFICIENT_DATA':
        return <span className="text-slate-400 font-semibold flex items-center gap-1 text-sm"><HelpCircle className="w-4 h-4" /> INSUFFICIENT_DATA</span>;
      default:
        return <span className="text-slate-400 text-sm">{verdict}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20 text-indigo-400">
              <Rocket className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Strategy Deployment Pipeline & Paper Incubator</h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Stage-gate quantitative deployment, multi-factor quality hurdles, and paper incubation telemetry ($0.00 Capital at Risk).
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDeployments}
            disabled={loading}
            className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 flex items-center gap-1.5 transition-colors"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <div className="px-3 py-1.5 text-xs bg-emerald-950/40 text-emerald-400 border border-emerald-800/50 rounded flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5" /> Paper-Only Guard Active ($0 Live Risk)
          </div>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>ACTIVE DEPLOYMENTS</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{activeCount}</span>
            <span className="text-xs text-slate-500">pipeline slots active</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>IN PAPER INCUBATION</span>
            <Clock className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-cyan-300">{incubatingCount}</span>
            <span className="text-xs text-slate-500">live observation</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>PAPER VALIDATED</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-300">{validatedCount}</span>
            <span className="text-xs text-slate-500">hurdles met</span>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>PROMOTION CANDIDATES</span>
            <Rocket className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-purple-300">{candidateCount}</span>
            <span className="text-xs text-slate-500">review ready</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'pipeline'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Activity className="w-4 h-4" /> Active Pipeline ({deployments.length})
        </button>
        <button
          onClick={() => setActiveTab('incubator')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'incubator'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart2 className="w-4 h-4" /> Incubation Telemetry
        </button>
        <button
          onClick={() => setActiveTab('quality_gates')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'quality_gates'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <ShieldCheck className="w-4 h-4" /> 5-Gate Quality Hurdle
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'history'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FileText className="w-4 h-4" /> Deployment Audit Log
        </button>
      </div>

      {/* Tab 1: Pipeline View */}
      {activeTab === 'pipeline' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Filter status:</span>
              {['ALL', 'INCUBATING', 'PAPER_VALIDATED', 'PAUSED', 'GATES_FAILED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded text-xs transition-colors ${
                    statusFilter === st
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {filteredDeployments.length === 0 ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-12 text-center">
              <Rocket className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-base font-medium text-slate-300">No deployments found</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Promote top candidates from the Optimization Studio or Strategy Lab to begin paper incubation.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredDeployments.map((d) => (
                <div
                  key={d.id}
                  onClick={() => setSelectedId(d.id)}
                  className={`bg-slate-900 border rounded-xl p-5 cursor-pointer transition-all hover:border-slate-700 ${
                    selectedId === d.id ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-mono text-slate-500">{d.id}</span>
                    {renderStatusBadge(d.status)}
                  </div>
                  <h3 className="text-base font-semibold text-white">{d.strategy_id}</h3>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                    <span>{d.symbol}</span>
                    <span>•</span>
                    <span>{d.timeframe}</span>
                    <span>•</span>
                    <span>${Number(d.initial_capital).toLocaleString()} paper</span>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-xs text-slate-500">
                      Created {new Date(d.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedId(d.id);
                        setActiveTab('incubator');
                      }}
                      className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                    >
                      View Telemetry →
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Incubation Telemetry View */}
      {activeTab === 'incubator' && selectedDetail && (
        <div className="space-y-6">
          {/* Selected Deployment Banner */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-slate-400">{selectedDetail.id}</span>
                {renderStatusBadge(selectedDetail.status)}
              </div>
              <h2 className="text-xl font-bold text-white">{selectedDetail.strategy_id} — {selectedDetail.symbol} ({selectedDetail.timeframe})</h2>
              <p className="text-xs text-slate-400 mt-1">
                Paper Account: ${Number(selectedDetail.initial_capital).toLocaleString()} • Target: {selectedDetail.incubation_config.min_duration_days} days & {selectedDetail.incubation_config.min_trade_count} trades
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {selectedDetail.status === 'INCUBATING' && canCancel && (
                <button
                  onClick={() => handlePause(selectedDetail.id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-amber-300 rounded border border-amber-700/40 flex items-center gap-1.5"
                >
                  <Pause className="w-3.5 h-3.5" /> Pause
                </button>
              )}

              {selectedDetail.status === 'PAUSED' && canExecute && (
                <button
                  onClick={() => handleResume(selectedDetail.id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-emerald-300 rounded border border-emerald-700/40 flex items-center gap-1.5"
                >
                  <Play className="w-3.5 h-3.5" /> Resume
                </button>
              )}

              {selectedDetail.status === 'INCUBATING' && canPromote && (
                <button
                  onClick={() => handleValidate(selectedDetail.id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded flex items-center gap-1.5"
                >
                  <ShieldCheck className="w-3.5 h-3.5" /> Evaluate & Validate
                </button>
              )}

              {selectedDetail.status === 'PAPER_VALIDATED' && canPromote && (
                <button
                  onClick={() => handlePromoteCandidate(selectedDetail.id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-500 text-white font-medium rounded flex items-center gap-1.5"
                >
                  <Rocket className="w-3.5 h-3.5" /> Mark Promotion Candidate
                </button>
              )}

              {['INCUBATING', 'PAUSED'].includes(selectedDetail.status) && canCancel && (
                <button
                  onClick={() => handleCancel(selectedDetail.id)}
                  disabled={actionLoading}
                  className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-rose-300 rounded border border-rose-700/40 flex items-center gap-1.5"
                >
                  <XCircle className="w-3.5 h-3.5" /> Cancel
                </button>
              )}
            </div>
          </div>

          {/* Incubation vs Benchmark Side-by-Side Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Paper Incubation Performance */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-semibold text-white">Live Paper Incubation Telemetry</h3>
                </div>
                <span className="text-xs text-slate-400">
                  {selectedDetail.incubation_metrics?.trading_days || 0} days active
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Paper Return</span>
                  <p className="text-lg font-bold text-emerald-400">
                    +{selectedDetail.incubation_metrics?.total_return_pct ?? 0}%
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Paper Sharpe</span>
                  <p className="text-lg font-bold text-white">
                    {selectedDetail.incubation_metrics?.sharpe_ratio ?? 0}
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Paper Max DD</span>
                  <p className="text-lg font-bold text-rose-400">
                    {selectedDetail.incubation_metrics?.max_drawdown_pct ?? 0}%
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Trades Executed</span>
                  <p className="text-lg font-bold text-white">
                    {selectedDetail.incubation_metrics?.total_trades ?? 0}
                  </p>
                </div>
              </div>

              <div className="pt-2 text-xs text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Daily Loss Violations:</span>
                  <span className="font-semibold text-white">{selectedDetail.incubation_metrics?.daily_loss_violations ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Risk Limit Violations:</span>
                  <span className="font-semibold text-white">{selectedDetail.incubation_metrics?.risk_violations ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Market Data Quality Score:</span>
                  <span className="font-semibold text-emerald-400">
                    {((selectedDetail.incubation_metrics?.data_quality_score ?? 1) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Backtest Benchmark Comparison */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">Backtest Benchmark Fidelity</h3>
                </div>
                <span className="text-xs text-slate-400">Prior In-Sample Benchmark</span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Backtest Return</span>
                  <p className="text-lg font-bold text-slate-300">
                    +{selectedDetail.benchmark_comparison?.backtest_return_pct ?? selectedDetail.backtest_benchmark?.total_return_pct ?? 0}%
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Backtest Sharpe</span>
                  <p className="text-lg font-bold text-slate-300">
                    {selectedDetail.benchmark_comparison?.backtest_sharpe ?? selectedDetail.backtest_benchmark?.sharpe_ratio ?? 0}
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Return Ratio (Fidelity)</span>
                  <p className="text-lg font-bold text-cyan-400">
                    {(selectedDetail.benchmark_comparison?.return_ratio ?? 0) * 100}%
                  </p>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <span className="text-xs text-slate-500">Sharpe Deviation</span>
                  <p className="text-lg font-bold text-slate-300">
                    {selectedDetail.benchmark_comparison?.sharpe_diff ?? 0}
                  </p>
                </div>
              </div>

              <div className="pt-2 text-xs text-slate-400">
                <p className="leading-relaxed">
                  Incubation evaluates whether paper trading performance matches backtest expectations within policy tolerances. Severe Sharpe deterioration or drawdown escalation triggers incubation failure.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: 5-Gate Quality Report View */}
      {activeTab === 'quality_gates' && selectedDetail && (
        <div className="space-y-5">
          <div className="bg-amber-950/30 border border-amber-700/40 rounded-xl p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200/90 leading-relaxed">
              <span className="font-semibold text-amber-300">Quantitative Safety Notice: </span>
              A Quality Gate PASS indicates historical compliance with institutional research hurdles. It MUST NEVER be interpreted as guaranteed profitability. All incubation orders execute exclusively within the Paper matching engine. Capital at risk is strictly $0.00.
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-semibold text-white">5-Gate Quantitative Hurdle Assessment</h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Summary Verdict:</span>
                {renderVerdictBadge(selectedDetail.quality_gate_results?.summary_verdict || 'INSUFFICIENT_DATA')}
              </div>
            </div>

            <div className="space-y-3">
              {(selectedDetail.quality_gate_results?.gate_results || []).map((gate, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{gate.gate_type}</span>
                    </div>
                    <p className="text-xs text-slate-400">{gate.details}</p>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {gate.actual_value !== undefined && gate.actual_value !== null && (
                      <span className="text-xs text-slate-400 font-mono">
                        Actual: <strong className="text-slate-200">{gate.actual_value}</strong>
                        {gate.threshold !== null && ` / Threshold: ${gate.threshold}`}
                      </span>
                    )}
                    {renderVerdictBadge(gate.verdict)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Audit Log View */}
      {activeTab === 'history' && selectedDetail && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white">State Transition Audit Trail</h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Deployment ID: {selectedDetail.id}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/50 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">From</th>
                  <th className="py-2.5 px-3">To</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">Authorization</th>
                  <th className="py-2.5 px-3">Reason</th>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {(selectedDetail.transition_history || []).map((t: any, idx: number) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 font-mono text-slate-400">{t.from_status}</td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-white">{t.to_status}</td>
                    <td className="py-2.5 px-3 text-slate-300">{t.actor_id}</td>
                    <td className="py-2.5 px-3 text-slate-400">{t.authorization}</td>
                    <td className="py-2.5 px-3 text-slate-400">{t.reason}</td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono">
                      {new Date(t.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeploymentPipelinePage;
