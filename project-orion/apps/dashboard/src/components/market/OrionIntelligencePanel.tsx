import React from 'react';
import {
  Cpu,
  Zap,
  Target,
  Activity,
  Clock,
} from 'lucide-react';

interface OrionIntelligencePanelProps {
  selectedSymbol?: string;
  className?: string;
}

export const OrionIntelligencePanel: React.FC<OrionIntelligencePanelProps> = ({
  selectedSymbol = 'EUR/USD',
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl border border-[#1E293B] bg-[#141E33] flex flex-col overflow-hidden ${className}`}
      style={{ backgroundColor: '#141E33', borderColor: '#1E293B' }}
    >
      {/* Header */}
      <div className="p-3 border-b border-[#1E293B] bg-[#0F172A] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-400">
            <Cpu className="w-3.5 h-3.5" />
          </div>
          <h3 className="text-xs font-bold font-mono text-slate-100 tracking-wider uppercase">
            ORION Intelligence
          </h3>
        </div>
        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded font-bold uppercase">
          LIVE MODEL
        </span>
      </div>

      <div className="p-3.5 space-y-3.5 overflow-y-auto max-h-[580px] font-mono text-xs">
        {/* Market Regime & Signal Cards */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Activity className="w-3 h-3 text-sky-400" />
              <span>Market Regime</span>
            </div>
            <div className="font-bold text-slate-100 text-xs">BULLISH TREND</div>
            <div className="text-[10px] text-sky-400 mt-0.5">High Volatility (92.4%)</div>
          </div>

          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" />
              <span>Strategy Signal</span>
            </div>
            <div className="font-bold text-emerald-400 text-xs flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              BUY {selectedSymbol}
            </div>
            <div className="text-[10px] text-emerald-400/90 mt-0.5 font-bold">87% Conviction</div>
          </div>
        </div>

        {/* Signal Confidence Meter */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-1.5">
          <div className="flex justify-between items-center text-[10px]">
            <span className="text-slate-400 uppercase font-semibold">Signal Confidence</span>
            <span className="text-sky-400 font-bold">87.4% High Conviction</span>
          </div>
          <div className="w-full h-1.5 bg-[#141E33] rounded-full overflow-hidden border border-[#1E293B]">
            <div className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 rounded-full w-[87.4%]" />
          </div>
        </div>

        {/* Risk State & Sizing */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Risk State</span>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded inline-block">
              NOMINAL (Risk-On)
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Position Sizing</span>
            <span className="text-xs font-bold text-slate-200">10,000 units</span>
            <div className="text-[10px] text-slate-500 mt-0.5">0.10 Lots (Fractional Kelly)</div>
          </div>
        </div>

        {/* Suggested Stop Loss & Take Profit Plan */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-2">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400 uppercase font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-sky-400" />
              Dynamic Exit Plan
            </span>
            <span className="text-slate-400 font-bold">R:R 1 : 2.0</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-1.5 rounded bg-rose-950/30 border border-rose-900/40">
              <div className="text-[9px] text-rose-400 uppercase">Stop Loss</div>
              <div className="font-bold text-rose-300">1.08200</div>
              <div className="text-[9px] text-slate-500">-30.2 pips</div>
            </div>
            <div className="p-1.5 rounded bg-emerald-950/30 border border-emerald-900/40">
              <div className="text-[9px] text-emerald-400 uppercase">Take Profit</div>
              <div className="font-bold text-emerald-300">1.09100</div>
              <div className="text-[9px] text-slate-500">+60.4 pips</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-[#1E293B]">
            <span>Expected Capital at Risk:</span>
            <span className="text-rose-400 font-bold">$150.00 (1.50% Paper Eq)</span>
          </div>
        </div>

        {/* Quantitative Robustness & Walk-Forward Validation */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-2">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400 uppercase font-semibold">Backtest & Walk-Forward</span>
            <span className="text-emerald-400 font-bold bg-emerald-950/40 px-1 rounded border border-emerald-800/40">
              ROBUST
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Sharpe</div>
              <div className="font-bold text-sky-400">1.92</div>
            </div>
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Win Rate</div>
              <div className="font-bold text-emerald-400">64.8%</div>
            </div>
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Profit Fac</div>
              <div className="font-bold text-slate-200">2.14</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-[#1E293B]">
            <span>WFA Out-of-Sample Efficiency:</span>
            <span className="text-sky-300 font-bold">88.4% Passed</span>
          </div>
        </div>

        {/* Recent Strategy Events Stream */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
            <span className="uppercase font-semibold flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              Recent Strategy Events
            </span>
            <span className="text-[9px] text-sky-400">Telemetry Feed</span>
          </div>
          <div className="space-y-1.5">
            <div className="text-[10px] flex items-center justify-between text-slate-300 p-1 rounded bg-[#141E33]/60 border border-[#1E293B]/60">
              <span className="text-emerald-400 font-semibold">▲ EMA_20_CROSS_UP</span>
              <span className="text-slate-500 text-[9px]">14:32:10 UTC</span>
            </div>
            <div className="text-[10px] flex items-center justify-between text-slate-300 p-1 rounded bg-[#141E33]/60 border border-[#1E293B]/60">
              <span className="text-sky-400 font-semibold">✓ MOMENTUM_FILTER_OK</span>
              <span className="text-slate-500 text-[9px]">14:30:00 UTC</span>
            </div>
            <div className="text-[10px] flex items-center justify-between text-slate-300 p-1 rounded bg-[#141E33]/60 border border-[#1E293B]/60">
              <span className="text-amber-400 font-semibold">⚡ VOLATILITY_EXPANSION</span>
              <span className="text-slate-500 text-[9px]">14:15:00 UTC</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
