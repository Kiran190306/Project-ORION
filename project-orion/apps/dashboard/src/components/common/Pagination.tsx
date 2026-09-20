import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onOffsetChange: (newOffset: number) => void;
  className?: string;
}

export const Pagination: React.FC<PaginationProps> = ({
  total,
  limit,
  offset,
  onOffsetChange,
  className = '',
}) => {
  if (total <= limit) {
    return null;
  }

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  const handlePrev = () => {
    onOffsetChange(Math.max(0, offset - limit));
  };

  const handleNext = () => {
    if (offset + limit < total) {
      onOffsetChange(offset + limit);
    }
  };

  return (
    <div
      className={`flex items-center justify-between gap-4 py-3 px-1 text-xs text-slate-400 font-mono ${className}`}
    >
      <div>
        Showing <span className="font-semibold text-slate-200">{offset + 1}</span> to{' '}
        <span className="font-semibold text-slate-200">{Math.min(offset + limit, total)}</span> of{' '}
        <span className="font-semibold text-slate-200">{total}</span> entries
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrev}
          disabled={offset === 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Prev</span>
        </Button>
        <span className="px-2 text-slate-300">
          Page {currentPage} of {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={handleNext}
          disabled={offset + limit >= total}
          aria-label="Next page"
        >
          <span>Next</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
};
