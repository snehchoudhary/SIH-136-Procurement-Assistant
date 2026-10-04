import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Info, Loader2, ShieldCheck, Upload, X } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { DataGrid } from '../components/evidence/DataGrid';
import { FindingCard } from '../components/evidence/FindingCard';
import { KPIComparisonChart } from '../components/evidence/KPIComparisonChart';
import { ProcessingTimeDistribution } from '../components/evidence/ProcessingTimeDistribution';
import { ReproduceModal } from '../components/evidence/ReproduceModal';
import { useAnimatedNumber } from '../hooks/useAnimatedNumber';
import {
  fetchDemoAnalysis,
  fetchEvidenceRows,
  fetchLatestEvidence,
  submitValidatorDecision,
  uploadEvidenceCSV,
} from '../lib/evidenceApi';
import type {
  EvidenceAnalysis,
  EvidenceRow,
  KPIResult,
  QualityFinding,
  ValidatorAction,
} from '../types/evidence';
import { cn } from '../lib/utils';

// ─── Helpers ─────────────────────────────────────────────────────────────────────

function getUserRole(): string {
  try {
    const token = window.localStorage.getItem('pilotproof-token') ?? '';
    const payload = token.split('.')[1];
    if (!payload) return '';
    return (JSON.parse(atob(payload)) as { role?: string }).role ?? '';
  } catch {
    return '';
  }
}

const DEMO_DATASETS: Array<{ key: string; label: string }> = [
  { key: 'hero_problematic',     label: 'Hero Problematic Demo' },
  { key: 'clean_pass',           label: 'Clean Pass Demo' },
  { key: 'corrected_resubmission', label: 'Corrected Resubmission' },
];
const DEMO_AGREEMENT_ID = 'demo-agreement';

function outcomeStyles(outcome: EvidenceAnalysis['overall_outcome']) {
  switch (outcome) {
    case 'passed':          return { text: 'All KPIs Passed',    icon: CheckCircle2,  color: 'text-success' };
    case 'failed':          return { text: 'KPIs Failed',         icon: AlertTriangle, color: 'text-danger' };
    case 'missing_evidence':return { text: 'Missing Evidence',    icon: Info,          color: 'text-muted' };
    default:                return { text: 'Pending Analysis',    icon: Loader2,       color: 'text-muted' };
  }
}

function severityLabel(severity: QualityFinding['severity']): string {
  return severity.charAt(0).toUpperCase() + severity.slice(1);
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────────

interface KPICardProps {
  kpi: KPIResult;
  onReproduce: (kpi: KPIResult) => void;
}

function KPIOutcomeChip({ outcome }: { outcome: KPIResult['outcome'] }) {
  const styles = {
    passed:           'bg-success/10 text-success border-success/30',
    failed:           'bg-danger/10 text-danger border-danger/30',
    missing_evidence: 'bg-raised text-muted border-border',
  };
  const labels = {
    passed: 'PASSED',
    failed: 'FAILED',
    missing_evidence: 'MISSING EVIDENCE',
  };
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold', styles[outcome])}>
      {labels[outcome]}
    </span>
  );
}

