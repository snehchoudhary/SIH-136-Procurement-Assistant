import React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'outline' | 'ghost' | 'danger';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles = {
  default: 'bg-primary text-on-primary hover:brightness-95 shadow-sm',
  primary: 'bg-primary text-on-primary hover:brightness-95 shadow-glow',
  outline: 'border border-border hover:bg-surface text-text',
  ghost: 'hover:bg-surface text-text',
  danger: 'bg-danger text-on-primary hover:brightness-95 shadow-sm',
};

const sizeStyles = {
  default: 'h-10 py-2 px-4',
  sm: 'h-8 px-3 rounded-md text-xs',
  lg: 'h-12 px-8 rounded-md text-base',
  icon: 'h-10 w-10',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', isLoading, leftIcon, rightIcon, children, ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:opacity-50 disabled:pointer-events-none',
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        ref={ref}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
        {!isLoading && leftIcon && <span className='mr-2'>{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className='ml-2'>{rightIcon}</span>}
      </button>
    );
  }
);
Button.displayName = 'Button';
