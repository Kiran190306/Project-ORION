import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { tradesApi } from '../api/endpoints';
import type { TradeResponse } from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Table, Column } from '../components/common/Table';
import { Pagination } from '../components/common/Pagination';
import { formatUnits, formatPrice, formatCurrency, formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const TradesPage: React.FC = () => {
  const [trades, setTrades] = useState<TradeResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await tradesApi.list({
        limit,
        offset,
        symbol: symbolFilter.trim() || undefined,
      });
      setTrades(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, symbolFilter]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  const columns: Column<TradeResponse>[] = [
    {
      header: 'Trade ID',
      render: (item) => (
        <span className="font-mono text-slate-300" title={item.trade_id}>
          {item.trade_id.substring(0, 8)}&hellip;
        </span>
      ),
    },
    {
      header: 'Order ID',
      render: (item) => (
        <span className="font-mono text-slate-400 text-xs" title={item.order_id}>
          {item.order_id.substring(0, 8)}&hellip;
        </span>
      ),
    },
    {
      header: 'Symbol',
      accessor: 'symbol',
      className: 'font-bold font-mono text-slate-100',
    },
    {
      header: 'Side',
      render: (item) => <Badge variant={item.side === 'BUY' ? 'buy' : 'sell'}>{item.side}</Badge>,
    },
    {
      header: 'Executed Volume',
      render: (item) => <span className="font-mono">{formatUnits(item.quantity)}</span>,
    },
    {
      header: 'Fill Price',
      render: (item) => <span className="font-mono">{formatPrice(item.price)}</span>,
    },
    {
      header: 'Commission',
      render: (item) => <span className="font-mono text-slate-400">{formatCurrency(item.commission)}</span>,
    },
    {
      header: 'Execution Time (UTC)',
      render: (item) => (
        <span className="font-mono text-xs text-slate-400">{formatDateTime(item.timestamp)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              TRADE EXECUTION LEDGER
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Historical transaction fills &bull; Broker execution confirmations &bull; Institutional trade records
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchTrades()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Filter Bar */}
      <Card className="p-3">
        <div className="relative w-full max-w-md font-mono text-xs">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={symbolFilter}
            onChange={(e) => {
              setSymbolFilter(e.target.value);
              setOffset(0);
            }}
            placeholder="Filter by symbol (e.g. EUR/USD)..."
            className="w-full pl-9 pr-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-600 focus:border-sky-500 focus:outline-none"
          />
        </div>
      </Card>

      {/* Trades Table */}
      <Card>
        {error ? (
          <div className="py-8 text-center text-xs text-rose-400 font-mono">
            Error loading trade history: {error}
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={trades}
              isLoading={isLoading}
              emptyMessage="No trade fills recorded for this account."
              keyExtractor={(item) => item.trade_id}
            />
            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onOffsetChange={(newOffset) => setOffset(newOffset)}
            />
          </>
        )}
      </Card>
    </div>
  );
};
