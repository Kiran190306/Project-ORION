import React from 'react';

export interface Column<T> {
  header: React.ReactNode;
  accessor?: keyof T;
  render?: (item: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: React.ReactNode;
  keyExtractor: (item: T, index: number) => string;
  className?: string;
}

export function Table<T>({
  columns,
  data,
  isLoading = false,
  emptyMessage = 'No records found.',
  keyExtractor,
  className = '',
}: TableProps<T>): React.ReactElement {
  return (
    <div className={`w-full overflow-x-auto rounded-lg border border-slate-800 ${className}`}>
      <table className="w-full text-left text-sm border-collapse">
        <thead className="bg-slate-900/90 text-xs uppercase tracking-wider text-slate-400 font-mono border-b border-slate-800">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                scope="col"
                className={`px-4 py-3 font-semibold ${col.headerClassName || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 bg-slate-950/40">
          {isLoading ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">
                <div className="inline-flex items-center gap-2.5">
                  <span className="w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                  <span>Loading trading data...</span>
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item, rowIdx) => (
              <tr
                key={keyExtractor(item, rowIdx)}
                className="hover:bg-slate-800/30 transition-colors"
              >
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className={`px-4 py-3 text-slate-200 ${col.className || ''}`}>
                    {col.render
                      ? col.render(item, rowIdx)
                      : col.accessor
                      ? String(item[col.accessor] ?? '—')
                      : '—'}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
