import React from 'react';
import { cn } from '../../lib/utils';
import type { Severity } from '../../types/evidence';

interface SeverityChipProps {
  severity: Severity;
  className?: string;
}

const config: Record<Severity, { label: string; classes: string }> = {
  critical: { label: 'Critical', classes: 'bg-danger/10 text-danger border-danger/25' },
  major:    { label: 'Major',    classes: 'bg-warning/10 text-warning border-warning/25' },
  minor:    { label: 'Minor',    classes: 'bg-raised text-muted border-border' },
  info:     { label: 'Info',     classes: 'bg-primary/10 text-primary border-primary/25' },
};

export const SeverityChip: React.FC<SeverityChipProps> = ({ severity, className }) => {
  const { label, classes } = config[severity];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
        classes,
        className
      )}
    >
      {label}
    </span>
  );
};
