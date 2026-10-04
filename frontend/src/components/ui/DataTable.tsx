import React from 'react';
import { cn } from '../../lib/utils';

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
  className?: string;
}

export function DataTable<T>({ data, columns, onRowClick, emptyState, className }: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return (
      <div className={cn('flex items-center justify-center p-8 border border-border rounded-lg text-muted bg-surface/50', className)}>
        {emptyState || 'No data available.'}
      </div>
    );
  }

  return (
    <div className={cn('w-full overflow-auto border border-border rounded-lg bg-surface', className)}>
      <table className='w-full text-sm text-left'>
        <thead className='bg-raised text-muted uppercase tracking-wider text-[10px] font-semibold border-b border-border'>
          <tr>
            {columns.map((col, idx) => (
              <th key={col.key || idx} className={cn('px-4 py-3', col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className='divide-y divide-border'>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              onClick={() => onRowClick?.(row)}
              className={cn(
                'group hover:bg-raised/50 transition-colors',
                rowIndex % 2 === 0 ? 'bg-transparent' : 'bg-surface/30',
                onRowClick && 'cursor-pointer'
              )}
            >
              {columns.map((col, colIndex) => (
                <td key={col.key || colIndex} className={cn('px-4 py-3', col.className)}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
