import React from 'react';

export type BadgeVariant =
  | 'default'
  | 'success'
  | 'danger'
  | 'warning'
  | 'info'
  | 'paper'
  | 'buy'
  | 'sell';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  dot = false,
  children,
  className = '',
  ...rest
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    success: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60',
    danger: 'bg-rose-950/60 text-rose-400 border-rose-800/60',
    warning: 'bg-amber-950/60 text-amber-400 border-amber-800/60',
    info: 'bg-sky-950/60 text-sky-400 border-sky-800/60',
    paper: 'bg-amber-500/10 text-amber-400 border-amber-500/30 font-bold',
    buy: 'bg-emerald-950/70 text-emerald-300 border-emerald-700/60 font-semibold',
    sell: 'bg-rose-950/70 text-rose-300 border-rose-700/60 font-semibold',
  };

  const dotColors: Record<BadgeVariant, string> = {
    default: 'bg-slate-400',
    success: 'bg-emerald-400',
    danger: 'bg-rose-400',
    warning: 'bg-amber-400',
    info: 'bg-sky-400',
    paper: 'bg-amber-400',
    buy: 'bg-emerald-400',
    sell: 'bg-rose-400',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs border uppercase tracking-wider font-mono ${variantStyles[variant]} ${className}`}
      {...rest}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
};

export const PaperTradingBadge: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5 font-bold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/40 uppercase tracking-widest font-mono font-bold shadow-sm shadow-amber-950/30 ${sizeClasses[size]}`}
      role="status"
      aria-label="Trading Environment: Paper Trading"
    >
      <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
      PAPER TRADING ONLY
    </span>
  );
};
