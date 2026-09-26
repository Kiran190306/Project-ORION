import React, { useState, useMemo, useRef } from 'react';
import {
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';
import { useToast } from '../common/Toast';

export interface Candle {
  time: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

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
  const [timeframe, setTimeframe] = useState<'1m' | '5m' | '15m' | '1h' | '4h' | '1d'>('1h');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showEMA, setShowEMA] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showRSI, setShowRSI] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [lotSize, setLotSize] = useState<number>(0.1);
  const [isOrderSubmitting, setIsOrderSubmitting] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  // Generate realistic OHLCV price series anchored to current symbol base price
  const candles: Candle[] = useMemo(() => {
    const isJpy = symbol.includes('JPY');
    const basePrice = isJpy ? 155.20 : symbol.includes('GBP') ? 1.2710 : symbol.includes('AUD') ? 0.6540 : 1.0850;
    const volatility = isJpy ? 0.25 : 0.0018;

    const data: Candle[] = [];
    let currentPrice = basePrice - volatility * 12;
    const now = Date.now();
    const intervalMinutes = timeframe === '1m' ? 1 : timeframe === '5m' ? 5 : timeframe === '15m' ? 15 : timeframe === '1h' ? 60 : timeframe === '4h' ? 240 : 1440;
    const count = 52;

    for (let i = 0; i < count; i++) {
      const timeMs = now - (count - i) * intervalMinutes * 60 * 1000;
      const d = new Date(timeMs);
      const timeStr = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;

      // Pseudo-random walk with trend momentum
      const trend = Math.sin(i / 6) * volatility * 0.45;
      const noise = (Math.sin(i * 1.7) * 0.5 + Math.cos(i * 0.9) * 0.5) * volatility;
      const open = currentPrice;
      const close = open + trend + noise;
      const high = Math.max(open, close) + Math.abs(Math.sin(i * 2.3)) * volatility * 0.6;
      const low = Math.min(open, close) - Math.abs(Math.cos(i * 1.9)) * volatility * 0.6;
      const volume = Math.round(5000 + Math.abs(Math.sin(i * 0.8)) * 12000);

      data.push({
        time: timeStr,
        timestamp: timeMs,
        open: Number(open.toFixed(isJpy ? 3 : 5)),
        high: Number(high.toFixed(isJpy ? 3 : 5)),
        low: Number(low.toFixed(isJpy ? 3 : 5)),
        close: Number(close.toFixed(isJpy ? 3 : 5)),
        volume,
      });

      currentPrice = close;
    }
    return data;
  }, [symbol, timeframe]);

  // Compute Technical Indicators: EMA 20, EMA 50, RSI 14, ATR 14
  const { ema20, ema50, rsi14, atr14 } = useMemo(() => {
    const closes = candles.map((c) => c.close);

    // EMA calculation helper
    const calcEMA = (period: number) => {
      const k = 2 / (period + 1);
      const ema: (number | null)[] = [];
      let prev = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
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
    for (let i = 1; i < candles.length && i <= 14; i++) {
      const tr = Math.max(
        candles[i].high - candles[i].low,
        Math.abs(candles[i].high - candles[i - 1].close),
        Math.abs(candles[i].low - candles[i - 1].close)
      );
      atrSum += tr;
    }
    const currentAtr = atrSum / Math.min(14, candles.length - 1);

    return {
      ema20: calcEMA(10), // using period 10 for 50-candle series responsiveness
      ema50: calcEMA(20),
      rsi14: calcRSI(14),
      atr14: currentAtr,
    };
  }, [candles]);

  // Active Candle for Tooltip
  const activeCandle = hoverIndex !== null && candles[hoverIndex] ? candles[hoverIndex] : candles[candles.length - 1];
  const activeEma20 = hoverIndex !== null && ema20[hoverIndex] ? ema20[hoverIndex] : ema20[ema20.length - 1];
  const activeRsi = hoverIndex !== null && rsi14[hoverIndex] ? rsi14[hoverIndex] : rsi14[rsi14.length - 1];

  // SVG Chart Geometry
  const width = 800;
  const height = 360;
  const padding = { top: 25, right: 65, bottom: 30, left: 10 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Visible Slice according to Zoom
  const visibleCandles = useMemo(() => {
    const visibleCount = Math.max(20, Math.round(candles.length / zoomLevel));
    return candles.slice(candles.length - visibleCount);
  }, [candles, zoomLevel]);

  const minPrice = Math.min(...visibleCandles.map((c) => c.low));
  const maxPrice = Math.max(...visibleCandles.map((c) => c.high));
  const priceRange = maxPrice - minPrice || 1;
  const maxVolume = Math.max(...visibleCandles.map((c) => c.volume)) || 1;

  const getY = (val: number) => padding.top + chartHeight - ((val - minPrice) / priceRange) * chartHeight;
  const candleStep = chartWidth / visibleCandles.length;

  // Grid price ticks
  const priceTicks = [0.15, 0.38, 0.62, 0.85].map((pct) => minPrice + priceRange * pct);

  // Target Stop Loss & Take Profit Levels
  const currentPrice = candles[candles.length - 1]?.close || 1.0850;
  const stopLossPrice = Number((currentPrice - atr14 * 1.5).toFixed(symbol.includes('JPY') ? 3 : 5));
  const takeProfitPrice = Number((currentPrice + atr14 * 2.5).toFixed(symbol.includes('JPY') ? 3 : 5));

  const handleExecutePaperOrder = (side: 'BUY' | 'SELL') => {
    setIsOrderSubmitting(true);
    setTimeout(() => {
      setIsOrderSubmitting(false);
      toast.success(`[PAPER] Simulated ${side} Order Filled: ${lotSize} Lots ${symbol} @ ${currentPrice}`);
      if (onPlaceOrder) {
        onPlaceOrder(side, lotSize * 100000);
      }
    }, 400);
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
            {currentPrice.toFixed(symbol.includes('JPY') ? 3 : 5)}
          </div>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded">
            +0.32%
          </span>
          <span className="text-[10px] font-mono text-slate-500 hidden sm:inline">
            ATR: {atr14.toFixed(symbol.includes('JPY') ? 3 : 5)}
          </span>
        </div>

        {/* Timeframe Selector */}
        <div className="flex items-center gap-1 bg-[#090D16] p-0.5 rounded-lg border border-[#1E293B]">
          {(['1m', '5m', '15m', '1h', '4h', '1d'] as const).map((tf) => (
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
              {tf.toUpperCase()}
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
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.75, z - 0.25))}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setZoomLevel(1)}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded"
              title="Reset Zoom"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1 text-slate-400 hover:text-slate-200 hover:bg-[#1A2742] rounded"
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
          O: <span className="text-slate-200">{activeCandle.open}</span>
        </div>
        <div>
          H: <span className="text-emerald-400">{activeCandle.high}</span>
        </div>
        <div>
          L: <span className="text-rose-400">{activeCandle.low}</span>
        </div>
        <div>
          C: <span className={activeCandle.close >= activeCandle.open ? 'text-emerald-400' : 'text-rose-400'}>{activeCandle.close}</span>
        </div>
        <div>
          VOL: <span className="text-slate-200">{activeCandle.volume.toLocaleString()}</span>
        </div>
        {showEMA && activeEma20 && (
          <div>
            EMA(20): <span className="text-sky-400">{activeEma20.toFixed(symbol.includes('JPY') ? 3 : 5)}</span>
          </div>
        )}
        {showRSI && activeRsi && (
          <div>
            RSI(14): <span className="text-amber-400">{activeRsi.toFixed(1)}</span>
          </div>
        )}
      </div>

      {/* Interactive Candlestick Chart SVG Canvas */}
      <div className="relative flex-1 bg-[#090D16] select-none">
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
                  {price.toFixed(symbol.includes('JPY') ? 3 : 5)}
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
                  fill={isGreen ? '#10B981' : '#F43F5E'}
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

          {/* Strategy Signal Marker on Recent Setup Candle */}
          {visibleCandles.length > 5 && (
            <g transform={`translate(${padding.left + (visibleCandles.length - 4) * candleStep + candleStep / 2}, ${getY(visibleCandles[visibleCandles.length - 4].low) + 18})`}>
              <path d="M 0 -8 L 6 2 L -6 2 Z" fill="#38BDF8" />
              <rect x="-38" y="4" width="76" height="14" rx="2" fill="#0C4A6E" stroke="#0284C7" strokeWidth="0.8" />
              <text x="0" y="14" fill="#E0F2FE" fontSize="8" fontFamily="JetBrains Mono" fontWeight="bold" textAnchor="middle">
                ▲ ORION SIGNAL
              </text>
            </g>
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
      </div>

      {/* Sub-Indicator Panels (RSI / MACD) */}
      {showRSI && (
        <div className="px-4 py-2 bg-[#0B101D] border-t border-[#1E293B] flex items-center justify-between font-mono text-[11px]">
          <div className="flex items-center gap-3">
            <span className="text-amber-400 font-bold">RSI(14):</span>
            <span className="text-slate-100 font-semibold">{activeRsi ? activeRsi.toFixed(1) : '56.4'}</span>
            <span className="text-[10px] text-slate-500">Thresholds: 70 (Overbought) / 30 (Oversold)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-[#141E33] rounded-full overflow-hidden border border-[#1E293B]">
              <div
                className="h-full bg-amber-400 rounded-full transition-all"
                style={{ width: `${Math.min(100, Math.max(0, activeRsi || 50))}%` }}
              />
            </div>
            <span className="text-[10px] text-slate-400">Neutral Range</span>
          </div>
        </div>
      )}

      {showMACD && (
        <div className="px-4 py-2 bg-[#0B101D] border-t border-[#1E293B] flex items-center justify-between font-mono text-[11px]">
          <div className="flex items-center gap-3">
            <span className="text-sky-400 font-bold">MACD(12,26,9):</span>
            <span className="text-emerald-400 font-semibold">+0.00034</span>
            <span className="text-slate-400">Signal: +0.00021</span>
            <span className="text-emerald-400 font-bold">Hist: +0.00013 (Bullish Expansion)</span>
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
            disabled={isOrderSubmitting}
            onClick={() => handleExecutePaperOrder('SELL')}
            className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 active:scale-95 text-white font-mono text-xs font-bold shadow-sm shadow-rose-950 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <span>SELL</span>
            <span className="text-[10px] opacity-80 tabular-nums">
              {(currentPrice - 0.00015).toFixed(symbol.includes('JPY') ? 3 : 5)}
            </span>
          </button>

          <button
            type="button"
            disabled={isOrderSubmitting}
            onClick={() => handleExecutePaperOrder('BUY')}
            className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-mono text-xs font-bold shadow-sm shadow-emerald-950 transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <span>BUY</span>
            <span className="text-[10px] opacity-80 tabular-nums">
              {(currentPrice + 0.00015).toFixed(symbol.includes('JPY') ? 3 : 5)}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};
