import React, { useState } from 'react';
import { ArrowRight, ShieldAlert } from 'lucide-react';
import { Button } from '../../common/Button';
import { getErrorMessage } from '../../../utils/errors';

interface RiskStepProps {
  onComplete: (metadata: Record<string, any>) => Promise<void>;
  isSubmitting: boolean;
}

export const RiskStep: React.FC<RiskStepProps> = ({ onComplete, isSubmitting }) => {
  const [maxDrawdown, setMaxDrawdown] = useState<number>(5.0);
  const [maxDailyLoss, setMaxDailyLoss] = useState<number>(2.0);
  const [maxPositionSize, setMaxPositionSize] = useState<number>(100000);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const metadata = {
      max_drawdown_pct: maxDrawdown,
      max_daily_loss_pct: maxDailyLoss,
      max_position_size: maxPositionSize,
    };

    try {
      await onComplete(metadata);
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
            RISK LIMITS & CIRCUIT BREAKERS
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Configure institutional downside limits and simulation safeguards
          </p>
        </div>
      </div>

      {error && (
        <div
          className="p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Institutional Safeguards Banner */}
      <div
        className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-start gap-3"
        role="region"
        aria-label="Server-Side Risk Enforcement"
      >
        <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5 text-sky-400" />
        <div className="space-y-1">
          <div className="font-semibold text-slate-200">Server-Side Risk Enforcement</div>
          <p className="text-slate-400 leading-relaxed">
            The ORION RiskEngine enforces these threshold bounds server-side prior to order execution.
            If a simulated position or drawdown exceeds these parameters, orders are rejected and automated
            trading is halted until the circuit breaker is reset.
          </p>
        </div>
      </div>

      {/* Sliders and Controls */}
      <div className="space-y-5">
        {/* Maximum Drawdown */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="max-drawdown-range" className="text-xs font-mono uppercase tracking-wider text-slate-300">
              Maximum Portfolio Drawdown Limit
            </label>
            <span className="text-sm font-mono font-bold text-amber-400">{maxDrawdown.toFixed(1)}%</span>
          </div>
          <input
            id="max-drawdown-range"
            type="range"
            min="1.0"
            max="15.0"
            step="0.5"
            value={maxDrawdown}
            onChange={(e) => setMaxDrawdown(parseFloat(e.target.value))}
            className="w-full accent-sky-500 bg-slate-800 cursor-pointer"
            aria-valuemin={1.0}
            aria-valuemax={15.0}
            aria-valuenow={maxDrawdown}
          />
          <div className="flex justify-between text-[11px] font-mono text-slate-500">
            <span>1.0% (Conservative)</span>
            <span>5.0% (Institutional Standard)</span>
            <span>15.0% (Aggressive)</span>
          </div>
        </div>

        {/* Daily Loss Limit */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="daily-loss-range" className="text-xs font-mono uppercase tracking-wider text-slate-300">
              Maximum Daily Loss Circuit Breaker
            </label>
            <span className="text-sm font-mono font-bold text-rose-400">{maxDailyLoss.toFixed(1)}%</span>
          </div>
          <input
            id="daily-loss-range"
            type="range"
            min="0.5"
            max="5.0"
            step="0.5"
            value={maxDailyLoss}
            onChange={(e) => setMaxDailyLoss(parseFloat(e.target.value))}
            className="w-full accent-sky-500 bg-slate-800 cursor-pointer"
            aria-valuemin={0.5}
            aria-valuemax={5.0}
            aria-valuenow={maxDailyLoss}
          />
          <div className="flex justify-between text-[11px] font-mono text-slate-500">
            <span>0.5% (Strict Daily Cap)</span>
            <span>2.0% (Recommended)</span>
            <span>5.0% (Maximum Cap)</span>
          </div>
        </div>

        {/* Max Position Size */}
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2">
          <div className="flex items-center justify-between">
            <label htmlFor="position-size-select" className="text-xs font-mono uppercase tracking-wider text-slate-300">
              Maximum Single Order Size
            </label>
            <span className="text-sm font-mono font-bold text-sky-400">
              {maxPositionSize.toLocaleString()} units
            </span>
          </div>
          <select
            id="position-size-select"
            value={maxPositionSize}
            onChange={(e) => setMaxPositionSize(parseInt(e.target.value, 10))}
            className="w-full px-3.5 py-2.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-200 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            <option value={25000}>25,000 Units (0.25 Standard Lot)</option>
            <option value={50000}>50,000 Units (0.50 Standard Lot)</option>
            <option value={100000}>100,000 Units (1.00 Standard Lot - Default)</option>
            <option value={200000}>200,000 Units (2.00 Standard Lots)</option>
          </select>
        </div>
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-slate-800 flex justify-end">
        <Button
          type="submit"
          variant="primary"
          size="md"
          isLoading={isSubmitting}
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          Confirm Risk Parameters
        </Button>
      </div>
    </form>
  );
};
