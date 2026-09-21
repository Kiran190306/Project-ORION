import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string | number;
  changeDirection?: 'up' | 'down' | 'neutral';
  changeLabel?: string;
  subValue?: string;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
  tooltip?: string;
  variant?: 'default' | 'profit' | 'loss' | 'warning' | 'brand';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  change,
  changeDirection,
  changeLabel,
  subValue,
  badge,
  icon,
  tooltip,
  variant = 'default',
  className = '',
}) => {
  const valueColor = {
    default: 'text-slate-100',
    profit: 'text-emerald-400',
    loss: 'text-rose-400',
    warning: 'text-amber-400',
    brand: 'text-sky-400',
  }[variant];

  return (
    <div
      className={`rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm backdrop-blur-xs flex flex-col justify-between transition-all hover:border-slate-700/80 ${className}`}
      style={{ backgroundColor: '#111927', borderColor: '#1e293b' }}
      title={tooltip}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400 font-mono">
          {label}
        </span>
        <div className="flex items-center gap-1.5">
          {badge}
          {icon && <div className="text-slate-400">{icon}</div>}
        </div>
      </div>

      <div className="my-1">
        <div className={`text-2xl font-bold tracking-tight font-mono ${valueColor}`}>
          {value}
        </div>
        {subValue && (
          <p className="text-xs text-slate-400 mt-0.5 font-mono">{subValue}</p>
        )}
      </div>

      {(change !== undefined || changeLabel) && (
        <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center gap-1.5 text-xs font-mono">
          {changeDirection === 'up' && (
            <TrendingUp className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
          )}
          {changeDirection === 'down' && (
            <TrendingDown className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
          )}
          {changeDirection === 'neutral' && (
            <Minus className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          )}

          {change !== undefined && (
            <span
              className={
                changeDirection === 'up'
                  ? 'text-emerald-400 font-semibold'
                  : changeDirection === 'down'
                  ? 'text-rose-400 font-semibold'
                  : 'text-slate-400'
              }
            >
              {change}
            </span>
          )}
          {changeLabel && <span className="text-slate-400">{changeLabel}</span>}
        </div>
      )}
    </div>
  );
};
