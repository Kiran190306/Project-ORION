import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Search, Filter } from 'lucide-react';
import { positionsApi } from '../api/endpoints';
import type { PositionResponse } from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { Table, Column } from '../components/common/Table';
import { Pagination } from '../components/common/Pagination';
import { useToast } from '../components/common/Toast';
import { formatUnits, formatPrice, formatPnl, formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const PositionsPage: React.FC = () => {
  const [positions, setPositions] = useState<PositionResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(15);
  const [offset, setOffset] = useState(0);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [openFilter, setOpenFilter] = useState<string>('true'); // Default to open
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Close position modal state
  const [selectedPosition, setSelectedPosition] = useState<PositionResponse | null>(null);
  const [isCloseOpen, setIsCloseOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const toast = useToast();

  const fetchPositions = useCallback(async () => {
    setIsLoading(true);
    try {
      const isOpenParam =
        openFilter === 'true' ? true : openFilter === 'false' ? false : undefined;

      const res = await positionsApi.list({
        limit,
        offset,
        symbol: symbolFilter.trim() || undefined,
        is_open: isOpenParam,
      });
      setPositions(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, symbolFilter, openFilter]);

  useEffect(() => {
    fetchPositions();
  }, [fetchPositions]);

  const handleClosePosition = async () => {
    if (!selectedPosition) return;
    setIsSubmitting(true);
    try {
      const res = await positionsApi.close(selectedPosition.id);
      toast.success(
        `Position closed: ${res.symbol} (${formatPnl(res.realized_pnl).formatted} realized)`
      );
      setIsCloseOpen(false);
      setSelectedPosition(null);
      fetchPositions();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<PositionResponse>[] = [
    {
      header: 'Position ID',
      render: (item) => (
        <span className="font-mono text-slate-300" title={item.id}>
          {item.id.substring(0, 8)}&hellip;
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
      header: 'Units',
      render: (item) => <span className="font-mono">{formatUnits(item.quantity)}</span>,
    },
    {
      header: 'Entry Price',
      render: (item) => <span className="font-mono">{formatPrice(item.open_price)}</span>,
    },
    {
      header: 'Current Price',
      render: (item) => <span className="font-mono">{formatPrice(item.current_price)}</span>,
    },
    {
      header: 'Unrealized P&L',
      render: (item) => {
        const pnl = formatPnl(item.unrealized_pnl);
        return (
          <span
            className={`font-mono font-bold ${
              pnl.isPositive ? 'text-emerald-400' : pnl.isNegative ? 'text-rose-400' : 'text-slate-300'
            }`}
          >
            {pnl.formatted}
          </span>
        );
      },
    },
    {
      header: 'Status',
      render: (item) => (
        <Badge variant={item.is_open ? 'info' : 'default'}>
          {item.is_open ? 'OPEN' : 'CLOSED'}
        </Badge>
      ),
    },
    {
      header: 'Opened At (UTC)',
      render: (item) => (
        <span className="font-mono text-xs text-slate-400">{formatDateTime(item.opened_at)}</span>
      ),
    },
    {
      header: 'Actions',
      render: (item) => {
        if (!item.is_open) return <span className="text-slate-600 text-xs">—</span>;
        return (
          <button
            onClick={() => {
              setSelectedPosition(item);
              setIsCloseOpen(true);
            }}
            className="text-xs font-mono text-rose-400 hover:text-rose-300 hover:underline cursor-pointer"
          >
            Close
          </button>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold font-mono tracking-tight text-slate-100">
              POSITIONS MONITOR
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Active market exposure &bull; Real-time mark-to-market valuations &bull; Paper position closing
          </p>
        </div>

        <Button variant="outline" size="sm" onClick={() => fetchPositions()}>
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Filters Bar */}
      <Card className="p-3">
        <div className="flex flex-col sm:flex-row items-center gap-3 font-mono text-xs">
          <div className="relative flex-1 w-full">
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

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={openFilter}
              onChange={(e) => {
                setOpenFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full sm:w-auto px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="true">Open Positions Only</option>
              <option value="false">Closed Positions Only</option>
              <option value="">All Positions</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Positions Table */}
      <Card>
        {error ? (
          <div className="py-8 text-center text-xs text-rose-400 font-mono">
            Error loading positions: {error}
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={positions}
              isLoading={isLoading}
              emptyMessage="No positions match the selected filter."
              keyExtractor={(item) => item.id}
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

      {/* Close Position Modal */}
      <Modal
        isOpen={isCloseOpen}
        onClose={() => setIsCloseOpen(false)}
        title="Close Paper Position"
        maxWidth="sm"
      >
        <div className="space-y-4 font-mono text-xs">
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px]">
            <strong>PAPER TRADING:</strong> Position will be liquidated at simulated market price. P&L will be realized in your paper account balance.
          </div>

          {selectedPosition && (
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Position ID:</span>
                <span>{selectedPosition.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Instrument:</span>
                <span className="font-bold text-slate-100">
                  {selectedPosition.symbol} ({selectedPosition.side})
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Volume:</span>
                <span>{formatUnits(selectedPosition.quantity)} units</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Entry Price:</span>
                <span>{formatPrice(selectedPosition.open_price)}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-slate-800">
                <span className="text-slate-500">Est. Unrealized P&L:</span>
                <span
                  className={`font-bold ${
                    formatPnl(selectedPosition.unrealized_pnl).isPositive
                      ? 'text-emerald-400'
                      : 'text-rose-400'
                  }`}
                >
                  {formatPnl(selectedPosition.unrealized_pnl).formatted}
                </span>
              </div>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCloseOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleClosePosition}
            >
              Confirm Close Position
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
