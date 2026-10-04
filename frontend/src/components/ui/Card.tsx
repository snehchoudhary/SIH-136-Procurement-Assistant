import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  glow?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, elevated, glow, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-card border border-border bg-surface text-text relative overflow-hidden transition-all duration-300',
          elevated && 'shadow-lg bg-raised',
          glow && 'shadow-glow hover:shadow-[0_0_0_1px_rgba(255,176,32,0.4),0_20px_50px_rgba(10,15,30,0.5)]',
          className
        )}
        {...props}
      >
        <div className='absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay bg-[url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")]'></div>
        <div className='relative z-10'>{children}</div>
      </div>
    );
  }
);
Card.displayName = 'Card';
