import React, { useState, useEffect } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import { Button } from '../../common/Button';
import { Badge } from '../../common/Badge';
import { strategiesApi } from '../../../api/endpoints';
import type { StrategyInfo } from '../../../api/types';
import { getErrorMessage } from '../../../utils/errors';

interface StrategyStepProps {
  onComplete: (metadata: Record<string, any>) => Promise<void>;
  isSubmitting: boolean;
}

export const StrategyStep: React.FC<StrategyStepProps> = ({ onComplete, isSubmitting }) => {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('TrendFollowing');
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>('M15');
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['EUR/USD', 'GBP/USD']);
  const [error, setError] = useState<string | null>(null);

  // Default fallback strategies matching project-orion catalogue
  const fallbackStrategies: StrategyInfo[] = [
    {
      id: 'TrendFollowing',
      name: 'Trend Following',
      type: 'MOMENTUM',
      description: 'Dual exponential moving average crossover with ATR dynamic volatility filter.',
      timeframes: ['M15', 'H1', 'D1'],
      symbols: ['EUR/USD', 'GBP/USD', 'USD/JPY'],
      is_active: true,
    },
    {
      id: 'MeanReversion',
      name: 'Mean Reversion',
      type: 'STATISTICAL_ARBITRAGE',
      description: 'Statistical mean reversion utilizing Bollinger Bands and RSI overbought/oversold boundaries.',
      timeframes: ['M15', 'H1'],
      symbols: ['EUR/USD', 'GBP/USD'],
      is_active: true,
    },
    {
      id: 'Breakout',
      name: 'Breakout & Volatility Expansion',
      type: 'VOLATILITY',
      description: 'Identifies consolidation compressions and enters on directional volume and range expansion.',
      timeframes: ['M15', 'H1', 'D1'],
      symbols: ['EUR/USD', 'USD/JPY'],
      is_active: true,
    },
  ];

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const res = await strategiesApi.list();
        if (isMounted) {
          if (res.strategies && res.strategies.length > 0) {
            setStrategies(res.strategies);
            setSelectedStrategyId(res.strategies[0].id);
          } else {
            setStrategies(fallbackStrategies);
          }
        }
      } catch {
        // Fallback to catalogue defaults gracefully
        if (isMounted) {
          setStrategies(fallbackStrategies);
        }
      }
    };
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleToggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) => {
      if (prev.includes(symbol)) {
        if (prev.length === 1) return prev; // Keep at least one
        return prev.filter((s) => s !== symbol);
      }
      return [...prev, symbol];
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const metadata = {
      strategy_id: selectedStrategyId,
      timeframe: selectedTimeframe,
      symbols: selectedSymbols,
    };

    try {
      // Also update account configuration in parallel if endpoint available
      try {
        await strategiesApi.updateAccountConfig({
          strategy_id: selectedStrategyId,
          timeframe: selectedTimeframe,
          symbols: selectedSymbols,
          parameters: {},
          is_active: true,
        });
      } catch {
        // Non-blocking for onboarding step completion
      }

      await onComplete(metadata);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const availableSymbols = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CHF'];
  const availableTimeframes = [
    { id: 'M15', label: '15 Minutes (M15)' },
    { id: 'H1', label: '1 Hour (H1)' },
    { id: 'D1', label: '1 Day (D1)' },
  ];

  return (
    <form onSubmit={handleSubmit} className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold font-mono tracking-tight text-slate-100">
            ALGORITHMIC STRATEGY SETUP
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Configure systematic strategy execution for your paper account
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

      {/* Strategy Selection Grid */}
      <div>
        <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
          Select Core Strategy Model
        </label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {(strategies.length > 0 ? strategies : fallbackStrategies).map((strat) => {
            const isSelected = selectedStrategyId === strat.id;
            return (
              <div
                key={strat.id}
                onClick={() => setSelectedStrategyId(strat.id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all duration-150 flex flex-col justify-between ${
                  isSelected
                    ? 'border-sky-500 bg-sky-950/30 ring-1 ring-sky-500/50'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === ' ' || e.key === 'Enter') {
                    setSelectedStrategyId(strat.id);
                  }
                }}
                aria-pressed={isSelected}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm text-slate-200">{strat.name}</span>
                    {isSelected && (
                      <div className="w-5 h-5 rounded-full bg-sky-500 text-slate-950 flex items-center justify-center">
                        <Check className="w-3 h-3 stroke-[3]" />
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                    {strat.description}
                  </p>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
                  <span>{strat.type}</span>
                  <Badge variant={isSelected ? 'info' : 'default'} className="text-[10px]">
                    {isSelected ? 'Active' : 'Select'}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Timeframe & Instrument Whitelist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
        {/* Timeframe */}
        <div>
          <label htmlFor="timeframe-select" className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
            Execution Timeframe
          </label>
          <select
            id="timeframe-select"
            value={selectedTimeframe}
            onChange={(e) => setSelectedTimeframe(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-200 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            {availableTimeframes.map((tf) => (
              <option key={tf.id} value={tf.id}>
                {tf.label}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-slate-500 mt-1.5 font-mono">
            Bar sampling frequency for algorithmic indicator signals.
          </p>
        </div>

        {/* Instruments */}
        <div>
          <label className="block text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
            Active Currency Pairs
          </label>
          <div className="flex flex-wrap gap-2">
            {availableSymbols.map((sym) => {
              const active = selectedSymbols.includes(sym);
              return (
                <button
                  type="button"
                  key={sym}
                  onClick={() => handleToggleSymbol(sym)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono border transition-colors ${
                    active
                      ? 'bg-sky-500/10 border-sky-500/40 text-sky-300 font-semibold'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                  aria-pressed={active}
                >
                  {sym}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-500 mt-1.5 font-mono">
            Selected pairs receive simulated tick streaming and order executions.
          </p>
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
          Confirm Strategy & Continue
        </Button>
      </div>
    </form>
  );
};
