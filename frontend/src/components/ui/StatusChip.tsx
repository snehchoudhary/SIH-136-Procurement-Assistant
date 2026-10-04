import React from 'react';
import { AlertTriangle, CheckCircle2, CircleDashed, Clock3, FlaskConical, Sparkles } from 'lucide-react';
import { cn } from '../../lib/utils';

type Status = 'Verified' | 'Pending' | 'Disputed' | 'Needs Verification' | 'AI-Drafted' | 'Simulated';
export interface StatusChipProps extends React.HTMLAttributes<HTMLDivElement> { status: Status }

const statusStyles: Record<Status, { tone: string; icon: React.ElementType }> = {
  Verified: { tone: 'bg-success/10 text-success border-success/25', icon: CheckCircle2 },
  Pending: { tone: 'bg-warning/10 text-warning border-warning/25', icon: Clock3 },
  Disputed: { tone: 'bg-danger/10 text-danger border-danger/25', icon: AlertTriangle },
  'Needs Verification': { tone: 'bg-warning/10 text-warning border-warning/25', icon: CircleDashed },
  'AI-Drafted': { tone: 'bg-primary/10 text-primary border-primary/25', icon: Sparkles },
  Simulated: { tone: 'bg-raised text-muted border-border', icon: FlaskConical },
};

export const StatusChip: React.FC<StatusChipProps> = ({ status, className, ...props }) => {
  const { tone, icon: Icon } = statusStyles[status];
  return <div className={cn('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium', tone, className)} {...props}>
    <Icon aria-hidden='true' size={13}/><span>{status}</span>
  </div>;
};
