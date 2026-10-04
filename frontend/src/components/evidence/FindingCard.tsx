import React from 'react';
import { cn } from '../../lib/utils';
import type { QualityFinding } from '../../types/evidence';
import { SeverityChip } from './SeverityChip';

interface FindingCardProps {
  finding: QualityFinding;
  onShowRows: (indices: number[]) => void;
  isSelected: boolean;
}

function formatCheckName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding, onShowRows, isSelected }) => {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-all duration-200',
        isSelected
          ? 'border-warning bg-warning/30 shadow-md'
          : 'border-border bg-surface hover:border-warning/60'
      )}
    >
      <div className='flex items-start justify-between gap-3 mb-2'>
        <div className='flex items-center gap-2 flex-wrap'>
          <SeverityChip severity={finding.severity} />
          <h4 className='font-semibold text-sm text-text'>{formatCheckName(finding.check_name)}</h4>
        </div>
        <span className='shrink-0 rounded-full bg-raised border border-border px-2 py-0.5 text-[10px] font-mono text-muted'>
          {finding.rows_affected} rows
        </span>
      </div>
      <p className='text-xs text-muted leading-relaxed mb-3'>{finding.explanation}</p>
      <button
        onClick={() => onShowRows(finding.row_indices)}
        className='text-xs font-medium text-primary hover:text-primary/80 transition-colors underline underline-offset-2'
      >
        Show rows ↗
      </button>
    </div>
  );
};
