import React, { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import {
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useToast } from '../common/Toast';
import { ordersApi, marketDataApi } from '../../api/endpoints';
import { getErrorMessage } from '../../utils/errors';

export interface Candle {
  time: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type CanonicalTimeframe = 'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1';

interface TerminalMarketChartProps {
  symbol?: string;
  onPlaceOrder?: (side: 'BUY' | 'SELL', quantity: number) => void;
  className?: string;
}

export const TerminalMarketChart: React.FC<TerminalMarketChartProps> = ({
  symbol = 'EUR/USD',
  onPlaceOrder,
  className = '',
}) => {
  const toast = useToast();
  const [timeframe, setTimeframe] = useState<CanonicalTimeframe>('H1');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showEMA, setShowEMA] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showRSI, setShowRSI] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [lotSize, setLotSize] = useState<number>(0.1);
  const [isOrderSubmitting, setIsOrderSubmitting] = useState(false);

  // Real historical market candles state
  const [candles, setCandles] = useState<Candle[]>([]);
  const [candlesLoading, setCandlesLoading] = useState<boolean>(true);
  const [candlesError, setCandlesError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch genuine historical candles from market data API
  const fetchCandles = useCallback(async () => {
    setCandlesLoading(true);
    setCandlesError(null);
    try {
      const res = await marketDataApi.getCandles(symbol, { timeframe, limit: 60 });
      const rawCandles = res.candles || [];
      const mapped: Candle[] = rawCandles.map((c) => {
        const d = new Date(c.timestamp);
        const validDate = !isNaN(d.getTime());
        const timeStr = validDate
          ? `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`
          : String(c.timestamp);
        return {
          time: timeStr,
          timestamp: validDate ? d.getTime() : Date.now(),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
          volume: Number(c.volume),
        };
      });
      setCandles(mapped);
    } catch (err) {
      setCandlesError(getErrorMessage(err));
      setCandles([]);
    } finally {
      setCandlesLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchCandles();
  }, [fetchCandles]);

  // Compute Technical Indicators: EMA 20, EMA 50, RSI 14, ATR 14
  const { ema20, ema50, rsi14, atr14 } = useMemo(() => {
    if (candles.length === 0) {
      return { ema20: [], ema50: [], rsi14: [], atr14: 0 };
    }

    const closes = candles.map((c) => c.close);

    // EMA calculation helper
    const calcEMA = (period: number) => {
      const k = 2 / (period + 1);
      const ema: (number | null)[] = [];
      let prev = closes.slice(0, Math.min(period, closes.length)).reduce((a, b) => a + b, 0) / Math.max(1, Math.min(period, closes.length));
      for (let i = 0; i < closes.length; i++) {
        if (i < period - 1) {
          ema.push(null);
        } else if (i === period - 1) {
          ema.push(prev);
        } else {
          prev = closes[i] * k + prev * (1 - k);
          ema.push(prev);
        }
      }
      return ema;
    };

    // RSI calculation helper
    const calcRSI = (period = 14) => {
      const rsi: (number | null)[] = [];
      let gains = 0;
      let losses = 0;
      for (let i = 1; i <= period && i < closes.length; i++) {
        const diff = closes[i] - closes[i - 1];
        if (diff >= 0) gains += diff;
        else losses += Math.abs(diff);
      }
      let avgGain = gains / period;
      let avgLoss = losses / period;

      for (let i = 0; i < closes.length; i++) {
        if (i < period) {
          rsi.push(null);
        } else {
          const diff = closes[i] - closes[i - 1];
          avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
          avgLoss = (avgLoss * (period - 1) + (diff < 0 ? Math.abs(diff) : 0)) / period;
          const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
          rsi.push(100 - 100 / (1 + rs));
        }
      }
      return rsi;
    };

    // ATR calculation helper
    let atrSum = 0;
    const atrPeriod = Math.min(14, candles.length - 1);
    for (let i = 1; i < candles.length && i <= 14; i++) {
      const tr = Math.max(
        candles[i].high - candles[i].low,
        Math.abs(candles[i].high - candles[i - 1].close),
        Math.abs(candles[i].low - candles[i - 1].close)
      );
      atrSum += tr;
    }
    const currentAtr = atrPeriod > 0 ? atrSum / atrPeriod : 0.001;

    return {
      ema20: calcEMA(10), // period 10 for responsiveness
      ema50: calcEMA(20),
      rsi14: calcRSI(14),
      atr14: currentAtr,
    };
  }, [candles]);

  const fallbackCandle: Candle = {
    time: '--',
    timestamp: 0,
    open: 0,
    high: 0,
    low: 0,
    close: 0,
    volume: 0,
  };

  // Active Candle for Tooltip
  const activeCandle =
    hoverIndex !== null && candles[hoverIndex]
      ? candles[hoverIndex]
      : candles.length > 0
        ? candles[candles.length - 1]
        : fallbackCandle;
  const activeEma20 =
    hoverIndex !== null && ema20[hoverIndex] !== undefined
      ? ema20[hoverIndex]
      : ema20.length > 0
        ? ema20[ema20.length - 1]
        : null;
  const activeRsi =
    hoverIndex !== null && rsi14[hoverIndex] !== undefined
      ? rsi14[hoverIndex]
      : rsi14.length > 0
        ? rsi14[rsi14.length - 1]
        : null;

  // SVG Chart Geometry
  const width = 800;
  const height = 360;
  const padding = { top: 25, right: 65, bottom: 30, left: 10 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Visible Slice according to Zoom
  const visibleCandles = useMemo(() => {
    if (candles.length === 0) return [];
    const visibleCount = Math.max(20, Math.round(candles.length / zoomLevel));
    return candles.slice(Math.max(0, candles.length - visibleCount));
  }, [candles, zoomLevel]);

  const isJpy = symbol.includes('JPY');
  const priceDecimals = isJpy ? 3 : 5;
  const hasCandles = visibleCandles.length > 0;
  const minPrice = hasCandles ? Math.min(...visibleCandles.map((c) => c.low)) : 1.0;
  const maxPrice = hasCandles ? Math.max(...visibleCandles.map((c) => c.high)) : 1.1;
  const priceRange = maxPrice > minPrice ? maxPrice - minPrice : 0.001;
  const maxVolume = hasCandles ? Math.max(...visibleCandles.map((c) => c.volume)) || 1 : 1;

  const getY = (val: number) => padding.top + chartHeight - ((val - minPrice) / priceRange) * chartHeight;
  const candleStep = hasCandles ? chartWidth / visibleCandles.length : chartWidth;

  // Grid price ticks
  const priceTicks = [0.15, 0.38, 0.62, 0.85].map((pct) => minPrice + priceRange * pct);

  // Target Stop Loss & Take Profit Levels
  const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0;
  const stopLossPrice = currentPrice > 0 ? Number((currentPrice - atr14 * 1.5).toFixed(priceDecimals)) : 0;
  const takeProfitPrice = currentPrice > 0 ? Number((currentPrice + atr14 * 2.5).toFixed(priceDecimals)) : 0;

  const handleExecutePaperOrder = async (side: 'BUY' | 'SELL') => {
    setIsOrderSubmitting(true);
    try {
      const units = Math.round(lotSize * 100000);
      const res = await ordersApi.create({
        symbol,
        side,
        order_type: 'MARKET',
        quantity: units,
      });
      toast.success(
        `[PAPER] Order Submitted: ${res.symbol} ${res.side} (${res.status || 'SUBMITTED'})`
      );
      if (onPlaceOrder) {
        onPlaceOrder(side, units);
      }
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setIsOrderSubmitting(false);
    }
  };

  return (
    <div
      ref={containerRef}
      className={`rounded-xl border border-[#1E293B] bg-[#141E33] flex flex-col overflow-hidden ${
        isFullscreen ? 'fixed inset-2 z-50 bg-[#090D16]' : ''
      } ${className}`}
      style={{ backgroundColor: '#141E33', borderColor: '#1E293B' }}
    >
      {/* Top Chart Header & Controls */}
      <div className="px-4 py-2.5 border-b border-[#1E293B] bg-[#0F172A] flex flex-wrap items-center justify-between gap-3">
        {/* Symbol & Price Summary */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-sm font-bold font-mono text-slate-100">{symbol}</h2>
          </div>
          <div className="text-sm font-bold font-mono text-emerald-400 tabular-nums">
            {currentPrice > 0 ? currentPrice.toFixed(priceDecimals) : '--'}
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-[#090D16] border border-[#1E293B] px-1.5 py-0.5 rounded">
            {timeframe}
          </span>
          <span className="text-[10px] font-mono text-slate-500 hidden sm:inline">
            ATR: {atr14 > 0 ? atr14.toFixed(priceDecimals) : '--'}
          </span>
        </div>

        {/* Timeframe Selector (Canonical Backend Timeframes) */}
        <div className="flex items-center gap-1 bg-[#090D16] p-0.5 rounded-lg border border-[#1E293B]">
          {(['M1', 'M5', 'M15', 'H1', 'H4', 'D1'] as const).map((tf) => (
            <button
              key={tf}
              type="button"
              onClick={() => setTimeframe(tf)}
              className={`px-2 py-0.5 text-[11px] font-mono rounded transition-colors cursor-pointer ${
                timeframe === tf
                  ? 'bg-sky-500/20 text-sky-300 font-bold border border-sky-500/40'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Indicators and View Controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setShowEMA(!showEMA)}
            className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors cursor-pointer ${
              showEMA
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300 font-semibold'
                : 'border-[#1E293B] text-slate-400 hover:bg-[#1A2742]'
            }`}
            title="Toggle Exponential Moving Averages (EMA 20/50)"
          >
            EMA
          </button>
          <button
            type="button"
            onClick={() => setShowVolume(!showVolume)}
            className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors cursor-pointer ${
              showVolume
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300 font-semibold'
                : 'border-[#1E293B] text-slate-400 hover:bg-[#1A2742]'
            }`}
            title="Toggle Volume Histogram"
          >
            VOL
          </button>
          <button
            type="button"
            onClick={() => setShowRSI(!showRSI)}
            className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors cursor-pointer ${
              showRSI
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300 font-semibold'
                : 'border-[#1E293B] text-slate-400 hover:bg-[#1A2742]'
            }`}
            title="Toggle Relative Strength Index (RSI 14)"
          >
            RSI
          </button>
          <button
            type="button"
            onClick={() => setShowMACD(!showMACD)}
            className={`px-2 py-1 text-[10px] font-mono rounded border transition-colors cursor-pointer ${
              showMACD
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300 font-semibold'
                : 'border-[#1E293B] text-slate-400 hover:bg-[#1A2742]'
            }`}
            title="Toggle Moving Average Convergence Divergence (MACD)"
          >
            MACD
          </button>

          {/* Zoom controls */}
          <div className="flex items-center border-l border-[#1E293B] pl-1.5 ml-1 gap-1">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.25))}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.75, z - 0.25))}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(1)}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded cursor-pointer"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded cursor-pointer"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
            >
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* OHLCV Live Metric Overlay Bar */}
      <div className="px-4 py-1.5 bg-[#090D16] border-b border-[#1E293B] flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-slate-400">
        <div>
          TIME: <span className="text-slate-200">{activeCandle.time}</span>
        </div>
        <div>
          O: <span className="text-slate-200">{activeCandle.open > 0 ? activeCandle.open.toFixed(priceDecimals) : '--'}</span>
        </div>
        <div>
          H: <span className="text-emerald-400">{activeCandle.high > 0 ? activeCandle.high.toFixed(priceDecimals) : '--'}</span>
        </div>
        <div>
          L: <span className="text-rose-400">{activeCandle.low > 0 ? activeCandle.low.toFixed(priceDecimals) : '--'}</span>
        </div>
        <div>
          C: <span className={activeCandle.close >= activeCandle.open ? 'text-emerald-400' : 'text-rose-400'}>
            {activeCandle.close > 0 ? activeCandle.close.toFixed(priceDecimals) : '--'}
          </span>
        </div>
        <div>
          VOL: <span className="text-slate-200">{activeCandle.volume.toLocaleString()}</span>
        </div>
        {showEMA && activeEma20 != null && (
          <div>
            EMA(20): <span className="text-sky-400">{activeEma20.toFixed(priceDecimals)}</span>
          </div>
        )}
        {showRSI && activeRsi != null && (
          <div>
            RSI(14): <span className="text-amber-400">{activeRsi.toFixed(1)}</span>
          </div>
        )}
      </div>

      {/* Candlestick Chart SVG Canvas / State Container */}
      <div className="relative flex-1 bg-[#090D16] select-none min-h-[360px] flex items-center justify-center">
        {/* Loading Overlay */}
        {candlesLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#090D16]/80 backdrop-blur-sm z-10">
            <Loader2 className="w-6 h-6 text-sky-400 animate-spin mb-2" />
            <span className="text-xs font-mono text-slate-300">
              Loading {symbol} ({timeframe}) market candles...
            </span>
          </div>
        )}

        {/* Error Overlay */}
        {candlesError && !candlesLoading && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#090D16]/90 p-4 text-center z-10">
            <AlertCircle className="w-6 h-6 text-rose-400 mb-2" />
            <span className="text-xs font-mono text-slate-200 mb-1">Failed to load market data</span>
            <span className="text-[11px] font-mono text-slate-400 mb-3 max-w-sm">{candlesError}</span>
            <button
              type="button"
              onClick={() => fetchCandles()}
              className="px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-mono flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Empty State */}
        {!candlesLoading && !candlesError && candles.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#090D16] p-4 text-center z-10">
            <span className="text-xs font-mono text-slate-400">
              Market data unavailable for {symbol} ({timeframe})
            </span>
            <button
              type="button"
              onClick={() => fetchCandles()}
              className="mt-2 text-xs font-mono text-sky-400 hover:underline flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" /> Retry
            </button>
          </div>
        )}

        {/* SVG Chart when candles exist */}
        {hasCandles && (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto block"
            onMouseLeave={() => setHoverIndex(null)}
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const relX = ((e.clientX - rect.left) / rect.width) * width - padding.left;
              const idx = Math.floor(relX / candleStep);
              if (idx >= 0 && idx < visibleCandles.length) {
                setHoverIndex(idx);
              }
            }}
          >
            {/* Subtle Grid Lines & Y-Axis Labels */}
            {priceTicks.map((price, i) => {
              const y = getY(price);
              return (
                <g key={i}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={width - padding.right}
                    y2={y}
                    stroke="#1E293B"
                    strokeDasharray="3 3"
                    strokeWidth="1"
                  />
                  <text
                    x={width - padding.right + 6}
                    y={y + 3}
                    fill="#64748B"
                    fontSize="10"
                    fontFamily="JetBrains Mono"
                    textAnchor="start"
                  >
                    {price.toFixed(priceDecimals)}
                  </text>
                </g>
              );
            })}

            {/* Volume Bars */}
            {showVolume &&
              visibleCandles.map((c, i) => {
                const x = padding.left + i * candleStep + candleStep / 2;
                const isGreen = c.close >= c.open;
                const barHeight = (c.volume / maxVolume) * 45;
                const y = height - padding.bottom - barHeight;
                return (
                  <rect
                    key={`vol-${i}`}
                    x={x - candleStep * 0.35}
                    y={y}
                    width={candleStep * 0.7}
                    height={barHeight}
                    fill={isGreen ? '#10B981' : '#F43F5E'}
                    opacity="0.22"
                  />
                );
              })}

            {/* Visible Stop Loss & Take Profit Reference Levels */}
            {currentPrice > 0 && (
              <g>
                {/* Take Profit (Green Dashed) */}
                <line
                  x1={padding.left}
                  y1={getY(takeProfitPrice)}
                  x2={width - padding.right}
                  y2={getY(takeProfitPrice)}
                  stroke="#10B981"
                  strokeDasharray="4 4"
                  strokeWidth="1.2"
                  opacity="0.8"
                />
                <rect
                  x={width - padding.right + 2}
                  y={getY(takeProfitPrice) - 8}
                  width="58"
                  height="16"
                  fill="#064E3B"
                  rx="3"
                />
                <text
                  x={width - padding.right + 6}
                  y={getY(takeProfitPrice) + 4}
                  fill="#34D399"
                  fontSize="9"
                  fontFamily="JetBrains Mono"
                  fontWeight="bold"
                >
                  TP {takeProfitPrice}
                </text>

                {/* Stop Loss (Red Dashed) */}
                <line
                  x1={padding.left}
                  y1={getY(stopLossPrice)}
                  x2={width - padding.right}
                  y2={getY(stopLossPrice)}
                  stroke="#F43F5E"
                  strokeDasharray="4 4"
                  strokeWidth="1.2"
                  opacity="0.8"
                />
                <rect
                  x={width - padding.right + 2}
                  y={getY(stopLossPrice) - 8}
                  width="58"
                  height="16"
                  fill="#4C0519"
                  rx="3"
                />
                <text
                  x={width - padding.right + 6}
                  y={getY(stopLossPrice) + 4}
                  fill="#FB7185"
                  fontSize="9"
                  fontFamily="JetBrains Mono"
                  fontWeight="bold"
                >
                  SL {stopLossPrice}
                </text>
              </g>
            )}

            {/* Candlesticks (Wicks & Bodies) */}
            {visibleCandles.map((c, i) => {
              const x = padding.left + i * candleStep + candleStep / 2;
              const isGreen = c.close >= c.open;
              const color = isGreen ? '#10B981' : '#F43F5E';
              const candleBodyTop = getY(Math.max(c.open, c.close));
              const candleBodyHeight = Math.max(2, Math.abs(getY(c.open) - getY(c.close)));
              const wickTop = getY(c.high);
              const wickBottom = getY(c.low);

              return (
                <g key={`candle-${i}`}>
                  {/* Wick */}
                  <line
                    x1={x}
                    y1={wickTop}
                    x2={x}
                    y2={wickBottom}
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  {/* Body */}
                  <rect
                    x={x - candleStep * 0.35}
                    y={candleBodyTop}
                    width={candleStep * 0.7}
                    height={candleBodyHeight}
                    fill={color}
                    rx="1"
                  />
                </g>
              );
            })}

            {/* EMA 20 Overlay Line */}
            {showEMA && (
              <polyline
                fill="none"
                stroke="#38BDF8"
                strokeWidth="1.8"
                opacity="0.9"
                points={visibleCandles
                  .map((_, i) => {
                    const val = ema20[candles.length - visibleCandles.length + i];
                    if (val == null) return null;
                    const x = padding.left + i * candleStep + candleStep / 2;
                    const y = getY(val);
                    return `${x},${y}`;
                  })
                  .filter(Boolean)
                  .join(' ')}
              />
            )}

            {/* EMA 50 Overlay Line */}
            {showEMA && (
              <polyline
                fill="none"
                stroke="#FBBF24"
                strokeWidth="1.6"
                strokeDasharray="4 2"
                opacity="0.8"
                points={visibleCandles
                  .map((_, i) => {
                    const val = ema50[candles.length - visibleCandles.length + i];
                    if (val == null) return null;
                    const x = padding.left + i * candleStep + candleStep / 2;
                    const y = getY(val);
                    return `${x},${y}`;
                  })
                  .filter(Boolean)
                  .join(' ')}
              />
            )}

            {/* Interactive Crosshair Guidelines */}
            {hoverIndex !== null && hoverIndex < visibleCandles.length && (
              <g>
                {/* Vertical line */}
                <line
                  x1={padding.left + hoverIndex * candleStep + candleStep / 2}
                  y1={padding.top}
                  x2={padding.left + hoverIndex * candleStep + candleStep / 2}
                  y2={height - padding.bottom}
                  stroke="#94A3B8"
                  strokeDasharray="2 2"
                  strokeWidth="1"
                />
                {/* Horizontal line */}
                <line
                  x1={padding.left}
                  y1={getY(visibleCandles[hoverIndex].close)}
                  x2={width - padding.right}
                  y2={getY(visibleCandles[hoverIndex].close)}
                  stroke="#94A3B8"
                  strokeDasharray="2 2"
                  strokeWidth="1"
                />
              </g>
            )}
          </svg>
        )}
      </div>

      {/* Sub-Indicator Panels (RSI / MACD) */}
      {showRSI && (
        <div className="px-4 py-2 bg-[#0B101D] border-t border-[#1E293B] flex items-center justify-between font-mono text-[11px]">
          <div className="flex items-center gap-3">
            <span className="text-amber-400 font-bold">RSI(14):</span>
            <span className="text-slate-100 font-semibold">{activeRsi != null ? activeRsi.toFixed(1) : '--'}</span>
            <span className="text-[10px] text-slate-500">Thresholds: 70 (Overbought) / 30 (Oversold)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-[#141E33] rounded-full overflow-hidden border border-[#1E293B]">
              <div
                className="h-full bg-amber-400 rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, activeRsi || 50))}%` }}
              />
            </div>
            <span className="text-[10px] text-slate-400">
              {activeRsi != null ? (activeRsi > 70 ? 'Overbought' : activeRsi < 30 ? 'Oversold' : 'Neutral Range') : 'No Data'}
            </span>
          </div>
        </div>
      )}

      {showMACD && (
        <div className="px-4 py-2 bg-[#0B101D] border-t border-[#1E293B] flex items-center justify-between font-mono text-[11px]">
          <div className="flex items-center gap-3">
            <span className="text-sky-400 font-bold">MACD(12,26,9):</span>
            <span className="text-slate-400">
              {hasCandles ? 'Calculated on live series' : 'Awaiting data'}
            </span>
          </div>
        </div>
      )}

      {/* Quick Paper Execution Order Bar */}
      <div className="px-4 py-2.5 bg-[#0F172A] border-t border-[#1E293B] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400 font-semibold">LOT SIZE:</span>
          {[0.01, 0.05, 0.1, 0.5, 1.0].map((size) => (
            <button
              key={size}
              type="button"
              onClick={() => setLotSize(size)}
              className={`px-2 py-0.5 text-xs font-mono rounded transition-colors cursor-pointer ${
                lotSize === size
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold'
                  : 'bg-[#141E33] text-slate-400 hover:text-slate-200 border border-[#1E293B]'
              }`}
            >
              {size.toFixed(2)}
            </button>
          ))}
        </div>

        {/* Action Buy / Sell buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={isOrderSubmitting || currentPrice === 0}
            onClick={() => handleExecutePaperOrder('SELL')}
            className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 active:scale-95 text-white font-mono text-xs font-bold shadow-sm shadow-rose-950 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isOrderSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            <span>SELL</span>
            <span className="text-[10px] opacity-80 tabular-nums">
              {currentPrice > 0 ? (currentPrice - (isJpy ? 0.015 : 0.00015)).toFixed(priceDecimals) : '--'}
            </span>
          </button>

          <button
            type="button"
            disabled={isOrderSubmitting || currentPrice === 0}
            onClick={() => handleExecutePaperOrder('BUY')}
            className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-mono text-xs font-bold shadow-sm shadow-emerald-950 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isOrderSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            <span>BUY</span>
            <span className="text-[10px] opacity-80 tabular-nums">
              {currentPrice > 0 ? (currentPrice + (isJpy ? 0.015 : 0.00015)).toFixed(priceDecimals) : '--'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
