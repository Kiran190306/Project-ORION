import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  RefreshCw,
  Search,
  Filter,
  Calculator,
  ChevronDown,
  ChevronUp,
  Layers,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { ordersApi, positionsApi, strategiesApi } from '../api/endpoints';
import type {
  OrderResponse,
  CreateOrderRequest,
  OrderSide,
  OrderType,
  AccountStrategyConfigResponse,
  PositionSizingMethod,
  PositionSizingResponse,
} from '../api/types';
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
  const [strategyFilter, setStrategyFilter] = useState('');
  const [availableStrategies, setAvailableStrategies] = useState<AccountStrategyConfigResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<OrderResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Position Sizing Calculator State
  const [showSizer, setShowSizer] = useState(false);
  const [sizingMethod, setSizingMethod] = useState<PositionSizingMethod>('risk_percent');
  const [sizingRiskPct, setSizingRiskPct] = useState('1.0');
  const [sizingAtr, setSizingAtr] = useState('');
  const [sizingKellyFraction, setSizingKellyFraction] = useState('0.25');
  const [sizingFixedNotional, setSizingFixedNotional] = useState('10000');
  const [isCalculatingSizing, setIsCalculatingSizing] = useState(false);
  const [sizingResult, setSizingResult] = useState<PositionSizingResponse | null>(null);

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
    trailing_distance: string;
    strategy_id: string;
  }>({
    symbol: 'EUR/USD',
    side: 'BUY',
    order_type: 'MARKET',
    quantity: '10000',
    price: '',
    stop_price: '',
    stop_loss: '',
    take_profit: '',
    trailing_distance: '',
    strategy_id: '',
  });

  const toast = useToast();

  const fetchStrategies = useCallback(async () => {
    try {
      const configs = await strategiesApi.listAccountConfigs();
      if (Array.isArray(configs)) {
        setAvailableStrategies(configs);
      } else {
        setAvailableStrategies([]);
      }
    } catch {
      setAvailableStrategies([]);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const fetchOrders = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await ordersApi.list({
        limit,
        offset,
        symbol: symbolFilter.trim() || undefined,
        status: statusFilter || undefined,
        strategy_id: strategyFilter || undefined,
      });
      setOrders(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }, [limit, offset, symbolFilter, statusFilter, strategyFilter]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const handleCalculateSizing = async () => {
    setIsCalculatingSizing(true);
    try {
      const res = await positionsApi.calculateSizing({
        symbol: formData.symbol.trim().toUpperCase(),
        method: sizingMethod,
        risk_percent: parseFloat(sizingRiskPct) || 1.0,
        entry_price: formData.price ? parseFloat(formData.price) : undefined,
        stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : undefined,
        atr: sizingAtr ? parseFloat(sizingAtr) : undefined,
        kelly_fraction: parseFloat(sizingKellyFraction) || 0.25,
        fixed_notional: sizingFixedNotional ? parseFloat(sizingFixedNotional) : undefined,
      });
      setSizingResult(res);
      if (res.is_valid) {
        toast.success(`Calculated size: ${res.calculated_units} units ($${res.monetary_risk} risk)`);
      } else if (res.validation_errors.length > 0) {
        toast.error(res.validation_errors[0]);
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsCalculatingSizing(false);
    }
  };

  const handleApplySizing = () => {
    if (sizingResult && sizingResult.is_valid && Number(sizingResult.calculated_units) > 0) {
      setFormData((prev) => ({
        ...prev,
        quantity: String(sizingResult.calculated_units),
      }));
      toast.success(`Applied ${sizingResult.calculated_units} units to Order Volume.`);
    }
  };

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

    if (formData.order_type === 'TRAILING_STOP' && (!formData.trailing_distance || parseFloat(formData.trailing_distance) <= 0)) {
      toast.error('Trailing Stop order requires a valid positive trailing distance.');
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
        trailing_distance: formData.trailing_distance ? parseFloat(formData.trailing_distance) : undefined,
        strategy_id: formData.strategy_id || undefined,
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
        trailing_distance: '',
        strategy_id: '',
      });
      setSizingResult(null);
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
      header: 'Strategy',
      render: (item) =>
        item.strategy_id ? (
          <Badge variant="info">{item.strategy_id}</Badge>
        ) : (
          <span className="text-slate-500 font-mono text-xs">Manual</span>
        ),
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

      {/* Paper Trading Safety Banner */}
      <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-amber-300 font-bold">
          <PaperTradingBadge size="sm" />
          <span>PAPER TRADING ONLY &bull; $0 REAL CAPITAL AT RISK</span>
        </div>
        <div className="text-[11px] text-amber-400/80">
          Simulated order fills &bull; Zero live broker capital risk
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

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <select
              value={strategyFilter}
              onChange={(e) => {
                setStrategyFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full sm:w-auto px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="">All Strategies</option>
              {(availableStrategies || []).map((s) => (
                <option key={s.strategy_id} value={s.strategy_id}>
                  {s.strategy_id} ({s.deployment_status || (s.is_active ? 'ACTIVE' : 'INACTIVE')})
                </option>
              ))}
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
            <strong>PAPER TRADING ONLY &bull; $0 REAL CAPITAL AT RISK:</strong> This simulated order executes strictly in the internal Project ORION paper execution adapter. No real-world funds or live broker connections are accessed.
          </div>

          {/* Executing Strategy Selection */}
          <div>
            <label className="block uppercase text-slate-400 mb-1">Executing Strategy (Optional)</label>
            <select
              value={formData.strategy_id}
              onChange={(e) => setFormData({ ...formData, strategy_id: e.target.value })}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
            >
              <option value="">Manual Execution (No Strategy)</option>
              {(availableStrategies || []).map((s) => (
                <option key={s.strategy_id} value={s.strategy_id}>
                  {s.strategy_id} — {s.deployment_status || (s.is_active ? 'ACTIVE' : 'INACTIVE')}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-slate-500 mt-1">
              Links order, fill, and position to institutional multi-strategy attribution tracking.
            </p>
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

          {/* Quantitative Position Sizer Accordion */}
          <div className="border border-sky-900/40 bg-sky-950/20 rounded-lg p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calculator className="w-4 h-4 text-sky-400" />
                <span className="font-bold text-sky-200">Quantitative Position Sizer</span>
                <span className="text-[10px] bg-sky-900/60 text-sky-300 px-1.5 py-0.5 rounded font-mono">
                  Domain Sizer API
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowSizer(!showSizer)}
                className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 cursor-pointer font-mono"
              >
                {showSizer ? (
                  <>Hide Calculator <ChevronUp className="w-3.5 h-3.5" /></>
                ) : (
                  <>Open Calculator <ChevronDown className="w-3.5 h-3.5" /></>
                )}
              </button>
            </div>

            {showSizer && (
              <div className="space-y-3 pt-2 border-t border-sky-900/30">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1">Sizing Model</label>
                    <select
                      value={sizingMethod}
                      onChange={(e) => setSizingMethod(e.target.value as PositionSizingMethod)}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
                    >
                      <option value="risk_percent">Risk % (Fixed Account Risk)</option>
                      <option value="atr">ATR Volatility (2.0x ATR)</option>
                      <option value="kelly">Kelly Criterion (Fractional)</option>
                      <option value="volatility">Volatility Target (Annualized)</option>
                      <option value="fixed">Fixed Notional Amount</option>
                    </select>
                  </div>

                  {sizingMethod === 'risk_percent' && (
                    <div>
                      <label className="block text-slate-400 mb-1">Risk Percentage (%)</label>
                      <input
                        type="number"
                        step="0.1"
                        min="0.01"
                        max="10.0"
                        value={sizingRiskPct}
                        onChange={(e) => setSizingRiskPct(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
                        placeholder="1.0"
                      />
                    </div>
                  )}

                  {sizingMethod === 'atr' && (
                    <div>
                      <label className="block text-slate-400 mb-1">ATR Distance (Price)</label>
                      <input
                        type="number"
                        step="0.0001"
                        min="0.00001"
                        value={sizingAtr}
                        onChange={(e) => setSizingAtr(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
                        placeholder="e.g. 0.0015"
                      />
                    </div>
                  )}

                  {sizingMethod === 'kelly' && (
                    <div>
                      <label className="block text-slate-400 mb-1">Kelly Fraction</label>
                      <input
                        type="number"
                        step="0.05"
                        min="0.05"
                        max="1.0"
                        value={sizingKellyFraction}
                        onChange={(e) => setSizingKellyFraction(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
                        placeholder="0.25 (Quarter-Kelly)"
                      />
                    </div>
                  )}

                  {sizingMethod === 'fixed' && (
                    <div>
                      <label className="block text-slate-400 mb-1">Fixed Notional (USD)</label>
                      <input
                        type="number"
                        step="1000"
                        min="100"
                        value={sizingFixedNotional}
                        onChange={(e) => setSizingFixedNotional(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-800 text-slate-100 focus:border-sky-500 focus:outline-none"
                        placeholder="10000"
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCalculateSizing}
                    isLoading={isCalculatingSizing}
                    className="border-sky-700 text-sky-300 hover:bg-sky-950"
                  >
                    Calculate Recommended Size
                  </Button>
                  <span className="text-[10px] text-slate-500">
                    Uses live stop loss & account equity via backend domain sizer
                  </span>
                </div>

                {sizingResult && (
                  <div
                    className={`p-3 rounded-lg border text-xs space-y-2 ${
                      sizingResult.is_valid
                        ? 'bg-slate-950 border-emerald-500/40 text-slate-200'
                        : 'bg-rose-950/20 border-rose-500/40 text-rose-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {sizingResult.is_valid ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-rose-400" />
                        )}
                        <span className="font-bold">
                          {sizingResult.is_valid
                            ? `Recommended: ${formatUnits(sizingResult.calculated_units)} units`
                            : 'Calculation Failed'}
                        </span>
                      </div>
                      <Badge
                        variant={
                          sizingResult.market_data_status === 'REALTIME'
                            ? 'success'
                            : sizingResult.market_data_status === 'FALLBACK'
                            ? 'warning'
                            : 'default'
                        }
                      >
                        {sizingResult.market_data_status} PRICE
                      </Badge>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-1 border-t border-slate-800">
                      <div>
                        <span className="text-slate-500 block">Monetary Risk:</span>
                        <span className="font-mono font-semibold">${sizingResult.monetary_risk}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Stop Distance:</span>
                        <span className="font-mono font-semibold">
                          {sizingResult.stop_distance !== null ? sizingResult.stop_distance : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Req Margin:</span>
                        <span className="font-mono font-semibold">${sizingResult.required_margin}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Account Equity:</span>
                        <span className="font-mono font-semibold">${sizingResult.account_equity}</span>
                      </div>
                    </div>

                    {sizingResult.constraints_applied.length > 0 && (
                      <div className="text-[10px] text-amber-400/90 bg-amber-950/20 p-1.5 rounded">
                        <strong>Constraints:</strong> {sizingResult.constraints_applied.join(', ')}
                      </div>
                    )}

                    {sizingResult.validation_errors.length > 0 && (
                      <div className="text-[10px] text-rose-400 bg-rose-950/30 p-1.5 rounded">
                        <strong>Validation Errors:</strong> {sizingResult.validation_errors.join('; ')}
                      </div>
                    )}

                    {sizingResult.is_valid && Number(sizingResult.calculated_units) > 0 && (
                      <div className="pt-1 flex justify-end">
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={handleApplySizing}
                        >
                          Apply {formatUnits(sizingResult.calculated_units)} Units to Volume
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
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
                <option value="TRAILING_STOP">TRAILING STOP</option>
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

          {formData.order_type === 'TRAILING_STOP' && (
            <div>
              <label className="block uppercase text-slate-400 mb-1">Trailing Distance (Price Offset / Pips)</label>
              <input
                type="number"
                step="0.0001"
                required
                value={formData.trailing_distance}
                onChange={(e) => setFormData({ ...formData, trailing_distance: e.target.value })}
                placeholder="e.g. 0.0020 (20 pips)"
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
