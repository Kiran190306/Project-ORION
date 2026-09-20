import React from 'react';
import { formatCurrency, formatPercent } from '../../utils/formatters';

interface EquityCurveChartProps {
  balance: string | number;
  equity: string | number;
  peakEquity: string | number;
  drawdownPct: number;
  currency?: string;
  className?: string;
}

export const EquityCurveChart: React.FC<EquityCurveChartProps> = ({
  balance,
  equity,
  peakEquity,
  drawdownPct,
  currency = 'USD',
  className = '',
}) => {
  const balNum = typeof balance === 'string' ? parseFloat(balance) : balance;
  const eqNum = typeof equity === 'string' ? parseFloat(equity) : equity;
  const peakNum = typeof peakEquity === 'string' ? parseFloat(peakEquity) : peakEquity;

  const validBal = isNaN(balNum) ? 100000 : balNum;
  const validEq = isNaN(eqNum) ? validBal : eqNum;
  const validPeak = isNaN(peakNum) ? Math.max(validBal, validEq) : Math.max(peakNum, validEq);

  // Generate a representative smooth SVG path based on balance -> peak -> current equity
  // 6 points over time: [T0, T1, T2, T3, T4, T5]
  const p0 = validBal;
  const p1 = validBal + (validPeak - validBal) * 0.35;
  const p2 = validBal + (validPeak - validBal) * 0.7;
  const p3 = validPeak;
  const p4 = validPeak - (validPeak - validEq) * 0.5;
  const p5 = validEq;

  const points = [p0, p1, p2, p3, p4, p5];
  const minVal = Math.min(...points) * 0.995;
  const maxVal = Math.max(...points) * 1.005;
  const range = maxVal - minVal || 1;

  const width = 500;
  const height = 180;
  const padding = 20;

  const getX = (index: number) => padding + (index / (points.length - 1)) * (width - 2 * padding);
  const getY = (val: number) => height - padding - ((val - minVal) / range) * (height - 2 * padding);

  const pathCoordinates = points.map((p, idx) => `${getX(idx)},${getY(p)}`).join(' L ');
  const areaPath = `M ${getX(0)},${height - padding} L ${pathCoordinates} L ${getX(
    points.length - 1
  )},${height - padding} Z`;

  const peakY = getY(validPeak);

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex items-center justify-between text-xs font-mono text-slate-400">
        <div>
          Current Drawdown:{' '}
          <span className={drawdownPct > 0 ? 'text-rose-400 font-semibold' : 'text-slate-200'}>
            {formatPercent(-Math.abs(drawdownPct))}
          </span>
        </div>
        <div>
          Peak Equity: <span className="text-slate-200">{formatCurrency(validPeak, currency)}</span>
        </div>
      </div>

      <div className="relative w-full rounded-lg bg-slate-950/60 p-2 border border-slate-800/80 overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-44 overflow-visible"
          role="img"
          aria-label={`Equity curve chart showing current equity ${formatCurrency(
            validEq,
            currency
          )} and peak equity ${formatCurrency(validPeak, currency)}`}
        >
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0284c7" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#0284c7" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={padding}
            y1={padding}
            x2={width - padding}
            y2={padding}
            stroke="#334155"
            strokeDasharray="3 3"
            strokeWidth="0.75"
          />
          <line
            x1={padding}
            y1={height / 2}
            x2={width - padding}
            y2={height / 2}
            stroke="#1e293b"
            strokeWidth="0.75"
          />
          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="#334155"
            strokeWidth="0.75"
          />

          {/* Peak equity line */}
          <line
            x1={padding}
            y1={peakY}
            x2={width - padding}
            y2={peakY}
            stroke="#f59e0b"
            strokeDasharray="4 4"
            strokeWidth="1.2"
          />

          {/* Area fill */}
          <path d={areaPath} fill="url(#equityGradient)" />

          {/* Line curve */}
          <path
            d={`M ${pathCoordinates}`}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Current point */}
          <circle
            cx={getX(points.length - 1)}
            cy={getY(validEq)}
            r="4.5"
            fill="#38bdf8"
            stroke="#090d16"
            strokeWidth="2"
          />
        </svg>

        {/* Accessible screen-reader fallback table */}
        <div className="sr-only">
          <table>
            <caption>Equity Curve Summary Data</caption>
            <thead>
              <tr>
                <th scope="col">Metric</th>
                <th scope="col">Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Starting Balance</td>
                <td>{formatCurrency(validBal, currency)}</td>
              </tr>
              <tr>
                <td>Peak Equity</td>
                <td>{formatCurrency(validPeak, currency)}</td>
              </tr>
              <tr>
                <td>Current Equity</td>
                <td>{formatCurrency(validEq, currency)}</td>
              </tr>
              <tr>
                <td>Current Drawdown</td>
                <td>{formatPercent(drawdownPct)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
