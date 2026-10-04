import React, { useMemo, useState } from 'react';
import { cn } from '../../lib/utils';
import type { EvidenceRow } from '../../types/evidence';

interface DataGridProps {
  rows: EvidenceRow[];
  highlightedIndices: number[];
  onRowClick: (row: EvidenceRow) => void;
}

const PREFERRED_COLUMNS = [
  'case_id',
  'language',
  'processing_time_before',
  'processing_time_after',
  'error_flag',
  'outcome',
  'period',
];

const PAGE_SIZE = 20;

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(1);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}

function formatHeader(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

type SortDir = 'asc' | 'desc' | null;

export const DataGrid: React.FC<DataGridProps> = ({ rows, highlightedIndices, onRowClick }) => {
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  // Determine visible columns: preferred columns first, then any others
  const columns = useMemo(() => {
    if (rows.length === 0) return PREFERRED_COLUMNS;
    const allKeys = new Set(rows.flatMap((r) => Object.keys(r).filter((k) => !k.startsWith('_'))));
    const preferred = PREFERRED_COLUMNS.filter((c) => allKeys.has(c));
    const rest = [...allKeys].filter((k) => !PREFERRED_COLUMNS.includes(k) && !k.startsWith('_'));
    return [...preferred, ...rest];
  }, [rows]);

  // Sort
  const sorted = useMemo(() => {
    if (!sortKey || !sortDir) return rows;
    return [...rows].sort((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (va === vb) return 0;
      const cmp = (va ?? '') < (vb ?? '') ? -1 : 1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const pageRows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const flaggedCount = rows.filter((r) => r._flagged).length;

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : d === 'desc' ? null : 'asc'));
      if (sortDir === 'desc') setSortKey(null);
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const highlightedSet = new Set(highlightedIndices);

  return (
    <div className='flex flex-col h-full'>
      {/* Header */}
      <div className='flex items-center justify-between px-4 py-3 border-b border-border shrink-0'>
        <h3 className='font-semibold text-sm text-text'>
          Data Grid
          <span className='ml-2 text-xs text-muted font-normal'>{rows.length} rows</span>
        </h3>
        {flaggedCount > 0 && (
          <span className='inline-flex items-center gap-1 rounded-full bg-warning/10 border border-warning/25 text-warning text-[10px] font-bold px-2 py-0.5'>
            ⚠ {flaggedCount} flagged
          </span>
        )}
      </div>

      {/* Table */}
      <div className='flex-1 overflow-auto'>
        {rows.length === 0 ? (
          <div className='flex h-48 items-center justify-center text-sm text-muted'>
            No data loaded. Select a demo dataset or upload a CSV.
          </div>
        ) : (
          <table className='w-full text-xs border-collapse'>
            <thead className='sticky top-0 bg-surface z-10'>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    onClick={() => handleSort(col)}
                    className='border-b border-border px-3 py-2 text-left font-semibold text-muted cursor-pointer hover:text-text whitespace-nowrap select-none'
                  >
                    {formatHeader(col)}
                    {sortKey === col && (
                      <span className='ml-1 text-primary'>{sortDir === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row) => {
                const isHighlighted = highlightedSet.has(row._row_index);
                const isFlagged = row._flagged;
                return (
                  <tr
                    key={row._row_index}
                    onClick={() => onRowClick(row)}
                      aria-label={`Evidence row ${row._row_index + 1}${isFlagged ? ', has quality findings' : ''}`}
                      tabIndex={row._flagged ? 0 : -1}
                      className={cn(
                      'cursor-pointer border-b border-border/40 transition-colors',
                      isHighlighted
                        ? 'bg-warning/10 border-l-2 border-l-warning'
                        : isFlagged
                        ? 'bg-warning/10 hover:bg-warning/20'
                        : 'hover:bg-raised/40'
                    )}
                  >
                    {columns.map((col) => (
                      <td key={col} className='px-3 py-2 text-text font-mono'>
                        {formatCell(row[col])}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {rows.length > 0 && (
        <div className='flex items-center justify-between px-4 py-2 border-t border-border shrink-0 text-xs text-muted'>
          <span>
            Page {page + 1} of {totalPages}
          </span>
          <div className='flex gap-2'>
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className='px-2 py-1 rounded border border-border hover:bg-raised disabled:opacity-40 disabled:cursor-not-allowed'
            >
              ‹ Prev
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className='px-2 py-1 rounded border border-border hover:bg-raised disabled:opacity-40 disabled:cursor-not-allowed'
            >
              Next ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
