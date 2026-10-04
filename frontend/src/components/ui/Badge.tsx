import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

const variantStyles = {
  default: 'border border-border bg-surface text-text',
  success: 'border-transparent bg-success/20 text-success',
  warning: 'border-transparent bg-warning/20 text-warning',
  error: 'border-transparent bg-danger/20 text-danger',
  info: 'border-transparent bg-primary/20 text-primary',
};

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2',
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
