import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastProps {
  id: string;
  title: string;
  message?: string;
  type?: ToastType;
  duration?: number;
  onDismiss: (id: string) => void;
}

const icons = {
  success: <CheckCircle className='text-success' size={20} />,
  error: <AlertCircle className='text-danger' size={20} />,
  info: <Info className='text-primary' size={20} />,
};

export const Toast: React.FC<ToastProps> = ({ id, title, message, type = 'info', duration = 5000, onDismiss }) => {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (duration <= 0) return;
    
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    const updateProgress = () => {
      const now = Date.now();
      const remaining = Math.max(0, endTime - now);
      setProgress((remaining / duration) * 100);
      
      if (remaining > 0) {
        requestAnimationFrame(updateProgress);
      } else {
        onDismiss(id);
      }
    };
    
    const animId = requestAnimationFrame(updateProgress);
    return () => cancelAnimationFrame(animId);
  }, [id, duration, onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      className='bg-surface border border-border shadow-lg rounded-lg p-4 mb-3 w-80 relative overflow-hidden flex items-start gap-3 pointer-events-auto glass'
    >
      <div className='shrink-0 mt-0.5'>{icons[type]}</div>
      <div className='flex-1'>
        <h4 className='text-sm font-semibold text-text'>{title}</h4>
        {message && <p className='text-xs text-muted mt-1'>{message}</p>}
      </div>
      <button onClick={() => onDismiss(id)} className='text-muted hover:text-text shrink-0'>
        <X size={16} />
      </button>
      
      {duration > 0 && (
        <div className='absolute bottom-0 left-0 h-1 bg-border w-full'>
          <div 
            className='h-full bg-primary transition-all ease-linear'
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </motion.div>
  );
};
