import React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, Download } from 'lucide-react';
import { Button } from '../ui/Button';
import type { KPIResult } from '../../types/evidence';

interface ReproduceModalProps {
  kpi: KPIResult | null;
  sha256Hash?: string;
  onClose: () => void;
}

function buildPythonCode(kpi: KPIResult): string {
  const lines: string[] = [
    `# ${kpi.kpi_label} · ${kpi.rows_used} source rows · ${kpi.outcome}`,
    kpi.python_code || '# Reproduction code is unavailable for this preview.',
  ];
  return lines.join('\n');
}

function downloadPy(kpi: KPIResult): void {
  const code = buildPythonCode(kpi);
  const blob = new Blob([code], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `reproduce_${kpi.kpi_key}.py`;
  a.click();
  URL.revokeObjectURL(url);
}

export const ReproduceModal: React.FC<ReproduceModalProps> = ({ kpi, sha256Hash, onClose }) => {
  return (
    <AnimatePresence>
      {kpi && (
        <motion.div
          key='reproduce-modal-backdrop'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className='fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4'
          onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
          <motion.div
            key='reproduce-modal-panel'
            initial={{ opacity: 0, scale: 0.96, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 24 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
            className='relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-surface shadow-2xl'
          >
            {/* Header */}
            <div className='flex items-start justify-between gap-4 p-6 border-b border-border'>
              <div>
                <p className='text-[10px] uppercase tracking-[0.18em] text-primary mb-1'>
                  Reproduce this result
                </p>
                <h2 className='font-heading text-xl font-bold text-text'>{kpi.kpi_label}</h2>
                <p className='text-xs text-muted mt-1'>
                  {kpi.rows_used} rows used · Outcome:{' '}
                  <span
                    className={
                      kpi.outcome === 'passed'
                        ? 'text-success'
                        : kpi.outcome === 'failed'
                        ? 'text-danger'
                        : 'text-muted'
                    }
                  >
                    {kpi.outcome.replace('_', ' ').toUpperCase()}
                  </span>
                </p>
              </div>

              <p className='text-[11px] text-muted'>The code shown is the calculation stored with this evidence result. The CSV rows remain the source of truth.</p>
              <button
                onClick={onClose}
                className='p-2 rounded-full text-muted hover:text-text hover:bg-raised transition-colors'
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className='p-6 space-y-6'>
              {/* Summary */}
              <div className='grid grid-cols-3 gap-3'>
                {[
                  { label: 'Claimed', value: kpi.claimed_value, suffix: kpi.unit },
                  { label: 'Recomputed', value: kpi.recomputed_value, suffix: kpi.unit },
                  { label: 'Delta', value: kpi.delta, suffix: kpi.unit, sign: true },
                ].map(({ label, value, suffix, sign }) => (
                  <div key={label} className='rounded-xl border border-border bg-raised/40 p-3 text-center'>
                    <p className='text-[10px] text-muted uppercase tracking-wide mb-1'>{label}</p>
                    <p className='font-mono font-bold text-lg text-text'>
                      {value == null
                        ? '—'
                        : `${sign && value > 0 ? '+' : ''}${value.toFixed(1)}${suffix}`}
                    </p>
                  </div>
                ))}
              </div>

              {/* Explanation */}
              <div>
                <p className='text-xs font-semibold text-muted uppercase tracking-wide mb-2'>Explanation</p>
                <p className='text-sm text-text leading-relaxed'>{kpi.explanation}</p>
              </div>

              {/* Calculation steps */}
              <div>
                <p className='text-xs font-semibold text-muted uppercase tracking-wide mb-3'>
                  Calculation Steps
                </p>
                <ol className='space-y-2'>
                  {kpi.calculation_steps.map((step, i) => (
                    <li key={i} className='flex gap-3 text-sm text-text'>
                      <span className='shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary font-bold text-[10px]'>
                        {i + 1}
                      </span>
                      <span className='leading-relaxed pt-0.5'>{step}</span>
                    </li>
                  ))}
                </ol>
              </div>

              {/* Python code */}
              <div>
                <p className='text-xs font-semibold text-muted uppercase tracking-wide mb-2'>
                  Python Reproduction Code
                </p>
                {sha256Hash && <p className='mb-2 break-all font-mono text-[10px] text-muted'>Source file SHA-256: {sha256Hash}</p>}
                <pre className='rounded-xl border border-border bg-raised/60 p-4 text-xs font-mono text-text overflow-x-auto leading-relaxed'>
                  {buildPythonCode(kpi)}
                </pre>
              </div>
            </div>

            {/* Footer */}
            <div className='flex items-center justify-end gap-3 px-6 pb-6'>
              <Button variant='outline' onClick={onClose}>
                Close
              </Button>
              <Button
                onClick={() => downloadPy(kpi)}
                leftIcon={<Download size={14} />}
              >
                Download .py
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
