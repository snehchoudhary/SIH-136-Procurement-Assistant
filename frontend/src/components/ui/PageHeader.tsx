import React from 'react';
import { cn } from '../../lib/utils';

export interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  actionSlot?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, description, eyebrow, actionSlot, className }) => {
  return (
    <div className={cn('flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 mb-6 border-b border-border', className)}>
      <div className='flex-1 slide-up'>
        {eyebrow && <span className='text-primary text-sm font-medium uppercase tracking-wider block mb-1'>{eyebrow}</span>}
        <h1 className='text-3xl font-heading font-bold text-text'>{title}</h1>
        {description && <p className='text-muted mt-2 max-w-2xl'>{description}</p>}
      </div>
      {actionSlot && <div className='shrink-0 flex items-center gap-2 slide-up' style={{ animationDelay: '0.1s' }}>{actionSlot}</div>}
    </div>
  );
};
