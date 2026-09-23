import React, { useState } from 'react';
import { ArrowRight, CheckCircle2, Shield, Wallet, Cpu, AlertCircle } from 'lucide-react';
import { Button } from '../../common/Button';
import { PaperTradingBadge } from '../../common/Badge';
import { getErrorMessage } from '../../../utils/errors';

interface PaperReadinessStepProps {
  onComplete: () => Promise<void>;
  isSubmitting: boolean;
  paperAccountReady: boolean;
}

export const PaperReadinessStep: React.FC<PaperReadinessStepProps> = ({
  onComplete,
  isSubmitting,
  paperAccountReady = true,
}) => {
  const [acknowledged, setAcknowledged] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!paperAccountReady) {
      setError('Paper trading account initialization is not ready. Please refresh.');
      return;
    }
    if (!acknowledged) {
      setError('Please acknowledge the paper trading simulation terms before proceeding.');
      return;
    }
    setError(null);
    try {
      await onComplete();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold font-mono tracking-tight text-slate-100">
            PAPER TRADING ENVIRONMENT READY
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Institutional simulation environment configured and provisioned
          </p>
        </div>
        <div>
          <PaperTradingBadge size="md" />
        </div>
      </div>

      {error && (
        <div
          className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2.5"
          role="alert"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Account Specifications Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Paper Balance */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0">
            <Wallet className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Simulated Paper Balance
            </div>
            <div className="text-lg font-bold font-mono text-emerald-400">$100,000.00 USD</div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">Virtual Equity &bull; 100:1 Leverage</div>
          </div>
        </div>

        {/* Capital Safety */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center flex-shrink-0">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Capital at Risk
            </div>
            <div className="text-lg font-bold font-mono text-amber-300">$0.00</div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">Zero Live Broker Execution</div>
          </div>
        </div>

        {/* Execution Adapter */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center flex-shrink-0">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Broker Adapter
            </div>
            <div className="text-sm font-semibold font-mono text-slate-200">Local Paper Engine</div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">Synthetic Spreads & Slippage</div>
          </div>
        </div>

        {/* Worker Status */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Autonomous Worker
            </div>
            <div className="text-sm font-semibold font-mono text-slate-300">Disabled (Safety Policy)</div>
            <div className="text-[11px] text-slate-500 font-mono mt-0.5">ORION_WORKER_ENABLED=false</div>
          </div>
        </div>
      </div>

      {/* Final Safety Acknowledgement */}
      <div className="p-4 rounded-xl border border-slate-700/80 bg-slate-900/90">
        <label className="flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            className="w-4 h-4 mt-0.5 rounded border-slate-700 text-sky-500 focus:ring-sky-500 bg-slate-800"
          />
          <div className="text-xs text-slate-300 leading-relaxed">
            <span className="font-semibold text-slate-100">
              Institutional Simulation Acknowledgment:
            </span>{' '}
            I confirm that I understand Project ORION is operating strictly in paper trading mode with{' '}
            <strong className="text-amber-300 font-mono">$0.00 capital at risk</strong>. No live exchange orders will
            be routed, and performance results represent simulation models only.
          </div>
        </label>
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-slate-800 flex justify-end">
        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isSubmitting}
          disabled={!acknowledged}
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          Launch Trading Terminal
        </Button>
      </div>
    </form>
  );
};
