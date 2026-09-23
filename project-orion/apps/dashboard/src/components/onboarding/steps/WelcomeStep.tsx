import React from 'react';
import { ArrowRight, BarChart2, Shield, Activity, Info } from 'lucide-react';
import { Button } from '../../common/Button';
import { PaperTradingBadge } from '../../common/Badge';

interface WelcomeStepProps {
  onComplete: () => Promise<void>;
  isSubmitting: boolean;
}

export const WelcomeStep: React.FC<WelcomeStepProps> = ({ onComplete, isSubmitting }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Platform Branding & Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold font-mono tracking-tight text-slate-100">
            WELCOME TO PROJECT ORION
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Institutional Quantitative Paper Trading Platform
          </p>
        </div>
        <div className="flex items-center gap-2">
          <PaperTradingBadge size="md" />
        </div>
      </div>

      {/* Strict Capital Safety Notice */}
      <div
        className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-3"
        role="region"
        aria-label="Simulation Safety Notice"
      >
        <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-400" />
        <div className="space-y-1">
          <div className="font-bold tracking-wider uppercase font-mono text-amber-300">
            SIMULATED PAPER TRADING &bull; $0.00 CAPITAL AT RISK
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">
            Project ORION operates exclusively in a simulated execution environment. All order submissions,
            market liquidity simulations, spreads, and portfolio metrics are mathematical representations.
            No live capital is held, traded, or at risk. Simulated performance does not guarantee future financial results.
          </p>
        </div>
      </div>

      {/* Feature Pillar Highlights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center mb-3">
              <BarChart2 className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">Quantitative Algorithms</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Explore systematic trading strategies including Trend Following and Mean Reversion with historical backtesting.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
              <Activity className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">High-Fidelity Broker</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Simulated fills with realistic slippage, synthetic spreads, order books, and real-time tick streaming.
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-3">
              <Shield className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-200 mb-1">Risk Governance</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Automated circuit breakers, maximum drawdown limits, and daily loss safeguards enforced server-side.
            </p>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-slate-800 flex justify-end">
        <Button
          variant="primary"
          size="md"
          onClick={onComplete}
          isLoading={isSubmitting}
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          Begin Onboarding
        </Button>
      </div>
    </div>
  );
};
