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
        <span className="text-[10px] font-mono text-slate-400 bg-slate-800/60 border border-slate-700/60 px-1.5 py-0.5 rounded font-bold uppercase">
          TELEMETRY IDLE
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
            <div className="font-bold text-slate-300 text-xs">Awaiting Analysis</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Regime Detector: Idle</div>
          </div>

          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" />
              <span>Strategy Signal</span>
            </div>
            <div className="font-bold text-slate-300 text-xs flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
              No Active Signal
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Awaiting live signal ({selectedSymbol})</div>
          </div>
        </div>

        {/* Signal Confidence Meter */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-1.5">
          <div className="flex justify-between items-center text-[10px]">
            <span className="text-slate-400 uppercase font-semibold">Signal Confidence</span>
            <span className="text-slate-500 font-bold">N/A (No active signal)</span>
          </div>
          <div className="w-full h-1.5 bg-[#141E33] rounded-full overflow-hidden border border-[#1E293B]">
            <div className="h-full bg-slate-700 rounded-full w-0" />
          </div>
        </div>

        {/* Risk State & Sizing */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Risk State</span>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded inline-block">
              NOMINAL
            </span>
            <div className="text-[10px] text-slate-500 mt-1">Paper Guard Active</div>
          </div>
          <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B]">
            <span className="text-[10px] text-slate-500 uppercase block mb-1">Position Sizing</span>
            <span className="text-xs font-bold text-slate-200">Standard Lot Model</span>
            <div className="text-[10px] text-slate-500 mt-0.5">Risk-Adjusted Sizing: Not Configured</div>
          </div>
        </div>

        {/* Dynamic Exit Plan */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-2">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400 uppercase font-semibold flex items-center gap-1">
              <Target className="w-3 h-3 text-sky-400" />
              Dynamic Exit Plan
            </span>
            <span className="text-slate-500 font-bold">R:R Dynamic (ATR)</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-1.5 rounded bg-[#141E33]/60 border border-[#1E293B]">
              <div className="text-[9px] text-slate-400 uppercase">Stop Loss</div>
              <div className="font-bold text-slate-300">Dynamic ATR</div>
              <div className="text-[9px] text-slate-500">Trailing limit</div>
            </div>
            <div className="p-1.5 rounded bg-[#141E33]/60 border border-[#1E293B]">
              <div className="text-[9px] text-slate-400 uppercase">Take Profit</div>
              <div className="font-bold text-slate-300">Dynamic ATR</div>
              <div className="text-[9px] text-slate-500">Target limit</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-[#1E293B]">
            <span>Expected Capital at Risk:</span>
            <span className="text-slate-300 font-medium">Calculated at order placement</span>
          </div>
        </div>

        {/* Quantitative Robustness & Walk-Forward Validation */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-2">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-400 uppercase font-semibold">Backtest & Walk-Forward</span>
            <span className="text-slate-400 font-bold bg-slate-800/60 px-1 rounded border border-slate-700/60">
              UNVALIDATED
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Sharpe</div>
              <div className="font-bold text-slate-400">N/A</div>
            </div>
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Win Rate</div>
              <div className="font-bold text-slate-400">N/A</div>
            </div>
            <div className="p-1.5 rounded bg-[#141E33] border border-[#1E293B]">
              <div className="text-[9px] text-slate-500">Profit Fac</div>
              <div className="font-bold text-slate-400">N/A</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-400 flex justify-between pt-1 border-t border-[#1E293B]">
            <span>WFA Validation:</span>
            <span className="text-slate-400">Run backtest in Strategy Lab</span>
          </div>
        </div>

        {/* Recent Strategy Events Stream */}
        <div className="p-2.5 rounded-lg bg-[#090D16] border border-[#1E293B] space-y-1.5">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
            <span className="uppercase font-semibold flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              Recent Strategy Events
            </span>
            <span className="text-[9px] text-slate-500">Telemetry Feed</span>
          </div>
          <div className="p-2 rounded bg-[#141E33]/40 border border-[#1E293B]/60 text-[10px] text-slate-400 text-center">
            No active strategy events dispatched. Autonomous worker cycle awaiting trigger.
          </div>
        </div>
      </div>
    </div>
  );
};
