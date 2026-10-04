import { AlertTriangle, ClipboardSignature, Scale } from 'lucide-react';
import { useEffect, useState } from 'react';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { apiFetch } from '../lib/api';

type MatrixRow = { startup_id: string; startup_name: string; evaluator: string; evaluation_id: string; scores: Record<string, { score: number; reason: string }> };
type Criterion = { key: string; label: string; weight: number };
type Matrix = { challenge_id: string; rubric_version: number | null; criteria: Criterion[]; matrix: MatrixRow[]; disagreements: Array<{ criterion: string; label: string; variance: number; threshold: number; flag: boolean }> };

export default function CommitteeWorkspacePage() {
  const [challengeId, setChallengeId] = useState('MH-MUNI-SC-001');
  const [matrix, setMatrix] = useState<Matrix | null>(null);
  const [varianceThreshold, setVarianceThreshold] = useState(1);
  const [startupId, setStartupId] = useState('');
  const [decision, setDecision] = useState('Shortlisted');
  const [reason, setReason] = useState('');
  const [dissent, setDissent] = useState('');
  const [responsibilities, setResponsibilities] = useState([{ name: '', responsibility: '', reason: '' }]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const response = await apiFetch(`/api/evaluations/committee/matrix?challenge_id=${encodeURIComponent(challengeId)}&variance_threshold=${varianceThreshold}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Could not load committee matrix.');
    setMatrix(result);
    if (!startupId && result.matrix[0]) setStartupId(result.matrix[0].startup_id);
  };
  useEffect(() => { void load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load committee matrix.')); }, [challengeId, varianceThreshold]);

  if (!window.localStorage.getItem('pilotproof-token')) return <div className='space-y-6 p-6'><h1 className='font-heading text-3xl font-bold'>Committee review</h1><DemoLoginPrompt /></div>;

  const recordDecision = async () => {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await apiFetch('/api/evaluations/committee/decisions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ challenge_id: challengeId, startup_id: startupId, decision, reason, dissent, responsibilities }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not record committee decision.');
      setMessage(`Decision recorded (${result.id}).`);
      setReason(''); setDissent('');
    } catch (reasonError) { setError(reasonError instanceof Error ? reasonError.message : 'Decision could not be recorded.'); }
    finally { setBusy(false); }
  };

  const maxScore = 5;
  return <div className='mx-auto max-w-7xl space-y-6 p-5 sm:p-8'>
    <header className='hero-wash flex flex-wrap items-end justify-between gap-4 rounded-[1.75rem] border border-border p-6'><div><p className='text-xs uppercase tracking-[0.18em] text-primary'>Officer workspace</p><h1 className='mt-2 font-heading text-3xl font-bold'>Committee review</h1><p className='mt-2 text-sm text-muted'>Compare criterion-level scores, flag disagreement, and record decision responsibilities with reasons.</p></div><div className='flex flex-wrap gap-3'><label className='text-xs text-muted'>Challenge<input className='mt-1 block w-48' value={challengeId} onChange={(event) => setChallengeId(event.target.value)} /></label><label className='text-xs text-muted'>Variance threshold<input className='mt-1 block w-24' type='number' min='0' max='4' step='0.1' value={varianceThreshold} onChange={(event) => setVarianceThreshold(Number(event.target.value))} /></label></div></header>
    {error && <p role='alert' className='rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger'>{error}</p>}{message && <p role='status' className='rounded-lg border border-success/30 bg-success/5 p-3 text-sm text-success'>{message}</p>}
    <Card className='overflow-x-auto p-5'><div className='mb-4 flex items-center gap-2'><Scale className='text-primary' /><div><h2 className='font-heading text-xl font-semibold'>Score matrix · rubric v{matrix?.rubric_version ?? '—'}</h2><p className='text-xs text-muted'>Cell intensity reflects the 1–5 score; hover/focus to read the evaluator’s reason.</p></div></div>{!matrix?.matrix.length ? <p className='py-10 text-center text-sm text-muted'>No submitted evaluations yet.</p> : <table className='min-w-[800px] w-full text-sm'><thead><tr><th className='p-3 text-left'>Startup</th><th className='p-3 text-left'>Evaluator</th>{matrix.criteria.map((criterion) => <th key={criterion.key} className='min-w-28 p-3 text-center'>{criterion.label}<span className='block text-[10px] text-muted'>weight {criterion.weight}%</span></th>)}</tr></thead><tbody>{matrix.matrix.map((row, index) => <tr key={`${row.evaluation_id}-${index}`} className='border-t border-border'><td className='p-3 font-medium'>{row.startup_name}</td><td className='p-3 text-muted'>{row.evaluator}</td>{matrix.criteria.map((criterion) => { const entry = row.scores[criterion.key]; const alpha = entry ? 0.12 + (entry.score / maxScore) * 0.48 : 0; const color = entry ? `rgb(var(--success) / ${alpha})` : 'transparent'; return <td key={criterion.key} className='p-2 text-center'><span title={entry?.reason || 'No criterion score'} className='inline-flex h-10 w-12 items-center justify-center rounded-lg border border-border font-mono font-bold' style={{ backgroundColor: color }}>{entry?.score ?? '—'}</span></td>; })}</tr>)}</tbody></table>}</Card>
    <Card className='p-5'><div className='mb-3 flex items-center gap-2'><AlertTriangle className='text-warning' /><h2 className='font-heading text-xl font-semibold'>Disagreement flags</h2></div>{matrix?.disagreements.length ? <div className='grid gap-3 md:grid-cols-2'>{matrix.disagreements.map((item) => <div key={item.criterion} className='rounded-xl border border-warning/30 bg-warning/5 p-4'><p className='font-semibold'>{item.label}</p><p className='mt-1 text-sm text-muted'>Score variance {item.variance.toFixed(2)} exceeds threshold {item.threshold.toFixed(2)}. Review the written reasons before deciding.</p></div>)}</div> : <p className='text-sm text-muted'>No criterion variance exceeds the selected threshold.</p>}</Card>
    <Card className='space-y-4 p-5 sm:p-6'><div className='flex items-center gap-2'><ClipboardSignature className='text-primary' /><h2 className='font-heading text-xl font-semibold'>Record committee decision</h2></div><div className='grid gap-4 md:grid-cols-2'><label className='grid gap-1 text-xs text-muted'>Applicant<select value={startupId} onChange={(event) => setStartupId(event.target.value)}>{Array.from(new Map((matrix?.matrix ?? []).map((item) => [item.startup_id, item.startup_name])).entries()).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label><label className='grid gap-1 text-xs text-muted'>Decision<select value={decision} onChange={(event) => setDecision(event.target.value)}>{['Shortlisted', 'Selected', 'Not selected', 'Correction requested'].map((item) => <option key={item}>{item}</option>)}</select></label></div><label className='grid gap-1 text-sm text-muted'>Decision reason<textarea rows={3} value={reason} onChange={(event) => setReason(event.target.value)} placeholder='State the evidence and criteria supporting this decision.' /></label><label className='grid gap-1 text-sm text-muted'>Record dissent (optional)<textarea rows={2} value={dissent} onChange={(event) => setDissent(event.target.value)} placeholder='Capture any differing view and its reasons.' /></label><div><div className='mb-2 flex items-center justify-between'><h3 className='font-semibold'>Named responsibilities</h3><Button variant='outline' size='sm' onClick={() => setResponsibilities((items) => [...items, { name: '', responsibility: '', reason: '' }])}>Add person</Button></div><div className='space-y-3'>{responsibilities.map((item, index) => <div key={index} className='grid gap-2 rounded-xl border border-border p-3 md:grid-cols-3'><input aria-label='Responsible person name' placeholder='Person name' value={item.name} onChange={(event) => setResponsibilities((rows) => rows.map((row, i) => i === index ? { ...row, name: event.target.value } : row))} /><input aria-label='Responsibility' placeholder='Responsibility' value={item.responsibility} onChange={(event) => setResponsibilities((rows) => rows.map((row, i) => i === index ? { ...row, responsibility: event.target.value } : row))} /><input aria-label='Responsibility reason' placeholder='Why assigned' value={item.reason} onChange={(event) => setResponsibilities((rows) => rows.map((row, i) => i === index ? { ...row, reason: event.target.value } : row))} /></div>)}</div></div><Button onClick={() => void recordDecision()} disabled={busy || !startupId || reason.trim().length < 10 || responsibilities.some((item) => !item.name.trim() || !item.responsibility.trim() || !item.reason.trim())}>Record decision and responsibilities</Button></Card>
  </div>;
}
