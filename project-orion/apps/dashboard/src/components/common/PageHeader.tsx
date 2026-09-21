import React from 'react';
import { Breadcrumbs, BreadcrumbItem } from './Breadcrumbs';
import { PaperTradingBadge } from './Badge';

export interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  showPaperBadge?: boolean;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs,
  actions,
  showPaperBadge = true,
  className = '',
}) => {
  return (
    <div
      className={`pb-5 mb-6 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 ${className}`}
      style={{ borderColor: '#1e293b' }}
    >
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div className="mb-2">
            <Breadcrumbs items={breadcrumbs} />
          </div>
        )}
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono">
            {title}
          </h1>
          {showPaperBadge && <PaperTradingBadge size="sm" />}
        </div>
        {subtitle && (
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2.5 flex-wrap flex-shrink-0">
          {actions}
        </div>
      )}
    </div>
  );
};