const KPICard: React.FC<KPICardProps> = ({ kpi, onReproduce }) => {
  const animClaimed     = useAnimatedNumber(kpi.claimed_value);
  const animRecomputed  = useAnimatedNumber(kpi.recomputed_value);
  const animDelta       = useAnimatedNumber(kpi.delta);

  return (
    <div className='rounded-xl border border-border bg-raised/30 p-4'>
      <div className='flex items-center justify-between gap-2 mb-3'>
        <h4 className='font-semibold text-sm text-text'>{kpi.kpi_label}</h4>
        <KPIOutcomeChip outcome={kpi.outcome} />
      </div>
      <div className='grid grid-cols-3 gap-2 mb-3'>
        <div className='text-center'>
          <p className='text-[10px] text-muted uppercase tracking-wide mb-1'>Claimed</p>
          <p className='font-mono font-bold text-primary text-sm'>
            {animClaimed != null ? `${animClaimed.toFixed(1)}${kpi.unit}` : '—'}
          </p>
        </div>
        <div className='text-center'>
          <p className='text-[10px] text-muted uppercase tracking-wide mb-1'>Recomputed</p>
          <p className={cn('font-mono font-bold text-sm',
            kpi.outcome === 'passed' ? 'text-success' :
            kpi.outcome === 'failed' ? 'text-danger' : 'text-muted')}>
            {animRecomputed != null ? `${animRecomputed.toFixed(1)}${kpi.unit}` : '—'}
          </p>
        </div>
        <div className='text-center'>
          <p className='text-[10px] text-muted uppercase tracking-wide mb-1'>Delta</p>
          <p className={cn('font-mono font-bold text-sm',
            animDelta != null && animDelta < 0 ? 'text-danger' :
            animDelta != null && animDelta > 0 ? 'text-success' : 'text-muted')}>
            {animDelta != null ? `${animDelta > 0 ? '+' : ''}${animDelta.toFixed(1)}${kpi.unit}` : '—'}
          </p>
        </div>
      </div>
      {kpi.threshold !== null && (
        <p className='text-[10px] text-muted mb-2'>
          Threshold: <span className='text-primary font-mono'>{kpi.threshold}{kpi.unit}</span>
          {' · '}
          Rows used: <span className='font-mono'>{kpi.rows_used}</span>
        </p>
      )}
      <p className='text-xs text-muted leading-relaxed mb-3'>{kpi.explanation}</p>
      <button
        onClick={() => onReproduce(kpi)}
        className='text-xs font-medium text-primary hover:text-primary/80 underline underline-offset-2 transition-colors'
      >
        Reproduce this result ↗
      </button>
    </div>
  );
};

// ─── Decision Modal ───────────────────────────────────────────────────────────────

interface DecisionModalProps {
  action: ValidatorAction | null;
  onConfirm: (reason: string) => void;
  onClose: () => void;
}

const ACTION_META: Record<ValidatorAction, { label: string; color: string; warning?: string }> = {
  accepted:             { label: 'Accept Evidence',       color: 'bg-success text-on-primary hover:brightness-95' },
  disputed:             { label: 'Dispute Evidence',      color: 'bg-warning text-text hover:brightness-95' },
  correction_requested: { label: 'Request Correction',    color: 'bg-warning text-text hover:brightness-95',
    warning: 'This will move the milestone to "Correction Requested" status. The startup will need to resubmit.' },
};

