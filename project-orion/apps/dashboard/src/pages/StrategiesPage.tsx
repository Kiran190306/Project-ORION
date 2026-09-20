import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Sliders, AlertCircle, Settings } from 'lucide-react';
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
  const [activeConfig, setActiveConfig] = useState<AccountStrategyConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit config modal
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedStrategyId, setSelectedStrategyId] = useState('');
  const [selectedTimeframe, setSelectedTimeframe] = useState('M15');
  const [symbolsInput, setSymbolsInput] = useState('EUR/USD,GBP/USD,USD/JPY');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toast = useToast();

  const fetchStrategies = useCallback(async () => {
    setIsLoading(true);
    try {
      const [cat, cfg] = await Promise.all([
        strategiesApi.list(),
        strategiesApi.getAccountConfig(),
      ]);
      setStrategies(cat.strategies);
      setActiveConfig(cfg);
      setSelectedStrategyId(cfg.strategy_id);
      setSelectedTimeframe(cfg.timeframe);
      setSymbolsInput(cfg.symbols.join(', '));
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

  const handleUpdateConfig = async (e: React.FormEvent) => {
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
      setActiveConfig(updated);
      toast.success(`Account strategy updated to ${updated.strategy_id} (${updated.timeframe})`);
      setIsEditOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading && !activeConfig) {
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
            Catalogue of quantitative trading strategies &bull; Account configuration &bull; Parameter schemas
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchStrategies()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 text-xs flex items-center gap-3 font-mono">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Currently Active Strategy Banner */}
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
              onClick={() => setIsEditOpen(true)}
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
                {activeConfig.symbols.join(', ') || 'None'}
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

      {/* Available Strategies Catalogue */}
      <div className="space-y-3">
        <h2 className="text-sm font-mono uppercase tracking-wider text-slate-400">
          Strategy Catalogue ({strategies.length})
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategies.map((strat) => {
            const isCurrent = activeConfig?.strategy_id === strat.id;

            return (
              <Card
                key={strat.id}
                className={isCurrent ? 'border-sky-500/60' : ''}
                title={
                  <div className="flex items-center gap-2">
                    <span>{strat.name}</span>
                    {isCurrent && <Badge variant="success">ACTIVE</Badge>}
                  </div>
                }
              >
                <div className="space-y-3 text-xs font-mono">
                  <p className="text-slate-400 text-xs leading-relaxed font-sans">{strat.description}</p>

                  <div>
                    <span className="text-slate-500">Supported Timeframes:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {strat.timeframes.map((tf) => (
                        <span key={tf} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {tf}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <span className="text-slate-500">Recommended Pairs:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {strat.symbols.map((sym) => (
                        <span key={sym} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                          {sym}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex justify-end">
                    <Button
                      variant={isCurrent ? 'outline' : 'secondary'}
                      size="sm"
                      onClick={() => {
                        setSelectedStrategyId(strat.id);
                        setIsEditOpen(true);
                      }}
                    >
                      {isCurrent ? 'Edit Parameters' : 'Select Strategy'}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Edit Strategy Configuration Modal */}
      <Modal
        isOpen={isEditOpen}
        onClose={() => setIsEditOpen(false)}
        title="Configure Account Strategy"
        maxWidth="md"
      >
        <form onSubmit={handleUpdateConfig} className="space-y-4 font-mono text-xs">
          <div>
            <label className="block uppercase text-slate-400 mb-1">Select Strategy</label>
            <select
              value={selectedStrategyId}
              onChange={(e) => setSelectedStrategyId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            >
              {strategies.map((s) => (
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
    </div>
  );
};
