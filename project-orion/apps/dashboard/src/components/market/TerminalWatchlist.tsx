import React, { useState, useCallback, useEffect } from 'react';
import { Search, RefreshCw, AlertCircle } from 'lucide-react';
import { marketDataApi } from '../../api/endpoints';
import type { MarketQuote } from '../../api/types';
import { usePolling } from '../../hooks/usePolling';

export interface WatchlistPairConfig {
  symbol: string;
  name: string;
}

const WATCHLIST_SYMBOLS: WatchlistPairConfig[] = [
  { symbol: 'EUR/USD', name: 'Euro / US Dollar' },
  { symbol: 'GBP/USD', name: 'British Pound / USD' },
  { symbol: 'USD/JPY', name: 'US Dollar / Yen' },
  { symbol: 'AUD/USD', name: 'Aussie / US Dollar' },
  { symbol: 'USD/CAD', name: 'US Dollar / Canadian' },
  { symbol: 'USD/CHF', name: 'US Dollar / Swiss Franc' },
  { symbol: 'NZD/USD', name: 'Kiwi / US Dollar' },
  { symbol: 'EUR/GBP', name: 'Euro / British Pound' },
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
  const [quotes, setQuotes] = useState<Record<string, MarketQuote>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuotes = useCallback(async () => {
    try {
      const results = await Promise.allSettled(
        WATCHLIST_SYMBOLS.map((item) => marketDataApi.getQuote(item.symbol))
      );
      const newQuotes: Record<string, MarketQuote> = {};
      let anySuccess = false;

      results.forEach((res) => {
        if (res.status === 'fulfilled' && res.value) {
          newQuotes[res.value.symbol] = res.value;
          anySuccess = true;
        }
      });

      if (anySuccess) {
        setQuotes((prev) => ({ ...prev, ...newQuotes }));
        setError(null);
      } else {
        setQuotes((prev) => {
          if (Object.keys(prev).length === 0) {
            setError('Market quotes currently unavailable');
          }
          return prev;
        });
      }
    } catch {
      setQuotes((prev) => {
        if (Object.keys(prev).length === 0) {
          setError('Failed to fetch market quotes');
        }
        return prev;
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Poll real quotes every 10 seconds with tab visibility checking
  usePolling(fetchQuotes, 10000);

  // Initial load
  useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  const filtered = WATCHLIST_SYMBOLS.filter(
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
      <div className="p-3 border-b border-[#1E293B] bg-[#0F172A] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-amber-400 animate-pulse' : error ? 'bg-rose-400' : 'bg-sky-400'}`} />
          <h3 className="text-xs font-bold font-mono text-slate-100 tracking-wider uppercase">
            FX Watchlist
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-400 uppercase">
            {isLoading ? 'SYNCING...' : 'LIVE QUOTES'}
          </span>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchQuotes();
            }}
            title="Refresh Watchlist"
            className="text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
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

      {/* Error state if no quotes could be loaded */}
      {error && Object.keys(quotes).length === 0 && !isLoading && (
        <div className="p-4 text-center">
          <AlertCircle className="w-5 h-5 text-amber-400 mx-auto mb-1.5" />
          <div className="text-[11px] font-mono text-slate-400 mb-2">{error}</div>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              fetchQuotes();
            }}
            className="text-xs font-mono text-sky-400 hover:underline inline-flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="w-3 h-3" /> Retry Connection
          </button>
        </div>
      )}

      {/* Pairs List */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1E293B]/60 max-h-[460px]">
        {filtered.map((item) => {
          const isSelected = item.symbol === selectedSymbol;
          const quote = quotes[item.symbol];
          const isJpy = item.symbol.includes('JPY');
          const decimals = isJpy ? 3 : 5;

          const bidNum = quote ? Number(quote.bid) : null;
          const askNum = quote ? Number(quote.ask) : null;
          let spreadPips: string = '--';
          if (quote?.spread_pips) {
            spreadPips = `${Number(quote.spread_pips).toFixed(1)}p`;
          } else if (bidNum != null && askNum != null) {
            const pipMult = isJpy ? 100 : 10000;
            spreadPips = `${(Math.abs(askNum - bidNum) * pipMult).toFixed(1)}p`;
          }

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
                  <span className="text-[9px] text-slate-400 bg-[#090D16] px-1 rounded border border-[#1E293B]">
                    {spreadPips}
                  </span>
                  {quote?.is_stale && (
                    <span className="text-[8px] text-amber-400 bg-amber-950/40 px-1 rounded border border-amber-800/40">
                      STALE
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {item.name}
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs font-semibold text-slate-200 tabular-nums">
                  {bidNum != null ? bidNum.toFixed(decimals) : (
                    <span className="text-slate-500">--.-----</span>
                  )}
                </div>
                <div className="text-[10px] text-slate-400 tabular-nums mt-0.5">
                  Ask: {askNum != null ? askNum.toFixed(decimals) : '--'}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
