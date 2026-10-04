import React from 'react';
import { cn } from '../../lib/utils';
import { useCountUp } from '../../hooks/useCountUp';

export interface StatTileProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  trend?: number;
}

export const StatTile: React.FC<StatTileProps> = ({ title, value, prefix = '', suffix = '', trend, className, ...props }) => {
  const count = useCountUp(value, 1200);

  return (
    <div
      className={cn(
        'p-5 rounded-card bg-surface border border-border hover:border-primary/50 transition-colors group relative overflow-hidden',
        className
      )}
      {...props}
    >
      <div className='absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity'>
        <svg viewBox='0 0 100 50' className='w-16 h-8 stroke-primary fill-none stroke-2'>
          <path d='M0 50 Q 25 25, 50 25 T 100 0' />
        </svg>
      </div>
      <p className='text-sm font-medium text-muted mb-2'>{title}</p>
      <div className='flex items-baseline gap-2'>
        <h3 className='text-3xl font-heading font-bold text-text'>
          {prefix}{count.toLocaleString()}{suffix}
        </h3>
        {trend !== undefined && (
          <span className={cn('text-sm font-medium', trend >= 0 ? 'text-success' : 'text-danger')}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
    </div>
  );
};
