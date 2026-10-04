import React from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: boolean;
  success?: boolean;
  helperText?: string;
  leftSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, success, helperText, leftSlot, rightSlot, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className='flex flex-col gap-1 w-full relative group'>
        {label && (
          <label htmlFor={inputId} className='text-sm font-medium text-muted mb-1 ml-1 group-focus-within:text-primary transition-colors -translate-y-0.5'>
            {label}
          </label>
        )}
        <div className='relative flex items-center w-full'>
          {leftSlot && <div className='absolute left-3 text-muted'>{leftSlot}</div>}
          <input
            id={inputId}
            ref={ref}
            className={cn(
              'w-full',
              leftSlot ? 'pl-10' : 'pl-3',
              rightSlot ? 'pr-10' : 'pr-3',
              error && 'border-danger focus:ring-danger/50 focus:border-danger',
              success && 'border-success focus:ring-success/50 focus:border-success',
              className
            )}
            {...props}
          />
          {rightSlot && <div className='absolute right-3 text-muted'>{rightSlot}</div>}
        </div>
        {helperText && (
          <span className={cn('text-xs ml-1 mt-1', error ? 'text-danger' : success ? 'text-success' : 'text-muted')}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';
