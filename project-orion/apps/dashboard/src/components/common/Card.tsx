import React from 'react';

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  footer?: React.ReactNode;
  badge?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  footer,
  badge,
  children,
  className = '',
  style,
  ...rest
}) => {
  return (
    <div
      className={`rounded-xl border border-slate-800 bg-[#141E33] shadow-md backdrop-blur-sm overflow-hidden flex flex-col transition-colors duration-150 ${className}`}
      style={{
        backgroundColor: '#141E33',
        borderColor: '#1E293B',
        ...style,
      }}
      {...rest}
    >
      {(title || subtitle || action || badge) && (
        <div
          className="px-5 py-4 border-b border-slate-800 flex items-center justify-between gap-4 flex-wrap"
          style={{ borderColor: '#1e293b' }}
        >
          <div className="flex items-center gap-2.5">
            {title && (
              <h3 className="text-sm font-semibold tracking-wide text-slate-100 flex items-center gap-2">
                {title}
              </h3>
            )}
            {badge && <div>{badge}</div>}
            {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className="p-5 flex-1">{children}</div>
      {footer && (
        <div
          className="px-5 py-3 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400"
          style={{ borderColor: '#1e293b' }}
        >
          {footer}
        </div>
      )}
    </div>
  );
};
