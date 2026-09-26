import React, { useState } from 'react';
import { Search, TrendingUp, TrendingDown } from 'lucide-react';

export interface WatchlistPair {
  symbol: string;
  name: string;
  bid: number;
  ask: number;
  spreadPips: number;
  change24h: number;
  high: number;
  low: number;
}

const DEFAULT_WATCHLIST: WatchlistPair[] = [
  { symbol: 'EUR/USD', name: 'Euro / US Dollar', bid: 1.08502, ask: 1.08522, spreadPips: 0.2, change24h: 0.35, high: 1.0874, low: 1.0815 },
  { symbol: 'GBP/USD', name: 'British Pound / USD', bid: 1.27110, ask: 1.27140, spreadPips: 0.3, change24h: -0.18, high: 1.2745, low: 1.2680 },
  { symbol: 'USD/JPY', name: 'US Dollar / Yen', bid: 155.210, ask: 155.240, spreadPips: 0.3, change24h: 0.42, high: 155.80, low: 154.90 },
  { symbol: 'AUD/USD', name: 'Aussie / US Dollar', bid: 0.65420, ask: 0.65460, spreadPips: 0.4, change24h: 0.12, high: 0.6570, low: 0.6520 },
  { symbol: 'USD/CAD', name: 'US Dollar / Canadian', bid: 1.36850, ask: 1.36900, spreadPips: 0.5, change24h: -0.22, high: 1.3720, low: 1.3660 },
  { symbol: 'USD/CHF', name: 'US Dollar / Swiss Franc', bid: 0.88410, ask: 0.88450, spreadPips: 0.4, change24h: 0.08, high: 0.8870, low: 0.8820 },
  { symbol: 'NZD/USD', name: 'Kiwi / US Dollar', bid: 0.60120, ask: 0.60170, spreadPips: 0.5, change24h: -0.45, high: 0.6050, low: 0.5995 },
  { symbol: 'EUR/GBP', name: 'Euro / British Pound', bid: 0.85350, ask: 0.85380, spreadPips: 0.3, change24h: 0.25, high: 0.8560, low: 0.8510 },
];

interface TerminalWatchlistProps {
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  className?: string;
}

export const TerminalWatchlist: React.FC<TerminalWatchlistProps> = ({
  selectedSymbol,
  onSelectSymbol,
  className = '',
}) => {
  const [search, setSearch] = useState('');

  const filtered = DEFAULT_WATCHLIST.filter(
    (p) =>
      p.symbol.toLowerCase().includes(search.toLowerCase()) ||
      p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div
      className={`rounded-xl border border-[#1E293B] bg-[#141E33] flex flex-col overflow-hidden ${className}`}
      style={{ backgroundColor: '#141E33', borderColor: '#1E293B' }}
    >
      {/* Header */}
      <div className="p-3 border-b border-[#1E293B] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-sky-400" />
          <h3 className="text-xs font-bold font-mono text-slate-100 tracking-wider uppercase">
            FX Watchlist
          </h3>
        </div>
        <span className="text-[10px] font-mono text-slate-500 uppercase">Live Stream</span>
      </div>

      {/* Quick Filter */}
      <div className="p-2 border-b border-[#1E293B] bg-[#0F172A]/50">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter pairs..."
            className="w-full bg-[#090D16] border border-[#1E293B] rounded pl-8 pr-2 py-1 text-[11px] font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-sky-500/50"
          />
        </div>
      </div>

      {/* Pairs List */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1E293B]/60 max-h-[460px]">
        {filtered.map((item) => {
          const isSelected = item.symbol === selectedSymbol;
          const isUp = item.change24h >= 0;

          return (
            <div
              key={item.symbol}
              onClick={() => onSelectSymbol(item.symbol)}
              className={`p-2.5 transition-all cursor-pointer font-mono flex items-center justify-between ${
                isSelected
                  ? 'bg-sky-500/10 border-l-2 border-l-sky-400 pl-2'
                  : 'hover:bg-[#1A2742]/80'
              }`}
            >
              <div>
                <div className="flex items-center gap-1.5">
                  <span className={`text-xs font-bold ${isSelected ? 'text-sky-300' : 'text-slate-100'}`}>
                    {item.symbol}
                  </span>
                  <span className="text-[9px] text-slate-500 bg-[#090D16] px-1 rounded border border-[#1E293B]">
                    {item.spreadPips}p
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  L: {item.low} H: {item.high}
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs font-semibold text-slate-200 tabular-nums">
                  {item.bid.toFixed(item.symbol.includes('JPY') ? 3 : 5)}
                </div>
                <div
                  className={`text-[10px] font-medium flex items-center justify-end gap-0.5 tabular-nums ${
                    isUp ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {isUp ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                  <span>{isUp ? '+' : ''}{item.change24h}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
