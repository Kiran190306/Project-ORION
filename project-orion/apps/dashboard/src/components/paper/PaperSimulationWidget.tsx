import React, { useState, useEffect, useCallback } from 'react';
import { Sliders, RotateCcw, Shield, CheckCircle2 } from 'lucide-react';
import { Card } from '../common/Card';
import { Badge, PaperTradingBadge } from '../common/Badge';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { useToast } from '../common/Toast';
import { paperApi } from '../../api/endpoints';
import type { PaperConfigResponse, UpdatePaperConfigRequest } from '../../api/types';
import { getErrorMessage } from '../../utils/errors';

interface PaperSimulationWidgetProps {
  onResetSuccess?: () => void;
}

export const PaperSimulationWidget: React.FC<PaperSimulationWidgetProps> = ({ onResetSuccess }) => {
  const toast = useToast();
  const [config, setConfig] = useState<PaperConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Reset modal state
  const [isResetOpen, setIsResetOpen] = useState<boolean>(false);
  const [resetBalance, setResetBalance] = useState<string>('100000.00');
  const [isResetting, setIsResetting] = useState<boolean>(false);

  // Config modal state
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [isUpdatingConfig, setIsUpdatingConfig] = useState<boolean>(false);
  const [configForm, setConfigForm] = useState<UpdatePaperConfigRequest>({
    default_spread_pips: 1.0,
    slippage_bps: 0.5,
    latency_ms: 20.0,
    partial_fill_probability: 0.0,
    deterministic: false,
  });

  const fetchConfig = useCallback(async () => {
    try {
      const res = await paperApi.getConfig();
      setConfig(res);
      setConfigForm({
        default_spread_pips: res.default_spread_pips,
        slippage_bps: res.slippage_bps,
        latency_ms: res.latency_ms,
        partial_fill_probability: res.partial_fill_probability,
        deterministic: res.deterministic,
      });
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    const balanceNum = parseFloat(resetBalance);
    if (isNaN(balanceNum) || balanceNum <= 0) {
      toast.error('Reset initial balance must be a positive number.');
      return;
    }

    setIsResetting(true);
    try {
      const res = await paperApi.reset({ initial_balance: balanceNum });
      toast.success(
        `Account reset successful! New balance: $${Number(res.new_balance).toLocaleString()}. Cancelled ${res.cancelled_orders_count} orders, closed ${res.closed_positions_count} positions.`
      );
      setIsResetOpen(false);
      if (onResetSuccess) {
        onResetSuccess();
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsResetting(false);
    }
  };

  const handleUpdateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingConfig(true);
    try {
      const updated = await paperApi.updateConfig(configForm);
      setConfig(updated);
      toast.success('Paper simulation parameters successfully updated.');
      setIsConfigOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsUpdatingConfig(false);
    }
  };

  if (isLoading && !config) {
    return (
      <Card title="Institutional Paper Execution Engine" badge={<PaperTradingBadge size="sm" />}>
        <div className="h-20 bg-slate-950/60 rounded-lg animate-pulse" />
      </Card>
    );
  }

  if (error && !config) {
    return (
      <Card title="Institutional Paper Execution Engine" badge={<PaperTradingBadge size="sm" />}>
        <div className="text-xs text-rose-400 font-mono p-2">Failed to load paper simulation config: {error}</div>
      </Card>
    );
  }

  return (
    <>
      <Card
        title="Institutional Paper Execution Engine"
        badge={<PaperTradingBadge size="sm" />}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConfigOpen(true)}
              leftIcon={<Sliders className="w-3.5 h-3.5 text-sky-400" />}
            >
              Config
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsResetOpen(true)}
              leftIcon={<RotateCcw className="w-3.5 h-3.5 text-amber-400" />}
            >
              Reset Account
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Microstructure Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 font-mono text-xs">
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Simulation Mode</span>
              <span className="text-slate-200 font-bold mt-0.5 block">
                {config?.deterministic ? (
                  <span className="text-purple-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> DETERMINISTIC
                  </span>
                ) : (
                  <span className="text-emerald-400">DYNAMIC (GAUSSIAN)</span>
                )}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Default Spread</span>
              <span className="text-slate-200 font-bold mt-0.5 block">
                {config ? `${config.default_spread_pips} pips` : '—'}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Adverse Slippage</span>
              <span className="text-slate-200 font-bold mt-0.5 block">
                {config ? `${config.slippage_bps} bps` : '—'}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Simulated Latency</span>
              <span className="text-slate-200 font-bold mt-0.5 block">
                {config ? `${config.latency_ms} ms` : '—'}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-500 block text-[10px] uppercase">Partial Fill Rate</span>
              <span className="text-slate-200 font-bold mt-0.5 block">
                {config ? `${(Number(config.partial_fill_probability) * 100).toFixed(0)}%` : '—'}
              </span>
            </div>
          </div>

          {/* Safety & Invariant Banner */}
          <div className="p-3 rounded-lg bg-sky-950/30 border border-sky-800/50 flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-sky-300">
              <Shield className="w-4 h-4 text-sky-400 flex-shrink-0" />
              <span>
                <strong>Zero Capital Risk ($0.00)</strong> &bull; Side-aware execution (BUY @ Ask + Slip, SELL @ Bid - Slip) &bull; Multi-tenant position netting active.
              </span>
            </div>
            <Badge variant="success">
              ENGINE READY
            </Badge>
          </div>
        </div>
      </Card>

      {/* Reset Account Modal */}
      <Modal
        isOpen={isResetOpen}
        onClose={() => setIsResetOpen(false)}
        title={
          <div className="flex items-center gap-2 text-slate-100 font-mono">
            <RotateCcw className="w-4 h-4 text-amber-400" />
            <span>Reset Paper Trading Account</span>
          </div>
        }
        size="md"
      >
        <form onSubmit={handleReset} className="space-y-4 font-mono text-xs">
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs">
            <p className="font-bold mb-1">Warning: Irreversible Paper Account Reset</p>
            <p className="text-[11px] text-amber-300/80">
              This action will immediately cancel all pending limit and stop orders, close all open positions at current market quotes, and reset your cash balance to the initial capital.
            </p>
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Initial Starting Capital (USD)</label>
            <input
              type="number"
              step="1000"
              min="1000"
              max="10000000"
              required
              value={resetBalance}
              onChange={(e) => setResetBalance(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-amber-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <Button variant="ghost" size="sm" type="button" onClick={() => setIsResetOpen(false)} disabled={isResetting}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              type="submit"
              isLoading={isResetting}
              leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
            >
              Confirm Reset Account
            </Button>
          </div>
        </form>
      </Modal>

      {/* Configure Simulation Modal */}
      <Modal
        isOpen={isConfigOpen}
        onClose={() => setIsConfigOpen(false)}
        title={
          <div className="flex items-center gap-2 text-slate-100 font-mono">
            <Sliders className="w-4 h-4 text-sky-400" />
            <span>Configure Paper Microstructure</span>
          </div>
        }
        size="md"
      >
        <form onSubmit={handleUpdateConfig} className="space-y-4 font-mono text-xs">
          <div>
            <label className="block uppercase text-slate-400 mb-1">Default Spread (Pips)</label>
            <input
              type="number"
              step="0.1"
              min="0.0"
              max="20.0"
              required
              value={configForm.default_spread_pips ?? 1.0}
              onChange={(e) =>
                setConfigForm({ ...configForm, default_spread_pips: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Adverse Slippage (BPS)</label>
            <input
              type="number"
              step="0.1"
              min="0.0"
              max="50.0"
              required
              value={configForm.slippage_bps ?? 0.5}
              onChange={(e) =>
                setConfigForm({ ...configForm, slippage_bps: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Simulated Latency (ms)</label>
            <input
              type="number"
              step="5"
              min="0"
              max="2000"
              required
              value={configForm.latency_ms ?? 20}
              onChange={(e) =>
                setConfigForm({ ...configForm, latency_ms: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block uppercase text-slate-400 mb-1">Partial Fill Probability (0.0 - 1.0)</label>
            <input
              type="number"
              step="0.05"
              min="0.0"
              max="1.0"
              required
              value={configForm.partial_fill_probability ?? 0.0}
              onChange={(e) =>
                setConfigForm({ ...configForm, partial_fill_probability: parseFloat(e.target.value) })
              }
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="deterministic_check"
              checked={configForm.deterministic ?? false}
              onChange={(e) =>
                setConfigForm({ ...configForm, deterministic: e.target.checked })
              }
              className="rounded bg-slate-950 border-slate-800 text-sky-500 focus:ring-0 cursor-pointer"
            />
            <label htmlFor="deterministic_check" className="text-slate-300 select-none cursor-pointer">
              Deterministic Mode (zero random variance for tests)
            </label>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <Button variant="ghost" size="sm" type="button" onClick={() => setIsConfigOpen(false)} disabled={isUpdatingConfig}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              type="submit"
              isLoading={isUpdatingConfig}
              leftIcon={<Sliders className="w-3.5 h-3.5" />}
            >
              Save Configuration
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
};
