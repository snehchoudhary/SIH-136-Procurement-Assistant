import { Eye, EyeOff, LockKeyhole, Send, ShieldAlert, ShieldCheck, Star } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusChip } from '../components/ui/StatusChip';
import { apiFetch } from '../lib/api';

type Criterion = { key: string; label: string; weight: number };
type QueueItem = { application_id: string; startup_id: string; startup_name: string | null; blind_label: string; sector: string; district: string; conflict_declaration: string; conflict_details: string; scoring_blocked: boolean; scoring_submitted: boolean };
type Rubric = { id: string | null; version: number | null; criteria: Criterion[] };

export default function EvaluatorWorkspacePage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [selected, setSelected] = useState<QueueItem | null>(null);
  const [challengeId, setChallengeId] = useState('MH-MUNI-SC-001');
  const [blind, setBlind] = useState(true);
  const [conflict, setConflict] = useState<'none' | 'declared' | ''>('');
  const [conflictDetails, setConflictDetails] = useState('');
  const [scores, setScores] = useState<Record<string, { score: number; reason: string }>>({});
  const [rationale, setRationale] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const loadQueue = async () => {
    const response = await apiFetch(`/api/evaluations/queue?challenge_id=${encodeURIComponent(challengeId)}&blind_mode=${blind}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Could not load evaluation queue.');
    setQueue(result.items ?? []);
    setRubric(result.rubric ?? null);
  };

  useEffect(() => { void loadQueue().catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load queue.')); }, [challengeId, blind]);
  const criteria = useMemo(() => rubric?.criteria ?? [], [rubric]);

  if (!window.localStorage.getItem('pilotproof-token')) return <div className='space-y-6 p-6'><h1 className='font-heading text-3xl font-bold'>Evaluator workspace</h1><DemoLoginPrompt /></div>;

  const submitConflict = async () => {
    if (!selected || !conflict) return;
    setBusy(true); setError('');
    try {
      const response = await apiFetch('/api/evaluations/conflicts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ startup_id: selected.startup_id, challenge_id: challengeId, has_conflict: conflict === 'declared', details: conflict === 'declared' ? conflictDetails : 'No conflict declared.' }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Conflict declaration failed.');
      await loadQueue();
      const refreshed = queue.find((item) => item.application_id === selected.application_id);
      setSelected(refreshed ? { ...refreshed, scoring_blocked: result.blocked_from_scoring, conflict_declaration: conflict } : selected);
      setMessage(result.blocked_from_scoring ? 'Conflict recorded. Scoring is blocked for this applicant.' : 'No-conflict declaration recorded. Scoring is available.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Conflict declaration failed.'); }
    finally { setBusy(false); }
  };

  const submitScores = async () => {
    if (!selected || !rubric?.id || !conflict) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const declarationResponse = await apiFetch('/api/evaluations/conflicts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ startup_id: selected.startup_id, challenge_id: challengeId, has_conflict: false, details: 'Evaluator confirmed no conflict before scoring.' }) });
      const declaration = await declarationResponse.json();
      if (!declarationResponse.ok) throw new Error(declaration.detail || 'Conflict declaration is required first.');
      const response = await apiFetch('/api/evaluations/score', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ application_id: selected.application_id, rubric_version_id: rubric.id, conflict_declaration_id: declaration.id, scores, overall_rationale: rationale }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Scoring failed.');
      setMessage(`Score submitted against rubric v${result.rubric_version}.`);
      setSelected(null); setConflict(''); setScores({}); setRationale('');
      await loadQueue();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Scoring failed.'); }
    finally { setBusy(false); }
  };

  return <div className='mx-auto max-w-7xl space-y-6 p-5 sm:p-8'>
    <header className='hero-wash flex flex-wrap items-end justify-between gap-4 rounded-[1.75rem] border border-border p-6'><div><p className='text-xs uppercase tracking-[0.18em] text-primary'>Evaluator workspace</p><h1 className='mt-2 font-heading text-3xl font-bold'>Independent evaluation</h1><p className='mt-2 text-sm text-muted'>Declare conflicts before scoring. Every rubric score requires a written reason.</p></div><label className='flex items-center gap-2 rounded-xl border border-border bg-surface/80 px-3 py-2 text-sm'><input type='checkbox' checked={blind} onChange={(event) => setBlind(event.target.checked)} className='accent-primary' />{blind ? <EyeOff size={16} /> : <Eye size={16} />} Blind mode</label></header>
    <div className='flex flex-wrap items-center gap-3'><label className='text-sm text-muted'>Challenge ID<input className='ml-2 w-56' value={challengeId} onChange={(event) => setChallengeId(event.target.value)} /></label><Button variant='outline' onClick={() => void loadQueue()}>Refresh queue</Button><span className='chip chip-neutral'>Rubric v{rubric?.version ?? '—'}</span></div>
    {error && <p role='alert' className='rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger'>{error}</p>}{message && <p role='status' className='rounded-lg border border-success/30 bg-success/5 p-3 text-sm text-success'>{message}</p>}
    <div className='grid gap-6 xl:grid-cols-[minmax(300px,0.75fr)_minmax(0,1.25fr)]'>
      <Card className='p-5'><h2 className='mb-4 font-heading text-xl font-semibold'>Applications · {queue.length}</h2><div className='space-y-3'>{queue.map((item) => <button key={item.application_id} onClick={() => { setSelected(item); setConflict(item.conflict_declaration === 'required' ? '' : item.conflict_declaration as 'none' | 'declared'); setScores({}); setRationale(''); setMessage(''); }} className={`w-full rounded-xl border p-4 text-left transition ${selected?.application_id === item.application_id ? 'border-primary/60 bg-primary/5' : 'border-border bg-raised/20 hover:border-primary/40'}`}><div className='flex items-start justify-between gap-2'><div><p className='font-semibold text-text'>{item.blind_label}</p><p className='mt-1 text-xs text-muted'>{item.sector} · {item.district}</p></div>{item.scoring_blocked ? <ShieldAlert className='h-4 w-4 text-danger' /> : item.scoring_submitted ? <StatusChip status='Verified' /> : <ShieldCheck className='h-4 w-4 text-success' />}</div><p className='mt-3 font-mono text-[10px] text-muted'>APP {item.application_id.slice(0, 12)}</p></button>)}</div></Card>
      <Card className='p-5 sm:p-6'>{!selected ? <div className='flex min-h-64 flex-col items-center justify-center text-center text-muted'><Star className='mb-3 text-primary' /><h2 className='font-heading text-xl font-semibold text-text'>Select an application</h2><p className='mt-2 text-sm'>Conflict declaration is the required first step.</p></div> : <div className='space-y-6'>
        <div><p className='text-xs uppercase tracking-widest text-muted'>Application review</p><h2 className='mt-1 font-heading text-2xl font-bold'>{selected.blind_label}</h2><p className='mt-1 text-sm text-muted'>{blind && !selected.scoring_submitted ? 'Applicant identity is hidden until scoring is submitted.' : selected.startup_name ?? 'Identity unavailable'} · {selected.sector}</p></div>
        <section className='rounded-xl border border-primary/30 bg-primary/5 p-4'><div className='mb-3 flex items-center gap-2'><ShieldCheck size={17} className='text-primary' /><h3 className='font-semibold'>Conflict declaration · required first</h3></div><div className='flex flex-wrap gap-2'><Button variant={conflict === 'none' ? 'primary' : 'outline'} onClick={() => setConflict('none')}>None</Button><Button variant={conflict === 'declared' ? 'danger' : 'outline'} onClick={() => setConflict('declared')}>Declared</Button></div>{conflict === 'declared' && <textarea className='mt-3 w-full' rows={3} value={conflictDetails} onChange={(event) => setConflictDetails(event.target.value)} placeholder='Describe the conflict relationship or interest.' />}{conflict && <Button className='mt-3' onClick={() => void submitConflict()} disabled={busy || (conflict === 'declared' && conflictDetails.trim().length < 3)}>{busy ? 'Saving…' : 'Record declaration'}</Button>}</section>
        {selected.scoring_blocked || conflict === 'declared' ? <div className='flex items-center gap-3 rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger'><LockKeyhole size={18} />This declared conflict is recorded. Scoring controls are blocked.</div> : conflict !== 'none' ? <div className='rounded-xl border border-warning/30 bg-warning/5 p-4 text-sm text-warning'>Choose and record “None” before score entry is enabled.</div> : <section className='space-y-4'><div className='flex items-center justify-between'><h3 className='font-heading text-xl font-semibold'>Rubric v{rubric?.version}</h3><span className='text-xs text-muted'>Score 1–5 · written reason required</span></div>{criteria.map((criterion) => <div key={criterion.key} className='grid gap-3 rounded-xl border border-border bg-raised/20 p-4 md:grid-cols-[1fr_110px]'><div><div className='flex flex-wrap items-center justify-between gap-2'><h4 className='font-semibold'>{criterion.label}</h4><span className='chip chip-neutral'>Weight {criterion.weight}%</span></div><textarea className='mt-3 w-full' rows={2} value={scores[criterion.key]?.reason ?? ''} onChange={(event) => setScores((current) => ({ ...current, [criterion.key]: { score: current[criterion.key]?.score ?? 3, reason: event.target.value } }))} placeholder='Explain the evidence behind this score.' /></div><label className='grid content-start gap-1 text-xs text-muted'>Score<select value={scores[criterion.key]?.score ?? 3} onChange={(event) => setScores((current) => ({ ...current, [criterion.key]: { score: Number(event.target.value), reason: current[criterion.key]?.reason ?? '' } }))}>{[1,2,3,4,5].map((score) => <option key={score} value={score}>{score} / 5</option>)}</select></label></div>)}<label className='grid gap-2 text-sm text-muted'>Overall rationale<textarea rows={3} value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder='Summarize the evidence and key limitations.' /></label><Button onClick={() => void submitScores()} disabled={busy || criteria.some((criterion) => (scores[criterion.key]?.reason?.trim().length ?? 0) < 5) || rationale.trim().length < 10}><Send size={15} />Submit scored evaluation</Button></section>}
      </div>}</Card>
    </div>
  </div>;
}
