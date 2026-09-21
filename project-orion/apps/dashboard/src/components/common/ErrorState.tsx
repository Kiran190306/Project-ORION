import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  correlationId?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to Load Data',
  message,
  correlationId,
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`rounded-xl border border-rose-900/40 bg-rose-950/20 p-6 text-center max-w-lg mx-auto my-6 ${className}`}
      role="alert"
    >
      <div className="w-10 h-10 rounded-full bg-rose-900/30 border border-rose-800/50 flex items-center justify-center text-rose-400 mx-auto mb-3">
        <AlertTriangle className="w-5 h-5" />
      </div>

      <h3 className="text-sm font-semibold text-rose-200 font-mono tracking-wide mb-1">
        {title}
      </h3>
      <p className="text-xs text-rose-300/80 mb-3 leading-relaxed">
        {message}
      </p>

      {correlationId && (
        <p className="text-[10px] text-slate-400 font-mono mb-4">
          Ref ID: <span className="text-slate-300">{correlationId}</span>
        </p>
      )}

      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="inline-flex items-center gap-2 border-rose-800/60 text-rose-300 hover:bg-rose-900/40 cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </Button>
      )}
    </div>
  );
};
