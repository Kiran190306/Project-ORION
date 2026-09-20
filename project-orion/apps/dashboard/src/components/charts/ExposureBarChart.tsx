import React from 'react';
import type { CurrencyExposure } from '../../api/types';
import { formatCurrency } from '../../utils/formatters';

interface ExposureBarChartProps {
  exposures: CurrencyExposure[];
  className?: string;
}

export const ExposureBarChart: React.FC<ExposureBarChartProps> = ({
  exposures,
  className = '',
}) => {
  if (!exposures || exposures.length === 0) {
    return (
      <div className="py-8 text-center text-xs text-slate-500 font-mono">
        No active currency exposures.
      </div>
    );
  }

  // Calculate max exposure for bar scaling
  const maxAbsExposure = Math.max(
    ...exposures.map((e) => {
      const net = Math.abs(typeof e.net_exposure === 'string' ? parseFloat(e.net_exposure) : e.net_exposure);
      return isNaN(net) ? 0 : net;
    }),
    1000
  );

  return (
    <div className={`flex flex-col gap-3 font-mono text-xs ${className}`}>
      {exposures.map((item) => {
        const netNum = typeof item.net_exposure === 'string' ? parseFloat(item.net_exposure) : item.net_exposure;
        const net = isNaN(netNum) ? 0 : netNum;
        const widthPct = Math.min(100, Math.max(5, (Math.abs(net) / maxAbsExposure) * 100));
        const isLong = net >= 0;

        return (
          <div key={item.currency} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-slate-300">
              <span className="font-semibold">{item.currency}</span>
              <span className={isLong ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                {isLong ? '+' : ''}
                {formatCurrency(net, item.currency, 0)} ({item.position_count} pos)
              </span>
            </div>
            <div className="w-full h-3 bg-slate-950/80 rounded-full border border-slate-800 overflow-hidden flex">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isLong ? 'bg-emerald-500/80' : 'bg-rose-500/80'
                }`}
                style={{ width: `${widthPct}%` }}
                role="progressbar"
                aria-valuenow={net}
                aria-valuemin={-maxAbsExposure}
                aria-valuemax={maxAbsExposure}
                aria-label={`${item.currency} net exposure`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
