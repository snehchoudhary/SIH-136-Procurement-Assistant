import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer, className }) => {
  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className='fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm'
            aria-hidden='true'
            onClick={onClose}
          />
          <div className='fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none'>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              role='dialog'
              aria-modal='true'
              aria-labelledby='modal-heading'
              className={cn('bg-surface border border-border rounded-card shadow-2xl w-full pointer-events-auto overflow-hidden flex flex-col', !className?.includes('max-w') && 'max-w-lg', className)}
            >
              <div className='flex justify-between items-center p-4 border-b border-border'>
                <h3 id='modal-heading' className='font-semibold text-lg text-text'>{title}</h3>
                <button onClick={onClose} aria-label='Close dialog' className='p-1 text-muted hover:text-text rounded-md hover:bg-raised transition-colors'>
                  <X size={20} />
                </button>
              </div>
              <div className='p-4 flex-1 overflow-y-auto'>
                {children}
              </div>
              {footer && (
                <div className='p-4 border-t border-border bg-raised/50 flex justify-end gap-2'>
                  {footer}
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};