const DecisionModal: React.FC<DecisionModalProps> = ({ action, onConfirm, onClose }) => {
  const [reason, setReason] = useState('');
  const meta = action ? ACTION_META[action] : null;
  const needsReason = action !== 'accepted';
  const canSubmit = !needsReason || reason.trim().length >= 20;

  useEffect(() => { if (!action) setReason(''); }, [action]);

  return (
    <AnimatePresence>
      {action && (
        <motion.div
          key='decision-backdrop'
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className='fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4'
          onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
          <motion.div
            key='decision-panel'
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
            className='w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl'
          >
            <div className='flex items-center justify-between mb-4'>
              <h2 className='font-heading text-lg font-bold'>{meta?.label}</h2>
              <button onClick={onClose} className='p-1.5 rounded-full hover:bg-raised text-muted hover:text-text transition-colors'>
                <X size={16} />
              </button>
            </div>

            {meta?.warning && (
              <div className='mb-4 rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning flex gap-2'>
                <AlertTriangle size={14} className='shrink-0 mt-0.5' />
                {meta.warning}
              </div>
            )}

            {needsReason && (
              <div className='mb-4'>
                <label className='block text-xs text-muted mb-1.5'>
                  Reason <span className='text-muted'>(min 20 characters)</span>
                </label>
                <textarea
                  rows={4}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder='Provide a clear reason for this decision...'
                  className='w-full rounded-xl border border-border bg-raised/40 px-3 py-2 text-sm text-text placeholder:text-muted resize-none focus:outline-none focus:ring-2 focus:ring-primary/40'
                />
                <p className='text-right text-[10px] text-muted mt-1'>{reason.trim().length}/20 min</p>
              </div>
            )}

            <div className='flex gap-3 justify-end'>
              <Button variant='outline' onClick={onClose}>Cancel</Button>
              <button
                disabled={!canSubmit}
                onClick={() => { onConfirm(reason); onClose(); setReason(''); }}
                className={cn(
                  'inline-flex items-center justify-center rounded-md px-4 h-10 text-sm font-medium text-inverse-text transition-colors disabled:opacity-40 disabled:pointer-events-none',
                  meta?.color
                )}
              >
                Confirm
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────────

export default function ValidatorWorkspacePage() {
  const [analysis, setAnalysis] = useState<EvidenceAnalysis | null>(null);
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<QualityFinding | null>(null);
  const [highlightedRowIndices, setHighlightedRowIndices] = useState<number[]>([]);
  const [activeDataset, setActiveDataset] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [reproduceKpi, setReproduceKpi] = useState<KPIResult | null>(null);
  const [decisionAction, setDecisionAction] = useState<ValidatorAction | null>(null);
  const [findingsOpen, setFindingsOpen] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const role = getUserRole();
  const isStartup = role === 'startup';

  const hasCritical = (analysis?.findings ?? []).some((f) => f.severity === 'critical');
  const canAccept = Boolean(analysis && !analysis.is_demo && analysis.overall_outcome === 'passed' && !hasCritical);

  // Load demo dataset
  const loadDemo = useCallback(async (key: string) => {
    setLoading(true);
    setError('');
    setSuccessMessage('');
    setSelectedFinding(null);
    setHighlightedRowIndices([]);

    try {
      const a = await fetchDemoAnalysis(key);
      setAnalysis(a);
      setActiveDataset(key);

      setRows(a.rows ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dataset.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load hero on mount for a good first impression
  useEffect(() => { void loadDemo('hero_problematic'); }, [loadDemo]);

  const refreshLatest = async () => {
    setLoading(true);
    setError('');
    try {
      const latest = await fetchLatestEvidence(DEMO_AGREEMENT_ID);
      setAnalysis(latest);
      setRows(latest.rows ?? []);
      setActiveDataset(null);
      setSuccessMessage(`Loaded submission v${latest.version_number}. Milestone status: ${latest.milestone_status ?? 'Pending'}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No persisted submission is available.');
    } finally { setLoading(false); }
  };

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setError('');
    setSuccessMessage('');
    setActiveDataset(null);
    try {
      const a = await uploadEvidenceCSV(file, DEMO_AGREEMENT_ID, {});
      setAnalysis(a);
      setRows(a.rows ?? await fetchEvidenceRows(a.upload_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDecisionConfirm = async (reason: string) => {
    if (!analysis || !decisionAction) return;
    try {
      await submitValidatorDecision(analysis.upload_id, decisionAction, reason);
      const labels: Record<ValidatorAction, string> = {
        accepted:             'Evidence accepted and recorded.',
        disputed:             'Dispute recorded.',
        correction_requested: 'Correction request submitted. Milestone moved to Correction Requested.',
      };
      setSuccessMessage(labels[decisionAction]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed.');
    }
    setDecisionAction(null);
  };

  const handleShowRows = (indices: number[]) => {
    setHighlightedRowIndices(indices);
  };

  const handleFindingSelect = (finding: QualityFinding) => {
    if (selectedFinding?.id === finding.id) {
      setSelectedFinding(null);
      setHighlightedRowIndices([]);
    } else {
      setSelectedFinding(finding);
      setHighlightedRowIndices(finding.row_indices);
    }
  };

  const handleRowClick = (row: EvidenceRow) => {
    if (!row._flagged || !row._finding_ids.length) return;
    const findingId = (row._finding_ids as string[])[0];
    const finding = analysis?.findings.find((f) => f.id === findingId) ?? null;
    if (finding) { setSelectedFinding(finding); setHighlightedRowIndices(finding.row_indices); }
  };

  const outcomeInfo = analysis ? outcomeStyles(analysis.overall_outcome) : null;
  const OutcomeIcon = outcomeInfo?.icon ?? null;

  return (
    <div className='flex flex-col h-[calc(100vh-4rem)] overflow-hidden'>
      {/* ── Top bar ───────────────────────────────────────────────────────── */}
      <div className='shrink-0 border-b border-border bg-surface/80 backdrop-blur-md px-5 py-3 flex flex-wrap items-center gap-3'>
        <div className='flex items-center gap-2 mr-2'>
          <ShieldCheck size={18} className='text-primary' />
          <h1 className='font-heading font-bold text-base text-text whitespace-nowrap'>
            Evidence Verification Workspace
          </h1>
        </div>

        {/* Dataset buttons */}
        <div className='flex items-center gap-2 flex-wrap'>
          {DEMO_DATASETS.map(({ key, label }) => (
            <button
              key={key}
              disabled={loading}
              onClick={() => void loadDemo(key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                activeDataset === key
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-muted hover:text-text hover:border-text/30'
              )}
            >
              {label}
            </button>
          ))}
          <button disabled={loading} onClick={() => void refreshLatest()} className='px-3 py-1.5 rounded-lg text-xs font-medium border border-primary text-primary hover:bg-primary disabled:opacity-50'>Refresh latest submission</button>
        </div>

        <div className='flex items-center gap-2 ml-auto'>
          {loading && <LoadingSpinner size='sm' />}

          {/* Upload CSV */}
          <input
            ref={fileInputRef}
            type='file'
            accept='.csv'
            className='hidden'
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleFileUpload(f); e.target.value = ''; }}
          />
          <Button
            size='sm'
            variant='outline'
            leftIcon={<Upload size={13} />}
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || !isStartup}
            title={!isStartup ? 'Only the applicant can submit evidence.' : 'Upload a CSV evidence file'}
          >
            Upload CSV
          </Button>
        </div>
      </div>

      {/* ── Alerts ────────────────────────────────────────────────────────── */}
      <div className='shrink-0 px-5'>
        {error && (
          <p role='alert' className='mt-2 rounded-xl border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger flex items-center gap-2'>
            <AlertTriangle size={13} />{error}
          </p>
        )}
        {successMessage && (
          <p role='status' className='mt-2 rounded-xl border border-success/30 bg-success/5 px-3 py-2 text-xs text-success flex items-center gap-2'>
            <CheckCircle2 size={13} />{successMessage}
          </p>
        )}
      </div>

      {/* ── Split Screen ──────────────────────────────────────────────────── */}
      <div className='flex-1 grid grid-cols-[55%_45%] min-h-0 mt-2'>

        {/* LEFT: Data Grid */}
        <div className='border-r border-border overflow-hidden flex flex-col'>
          <DataGrid
            rows={rows}
            highlightedIndices={highlightedRowIndices}
            onRowClick={handleRowClick}
          />
        </div>

        {/* RIGHT: Metric Panel */}
        <div className='overflow-y-auto flex flex-col'>

          {/* Overall outcome banner */}
          {analysis && outcomeInfo && OutcomeIcon && (
            <div className={cn(
              'shrink-0 mx-4 mt-3 rounded-xl border px-4 py-3 flex items-start gap-3',
              analysis.overall_outcome === 'passed'
                ? 'border-success/30 bg-success/5'
                : analysis.overall_outcome === 'failed'
                ? 'border-danger/30 bg-danger/5'
                : 'border-border/30 bg-raised/5'
            )}>
              <OutcomeIcon size={16} className={cn('mt-0.5 shrink-0', outcomeInfo.color)} />
              <div>
                <p className={cn('text-xs font-bold', outcomeInfo.color)}>{outcomeInfo.text}</p>
                <p className='text-[11px] text-muted mt-0.5 leading-relaxed'>{analysis.outcome_summary}</p>
                {analysis.is_demo && <p className='mt-1 text-[10px] font-semibold text-primary'>Synthetic demo evidence · decisions disabled</p>}
                {analysis.milestone_status && <p className='mt-1 text-[10px] text-muted'>Milestone: {analysis.milestone_status}</p>}
                {analysis.previous_version_marked_stale && (
                  <p className='text-[10px] text-warning mt-1'>⚠ Previous version marked stale</p>
                )}
              </div>
            </div>
          )}

          {/* ── Findings list ──────────────────────────────────────────── */}
          <div className='mx-4 mt-4'>
            <button
              onClick={() => setFindingsOpen((v) => !v)}
              className='w-full flex items-center justify-between mb-2 text-left'
            >
              <div className='flex items-center gap-2'>
                <span className='text-xs font-bold text-text uppercase tracking-wide'>Quality Findings</span>
                {analysis && (
                  <span className='rounded-full bg-raised border border-border px-2 py-0.5 text-[10px] font-mono text-muted'>
                    {analysis.findings.length}
                  </span>
                )}
              </div>
              {findingsOpen ? <ChevronUp size={14} className='text-muted' /> : <ChevronDown size={14} className='text-muted' />}
            </button>

            <AnimatePresence initial={false}>
              {findingsOpen && (
                <motion.div
                  key='findings-section'
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.22 }}
                  className='overflow-hidden'
                >
                  {analysis?.findings.length === 0 && (
                    <p className='text-xs text-muted py-3 text-center rounded-xl border border-dashed border-border'>
                      No quality findings — dataset is clean.
                    </p>
                  )}
                  <div className='space-y-2'>
                    {(analysis?.findings ?? []).map((finding) => (
                      <div key={finding.id} onClick={() => handleFindingSelect(finding)} className='cursor-pointer'>
                        <FindingCard
                          finding={finding}
                          isSelected={selectedFinding?.id === finding.id}
                          onShowRows={handleShowRows}
                        />
                        <span className='sr-only'>{severityLabel(finding.severity)} severity</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── Validator actions ──────────────────────────────────────── */}
          <div className='mx-4 mt-4'>
            <p className='text-xs font-bold text-text uppercase tracking-wide mb-2'>Validator Decision</p>
            {isStartup ? (
              <p className='text-xs text-muted rounded-xl border border-dashed border-border py-3 px-3'>
                Applicants cannot validate their own evidence.
              </p>
            ) : (
              <div className='flex flex-wrap gap-2'>
                <button
                  disabled={!canAccept}
                  onClick={() => setDecisionAction('accepted')}
                  title={!canAccept ? 'Only a current, complete passing upload can be accepted' : 'Accept evidence'}
                  className='px-3 py-1.5 rounded-lg text-xs font-medium bg-success/20 border border-success/40 text-success hover:bg-success/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors'
                >
                  ✓ Accept
                </button>
                <button
                  disabled={!analysis}
                  onClick={() => setDecisionAction('disputed')}
                  className='px-3 py-1.5 rounded-lg text-xs font-medium bg-warning/20 border border-warning/40 text-warning hover:bg-warning/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors'
                >
                  ⚑ Dispute
                </button>
                <button
                  disabled={!analysis}
                  onClick={() => setDecisionAction('correction_requested')}
                  className='px-3 py-1.5 rounded-lg text-xs font-medium bg-warning/20 border border-warning/40 text-warning hover:bg-warning/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors'
                >
                  ↺ Request Correction
                </button>
              </div>
            )}
          </div>

          {/* ── KPI Comparison ─────────────────────────────────────────── */}
          <div className='mx-4 mt-5'>
            <p className='text-xs font-bold text-text uppercase tracking-wide mb-3'>KPI Comparison</p>

            {analysis && analysis.kpi_results.length > 0 ? (
              <>
                <Card className='p-3 mb-3'>
                  <KPIComparisonChart kpiResults={analysis.kpi_results} />
                </Card>
                <div className='space-y-3'>
                  {analysis.kpi_results.map((kpi) => (
                    <KPICard key={kpi.id} kpi={kpi} onReproduce={setReproduceKpi} />
                  ))}
                </div>
              </>
            ) : (
              <p className='text-xs text-muted py-4 text-center rounded-xl border border-dashed border-border'>
                No KPI results available.
              </p>
            )}
          </div>

          {/* ── Processing Time Distribution ────────────────────────────── */}
          <div className='mx-4 mt-5 mb-6'>
            <p className='text-xs font-bold text-text uppercase tracking-wide mb-3'>Processing Time Distribution</p>
            <Card className='p-4'>
              <ProcessingTimeDistribution rows={rows} />
            </Card>
          </div>
        </div>
      </div>

      {/* ── Modals ────────────────────────────────────────────────────────── */}
      <ReproduceModal kpi={reproduceKpi} sha256Hash={analysis?.sha256_hash} onClose={() => setReproduceKpi(null)} />
      <DecisionModal
        action={decisionAction}
        onConfirm={handleDecisionConfirm}
        onClose={() => setDecisionAction(null)}
      />
    </div>
  );
}
