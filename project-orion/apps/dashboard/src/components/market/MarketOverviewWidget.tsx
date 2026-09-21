import React, { useState, useEffect, useCallback } from 'react';
import { Radio, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { marketDataApi } from '../../api/endpoints';
import type { MarketQuote } from '../../api/types';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';

const WATCHLIST_SYMBOLS = ['EUR/USD', 'GBP/USD', 'USD/JPY'];

export const MarketOverviewWidget: React.FC = () => {
  const [quotes, setQuotes] = useState<Record<string, MarketQuote>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuotes = useCallback(async () => {
    try {
      const results = await Promise.allSettled(
        WATCHLIST_SYMBOLS.map((sym) => marketDataApi.getQuote(sym))
      );
      const newQuotes: Record<string, MarketQuote> = {};
      results.forEach((res, idx) => {
        if (res.status === 'fulfilled') {
          newQuotes[WATCHLIST_SYMBOLS[idx]] = res.value;
        }
      });
      setQuotes(newQuotes);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market rates');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuotes();
    const interval = setInterval(fetchQuotes, 10000);
    return () => clearInterval(interval);
  }, [fetchQuotes]);

  return (
    <Card
      title="Live Market Feed"
      subtitle="Canonical institutional pricing & quality governance (Paper execution sync)"
      action={
        <div className="flex items-center gap-2">
          <Badge variant="info">
            <Radio className="w-3 h-3 mr-1 inline animate-pulse text-sky-400" />
            PAPER FEED
          </Badge>
          <button
            onClick={() => {
              setIsLoading(true);
              fetchQuotes();
            }}
            title="Refresh Quotes"
            className="p-1 rounded text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      }
    >
      {error && (
        <div className="p-3 mb-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center gap-2 font-mono">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {WATCHLIST_SYMBOLS.map((symbol) => {
          const quote = quotes[symbol];
          if (!quote) {
            return (
              <div
                key={symbol}
                className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 animate-pulse font-mono text-xs"
              >
                <div className="text-slate-400 font-bold">{symbol}</div>
                <div className="h-4 bg-slate-800 rounded mt-2 w-20" />
              </div>
            );
          }

          const isStale = quote.is_stale;
          const spreadPips = quote.spread_pips != null ? Number(quote.spread_pips).toFixed(1) : '-';

          return (
            <div
              key={symbol}
              className={`p-3 rounded-lg border transition-colors font-mono ${
                isStale
                  ? 'bg-amber-950/20 border-amber-800/60'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-slate-200 text-sm">{quote.symbol}</span>
                {isStale ? (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-300 border border-amber-700/60">
                    <AlertTriangle className="w-3 h-3" />
                    STALE
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
                    <CheckCircle2 className="w-3 h-3" />
                    {quote.quality}
                  </span>
                )}
              </div>

              <div className="flex items-baseline justify-between mb-1.5">
                <span className="text-slate-400 text-xs">Mid Rate:</span>
                <span className="font-bold text-slate-100 text-base">
                  {Number(quote.mid).toFixed(symbol.includes('JPY') ? 3 : 5)}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1.5 border-t border-slate-800/80 text-slate-400">
                <div>
                  <span className="text-slate-500">Bid: </span>
                  <span className="text-slate-300">{Number(quote.bid).toFixed(symbol.includes('JPY') ? 3 : 5)}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500">Ask: </span>
                  <span className="text-slate-300">{Number(quote.ask).toFixed(symbol.includes('JPY') ? 3 : 5)}</span>
                </div>
                <div>
                  <span className="text-slate-500">Spread: </span>
                  <span className="text-sky-300 font-semibold">{spreadPips} pips</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-500">Src: </span>
                  <span className="text-slate-300">{quote.provider}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
