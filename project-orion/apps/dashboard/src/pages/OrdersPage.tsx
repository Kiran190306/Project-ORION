import React, { useState, useEffect, useCallback } from 'react';
import { Plus, RefreshCw, Search, Filter } from 'lucide-react';
import { ordersApi } from '../api/endpoints';
import type { OrderResponse, CreateOrderRequest, OrderSide, OrderType } from '../api/types';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge, PaperTradingBadge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { Table, Column } from '../components/common/Table';
import { Pagination } from '../components/common/Pagination';
import { useToast } from '../components/common/Toast';
import { formatUnits, formatPrice, formatDateTime } from '../utils/formatters';
import { getErrorMessage } from '../utils/errors';

export const OrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(15);
  const [offset, setOffset] = useState(0);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<OrderResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create Order Form State
  const [formData, setFormData] = useState<{
    symbol: string;
    side: OrderSide;
    order_type: OrderType;
    quantity: string;
    price: string;
    stop_price: string;
    stop_loss: string;
    take_profit: string;
  }>({
    symbol: 'EUR/USD',
    side: 'BUY',
    order_type: 'MARKET',
    quantity: '10000',
    price: '',
    stop_price: '',
    stop_loss: '',
    take_profit: '',
  });

  const toast = useToast();

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await ordersApi.list({
        limit,
        offset,
        symbol: symbolFilter.trim() || undefined,
        status: statusFilter || undefined,
      });
      setOrders(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, symbolFilter, statusFilter]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(formData.quantity);
    if (isNaN(qty) || qty <= 0) {
      toast.error('Order quantity must be a strictly positive number.');
      return;
    }

    if (formData.order_type === 'LIMIT' && (!formData.price || parseFloat(formData.price) <= 0)) {
      toast.error('Limit order requires a valid limit price.');
      return;
    }

    if (formData.order_type === 'STOP' && (!formData.stop_price || parseFloat(formData.stop_price) <= 0)) {
      toast.error('Stop order requires a valid trigger stop price.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: CreateOrderRequest = {
        symbol: formData.symbol.trim().toUpperCase(),
        side: formData.side,
        order_type: formData.order_type,
        quantity: qty,
        price: formData.price ? parseFloat(formData.price) : undefined,
        stop_price: formData.stop_price ? parseFloat(formData.stop_price) : undefined,
        stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : undefined,
        take_profit: formData.take_profit ? parseFloat(formData.take_profit) : undefined,
      };

      const res = await ordersApi.create(payload);
      toast.success(`Order created: ${res.symbol} ${res.side} (${res.status})`);
      setIsCreateOpen(false);
      // Reset form
      setFormData({
        symbol: 'EUR/USD',
        side: 'BUY',
        order_type: 'MARKET',
        quantity: '10000',
        price: '',
        stop_price: '',
        stop_loss: '',
        take_profit: '',
      });
      fetchOrders();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelOrder = async () => {
    if (!selectedOrder) return;
    setIsSubmitting(true);
    try {
      await ordersApi.cancel(selectedOrder.id);
      toast.success(`Order ${selectedOrder.id.substring(0, 8)} cancelled.`);
      setIsCancelOpen(false);
      setSelectedOrder(null);
      fetchOrders();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns: Column<OrderResponse>[] = [
    {
      header: 'Order ID',
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
      header: 'Type',
      render: (item) => <span className="font-mono text-xs text-slate-300">{item.order_type}</span>,
    },
    {
      header: 'Quantity',
      render: (item) => <span className="font-mono">{formatUnits(item.quantity)}</span>,
    },
    {
      header: 'Price',
      render: (item) => (
        <span className="font-mono text-slate-300">
          {item.price ? formatPrice(item.price) : 'MARKET'}
        </span>
      ),
    },
    {
      header: 'Status',
      render: (item) => {
        const variant =
          item.status === 'FILLED'
            ? 'success'
            : item.status === 'CANCELLED' || item.status === 'REJECTED'
            ? 'danger'
            : 'warning';
        return <Badge variant={variant}>{item.status}</Badge>;
      },
    },
    {
      header: 'Created (UTC)',
      render: (item) => (
        <span className="font-mono text-xs text-slate-400">
          {formatDateTime(item.created_at)}
        </span>
      ),
    },
    {
      header: 'Actions',
      render: (item) => {
        const cancellable = item.status === 'PENDING' || item.status === 'SUBMITTED';
        if (!cancellable) return <span className="text-slate-600 text-xs">—</span>;
        return (
          <button
            onClick={() => {
              setSelectedOrder(item);
              setIsCancelOpen(true);
            }}
            className="text-xs font-mono text-rose-400 hover:text-rose-300 hover:underline cursor-pointer"
          >
            Cancel
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
              ORDER MANAGEMENT
            </h1>
            <PaperTradingBadge size="sm" />
          </div>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Submit paper trading orders &bull; Monitor order execution &bull; Real-time status tracking
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button variant="outline" size="sm" onClick={() => fetchOrders()}>
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsCreateOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Place Paper Order
          </Button>
        </div>
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
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full sm:w-auto px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="FILLED">FILLED</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="PENDING">PENDING</option>
              <option value="CANCELLED">CANCELLED</option>
              <option value="REJECTED">REJECTED</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Orders Table */}
      <Card>
        {error ? (
          <div className="py-8 text-center text-xs text-rose-400 font-mono">
            Error loading orders: {error}
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={orders}
              isLoading={isLoading}
              emptyMessage="No paper trading orders match the current criteria."
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

      {/* Place Paper Order Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title={
          <div className="flex items-center gap-2">
            <span>Place Paper Order</span>
            <PaperTradingBadge size="sm" />
          </div>
        }
        maxWidth="lg"
      >
        <form onSubmit={handleCreateOrder} noValidate className="space-y-4 font-mono text-xs">
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] leading-relaxed">
            <strong>NOTICE:</strong> This order executes in <strong>PAPER TRADING MODE</strong>. No real-world funds or live broker connections are used.
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block uppercase text-slate-400 mb-1">Currency Pair</label>
              <input
                type="text"
                required
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
                placeholder="EUR/USD"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 uppercase focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block uppercase text-slate-400 mb-1">Side</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, side: 'BUY' })}
                  className={`py-2 rounded-lg border text-center font-bold cursor-pointer transition-all ${
                    formData.side === 'BUY'
                      ? 'bg-emerald-950 border-emerald-500 text-emerald-300 shadow-sm shadow-emerald-950'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, side: 'SELL' })}
                  className={`py-2 rounded-lg border text-center font-bold cursor-pointer transition-all ${
                    formData.side === 'SELL'
                      ? 'bg-rose-950 border-rose-500 text-rose-300 shadow-sm shadow-rose-950'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  SELL
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block uppercase text-slate-400 mb-1">Order Type</label>
              <select
                value={formData.order_type}
                onChange={(e) => setFormData({ ...formData, order_type: e.target.value as OrderType })}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              >
                <option value="MARKET">MARKET</option>
                <option value="LIMIT">LIMIT</option>
                <option value="STOP">STOP</option>
              </select>
            </div>

            <div>
              <label className="block uppercase text-slate-400 mb-1">Volume (Units)</label>
              <input
                type="number"
                required
                min="1"
                step="1"
                value={formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                placeholder="10000"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>
          </div>

          {formData.order_type === 'LIMIT' && (
            <div>
              <label className="block uppercase text-slate-400 mb-1">Limit Price</label>
              <input
                type="number"
                step="0.00001"
                required
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                placeholder="e.g. 1.08500"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>
          )}

          {formData.order_type === 'STOP' && (
            <div>
              <label className="block uppercase text-slate-400 mb-1">Stop Trigger Price</label>
              <input
                type="number"
                step="0.00001"
                required
                value={formData.stop_price}
                onChange={(e) => setFormData({ ...formData, stop_price: e.target.value })}
                placeholder="e.g. 1.09000"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block uppercase text-slate-400 mb-1">Stop Loss (Optional)</label>
              <input
                type="number"
                step="0.00001"
                value={formData.stop_loss}
                onChange={(e) => setFormData({ ...formData, stop_loss: e.target.value })}
                placeholder="e.g. 1.07500"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block uppercase text-slate-400 mb-1">Take Profit (Optional)</label>
              <input
                type="number"
                step="0.00001"
                value={formData.take_profit}
                onChange={(e) => setFormData({ ...formData, take_profit: e.target.value })}
                placeholder="e.g. 1.10000"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsCreateOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
            >
              Confirm & Submit Paper Order
            </Button>
          </div>
        </form>
      </Modal>

      {/* Cancel Order Confirmation Modal */}
      <Modal
        isOpen={isCancelOpen}
        onClose={() => setIsCancelOpen(false)}
        title="Confirm Order Cancellation"
        maxWidth="sm"
      >
        <div className="space-y-4 font-mono text-xs">
          <p className="text-slate-300">
            Are you sure you want to cancel the following pending order?
          </p>
          {selectedOrder && (
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-slate-300">
              <div>
                <span className="text-slate-500">Order ID:</span> {selectedOrder.id}
              </div>
              <div>
                <span className="text-slate-500">Instrument:</span> {selectedOrder.symbol} ({selectedOrder.side})
              </div>
              <div>
                <span className="text-slate-500">Volume:</span> {selectedOrder.quantity} units
              </div>
            </div>
          )}
          <div className="pt-2 flex items-center justify-end gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsCancelOpen(false)}
            >
              Keep Order
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleCancelOrder}
            >
              Cancel Order
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
