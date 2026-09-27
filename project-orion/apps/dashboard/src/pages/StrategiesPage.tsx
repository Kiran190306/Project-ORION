import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  Sliders,
  AlertCircle,
  Settings,
  Plus,
  Trash2,
  ExternalLink,
  Layers,
  Activity,
} from 'lucide-react';
import { strategiesApi } from '../api/endpoints';
import type {
  StrategyInfo,
  AccountStrategyConfigResponse,
  UpdateAccountStrategyRequest,
} from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { useToast } from '../components/common/Toast';
import { formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const StrategiesPage: React.FC = () => {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [activeConfigs, setActiveConfigs] = useState<AccountStrategyConfigResponse[]>([]);
  const [activeConfig, setActiveConfig] = useState<AccountStrategyConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit/Add config modal
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [selectedTimeframe, setSelectedTimeframe] = useState('M15');
  const [symbolsInput, setSymbolsInput] = useState('EUR/USD,GBP/USD,USD/JPY');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Deactivate confirmation modal
  const [deactivatingId, setDeactivatingId] = useState<string | null>(null);

  const toast = useToast();

  const fetchStrategies = useCallback(async () => {
    setIsLoading(true);
    try {
      const [cat, singleCfg, configs] = await Promise.all([
        strategiesApi.list().catch(() => ({ strategies: [], total: 0 })),
        strategiesApi.getAccountConfig().catch(() => null),
        strategiesApi.listAccountConfigs().catch(() => []),
      ]);
      setStrategies(cat.strategies || []);

      let mergedConfigs: AccountStrategyConfigResponse[] = [];
      if (Array.isArray(configs)) {
        mergedConfigs = configs;
      } else if (configs && typeof configs === 'object' && 'strategy_id' in (configs as unknown as Record<string, unknown>)) {
        mergedConfigs = [configs as AccountStrategyConfigResponse];
      } else if (singleCfg && typeof singleCfg === 'object' && 'strategy_id' in (singleCfg as unknown as Record<string, unknown>)) {
        mergedConfigs = [singleCfg as AccountStrategyConfigResponse];
      }
      setActiveConfigs(mergedConfigs);

      const chosen =
        singleCfg && typeof singleCfg === 'object' && 'strategy_id' in (singleCfg as unknown as Record<string, unknown>)
          ? (singleCfg as AccountStrategyConfigResponse)
          : mergedConfigs[0] || null;
      setActiveConfig(chosen);

      if (chosen) {
        setSelectedStrategyId(chosen.strategy_id);
        setSelectedTimeframe(chosen.timeframe);
        setSymbolsInput(chosen.symbols ? chosen.symbols.join(', ') : 'EUR/USD');
      }
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const handleOpenDeployModal = (strategyId?: string) => {
    const targetId = strategyId || selectedStrategyId || strategies[0]?.id || 'trend_following';
    const existing = (activeConfigs || []).find((c) => c.strategy_id === targetId);

    if (existing) {
      setSelectedStrategyId(existing.strategy_id);
      setSelectedTimeframe(existing.timeframe);
      setSymbolsInput(existing.symbols.join(', '));
    } else {
      setSelectedStrategyId(targetId);
      setSelectedTimeframe('M15');
      setSymbolsInput('EUR/USD,GBP/USD,USD/JPY');
    }
    setIsEditOpen(true);
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStrategyId) {
      toast.error('Please select a valid strategy.');
      return;
    }

    const parsedSymbols = symbolsInput
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);

    if (parsedSymbols.length === 0) {
      toast.error('At least one symbol pair must be specified.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: UpdateAccountStrategyRequest = {
        strategy_id: selectedStrategyId,
        timeframe: selectedTimeframe,
        symbols: parsedSymbols,
        parameters: activeConfig?.parameters || {},
        is_active: true,
      };

      const updated = await strategiesApi.updateAccountConfig(payload);
      try {
        await strategiesApi.createAccountConfig(payload);
      } catch {
        // Fallback for non-multi endpoints
      }

      toast.success(
        `Account strategy updated to ${updated.strategy_id} (${updated.timeframe})`
      );
      setIsEditOpen(false);
      fetchStrategies();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeactivate = async () => {
    if (!deactivatingId) return;
    setIsSubmitting(true);
    try {
      await strategiesApi.deleteAccountConfig(deactivatingId);
      toast.success(`Strategy ${deactivatingId} deactivated.`);
      setDeactivatingId(null);
      fetchStrategies();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDeploymentBadge = (status?: string | null, isActive: boolean = true) => {
    if (!isActive) return <Badge variant="default">DISABLED</Badge>;
    switch (status) {
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
  };

  if (isLoading && !activeConfig && activeConfigs.length === 0) {
    return (
      <div className="space-y-6">
        <div className="h-6 bg-slate-800 rounded w-48 animate-pulse" />
        <div className="h-28 bg-slate-900 border border-slate-800 rounded-xl animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-44 bg-slate-900 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              STRATEGY REGISTRY & CONTROL
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Institutional strategy catalogue &bull; Multi-strategy paper execution &bull; Lifecycle gate visibility
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/deployments';
              }
            }}
            leftIcon={<ExternalLink className="w-3.5 h-3.5" />}
          >
            Deployment Pipeline
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchStrategies()}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => handleOpenDeployModal()}
            leftIcon={<Plus className="w-3.5 h-3.5" />}
          >
            Deploy Strategy
          </Button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-3 font-mono">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Account Strategy Primary Banner */}
      {activeConfig && (
        <Card
          className="border-sky-500/40 bg-sky-950/20"
          title={
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-sky-400" />
              <span>Active Account Strategy</span>
            </div>
          }
          action={
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleOpenDeployModal(activeConfig.strategy_id)}
              leftIcon={<Settings className="w-3.5 h-3.5" />}
            >
              Modify Configuration
            </Button>
          }
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
            <div>
              <span className="text-slate-400">Strategy Name:</span>
              <div className="text-sm font-bold text-slate-100 mt-0.5">{activeConfig.strategy_id}</div>
            </div>
            <div>
              <span className="text-slate-400">Execution Timeframe:</span>
              <div className="text-sm font-bold text-slate-100 mt-0.5">{activeConfig.timeframe}</div>
            </div>
            <div>
              <span className="text-slate-400">Active Currency Pairs:</span>
              <div className="text-sm font-semibold text-slate-200 mt-0.5">
                {activeConfig.symbols ? activeConfig.symbols.join(', ') : 'None'}
              </div>
            </div>
            <div>
              <span className="text-slate-400">Last Configured:</span>
              <div className="text-xs text-slate-300 mt-0.5">
                {formatDateTime(activeConfig.updated_at)}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Active Multi-Strategy Deployments Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-mono uppercase tracking-wider text-slate-300 font-bold">
              Active Strategy Deployments ({activeConfigs.length})
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Multi-strategy execution enabled &bull; Independent risk & attribution
          </span>
        </div>

        {activeConfigs.length === 0 ? (
          <Card className="p-6 text-center space-y-3">
            <Activity className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-mono text-slate-400">
              No strategies are currently deployed to this paper account.
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleOpenDeployModal()}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Deploy First Strategy
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.isArray(activeConfigs) && activeConfigs.map((cfg) => (
              <Card
                key={cfg.strategy_id}
                className="border-sky-500/40 bg-sky-950/10 space-y-3"
                title={
                  <div className="flex items-center justify-between w-full pr-2">
                    <div className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-sky-400" />
                      <span className="font-bold text-slate-100">{cfg.name || cfg.strategy_id}</span>
                    </div>
                    {getDeploymentBadge(cfg.deployment_status, cfg.is_active)}
                  </div>
                }
              >
                <div className="space-y-2.5 font-mono text-xs">
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <span className="text-slate-500 block">Strategy ID:</span>
                      <span className="text-slate-300 font-semibold">{cfg.strategy_id}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Timeframe:</span>
                      <span className="text-slate-200 font-bold">{cfg.timeframe}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500 block text-[11px] mb-1">Target Instruments:</span>
                    <div className="flex flex-wrap gap-1">
                      {(cfg.symbols || []).map((sym) => (
                        <span
                          key={sym}
                          className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-sky-300 text-[10px]"
                        >
                          {sym}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Configured: {formatDateTime(cfg.updated_at)}</span>
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleOpenDeployModal(cfg.strategy_id)}
                        className="h-7 px-2 text-xs"
                      >
                        <Settings className="w-3 h-3 mr-1" /> Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => setDeactivatingId(cfg.strategy_id)}
                        className="h-7 px-2 text-xs"
                        title="Deactivate strategy"
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Available Strategies Catalogue */}
      <div className="space-y-3 pt-4 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-mono uppercase tracking-wider text-slate-400">
            Strategy Catalogue ({strategies.length})
          </h2>
          <span className="text-[11px] font-mono text-slate-500">
            Select a quantitative model to configure parameters and deploy
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(strategies || []).map((strat) => {
            const isDeployed = (activeConfigs || []).some(
              (c) => c.strategy_id === strat.id && c.is_active
            );

            return (
              <Card
                key={strat.id}
                className={isDeployed ? 'border-sky-500/50' : ''}
                title={
                  <div className="flex items-center justify-between w-full">
                    <span>{strat.name}</span>
                    {isDeployed && <Badge variant="success">DEPLOYED</Badge>}
                  </div>
                }
              >
                <div className="space-y-3 text-xs font-mono">
                  <p className="text-slate-400 text-xs leading-relaxed font-sans">{strat.description}</p>

                  <div>
                    <span className="text-slate-500">Supported Timeframes:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(strat.timeframes || []).map((tf) => (
                        <span key={tf} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {tf}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500">Recommended Pairs:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {(strat.symbols || []).map((sym) => (
                        <span key={sym} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {sym}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex justify-end">
                    <Button
                      variant={isDeployed ? 'outline' : 'primary'}
                      size="sm"
                      onClick={() => handleOpenDeployModal(strat.id)}
                    >
                      {isDeployed ? 'Edit Parameters' : 'Select Strategy'}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Deploy / Configure Strategy Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Configure Account Strategy"
        maxWidth="md"
      >
        <form onSubmit={handleSaveConfig} className="space-y-4 font-mono text-xs">
          <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-800 text-sky-200 text-[11px] leading-relaxed">
            <strong>MULTI-STRATEGY EXECUTION:</strong> Deploying this strategy activates paper execution for the specified currency pairs. It operates concurrently with any existing active strategies.
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Select Strategy</label>
            <select
              value={selectedStrategyId}
              onChange={(e) => setSelectedStrategyId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            >
              {(strategies || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.id})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Execution Timeframe</label>
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            >
              <option value="M1">M1 (1 Minute)</option>
              <option value="M5">M5 (5 Minutes)</option>
              <option value="M15">M15 (15 Minutes)</option>
              <option value="H1">H1 (1 Hour)</option>
              <option value="H4">H4 (4 Hours)</option>
              <option value="D1">D1 (Daily)</option>
            </select>
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">
              Target Currency Pairs (Comma Separated)
            </label>
            <input
              type="text"
              required
              value={symbolsInput}
              onChange={(e) => setSymbolsInput(e.target.value)}
              placeholder="EUR/USD, GBP/USD, USD/JPY"
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            />
            <p className="text-[10px] text-slate-500 mt-1">
              Example: EUR/USD, GBP/USD, USD/JPY, AUD/USD
            </p>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsEditOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
            >
              Save Strategy Settings
            </Button>
          </div>
        </form>
      </Modal>

      {/* Deactivate Strategy Modal */}
      <Modal
        isOpen={Boolean(deactivatingId)}
        onClose={() => setDeactivatingId(null)}
        title="Confirm Strategy Deactivation"
        maxWidth="sm"
      >
        <div className="space-y-4 font-mono text-xs">
          <p className="text-slate-300">
            Are you sure you want to deactivate strategy <strong className="text-white">{deactivatingId}</strong>?
          </p>
          <p className="text-slate-400 text-[11px]">
            New simulated order generation for this strategy will halt. Existing open positions attributable to this strategy will remain open until closed manually or by risk limits.
          </p>
          <div className="pt-2 flex items-center justify-end gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeactivatingId(null)}
            >
              Keep Active
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleDeactivate}
            >
              Deactivate Strategy
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
