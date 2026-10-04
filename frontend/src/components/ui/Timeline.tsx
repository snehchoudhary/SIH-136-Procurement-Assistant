import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  date: string;
  isActive?: boolean;
}

export interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ events, className }) => {
  return (
    <div className={cn('relative pl-6', className)}>
      <div className='absolute left-2 top-2 bottom-2 w-px bg-border'>
        <motion.div
          className='absolute top-0 left-0 w-full bg-primary'
          initial={{ height: 0 }}
          animate={{ height: '100%' }}
          transition={{ duration: 1.5, ease: 'easeInOut' }}
        />
      </div>
      
      <div className='space-y-6 relative'>
        {events.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.15 + 0.3 }}
            className='relative'
          >
            <div className={cn(
              'absolute -left-[30px] top-1.5 w-3 h-3 rounded-full border-2 bg-bg',
              event.isActive ? 'border-primary animate-pulse shadow-[0_0_8px_rgba(255,176,32,0.6)]' : 'border-muted'
            )} />
            <div className={cn('p-4 rounded-lg border bg-surface transition-colors', event.isActive ? 'border-primary/50' : 'border-border')}>
              <div className='flex justify-between items-start mb-1'>
                <h4 className='font-semibold text-text'>{event.title}</h4>
                <span className='text-xs text-muted font-mono'>{event.date}</span>
              </div>
              <p className='text-sm text-muted'>{event.description}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
