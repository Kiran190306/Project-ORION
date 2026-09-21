import React from 'react';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl border border-slate-800/80 bg-slate-900/40 p-8 text-center flex flex-col items-center justify-center max-w-md mx-auto my-6 ${className}`}
      style={{ backgroundColor: '#0e1626', borderColor: '#1e293b' }}
    >
      <div className="w-12 h-12 rounded-full bg-slate-800/70 border border-slate-700/60 flex items-center justify-center text-slate-400 mb-3">
        {icon || <Inbox className="w-6 h-6 text-slate-400" />}
      </div>
      <h3 className="text-sm font-semibold text-slate-200 font-mono tracking-wide mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-xs text-slate-400 mb-4 max-w-xs leading-relaxed">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
};
