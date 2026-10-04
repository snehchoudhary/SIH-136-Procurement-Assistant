import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, FileCheck2, FileDiff, MessageCircle, Plus, Send, ShieldCheck, Sparkles, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusChip } from '../components/ui/StatusChip';
import { LifecycleRail } from '../components/workflow/LifecycleRail';
import { WhyBlocked } from '../components/workflow/WhyBlocked';
import { apiFetch } from '../lib/api';

type ClauseMap = Record<string, string>;
type Version = { id: string; version: number; template_key: string; clauses: ClauseMap; change_note: string; approved: boolean; start_date: string; end_date: string };
type Agreement = { id: string; challenge_id: string; startup_id: string; startup_name?: string; status: string; terms_accepted: boolean; approval_chain: Array<{ user_id: string; name: string; role: string; approved: boolean; approved_at: string | null }> };
type Milestone = { id: string; code: string; title: string; amount: number; status: string; lifecycle_state: string; evidence_requirements: string[]; acceptance_criteria: string[]; linked_kpis: string[]; planned_start: string | null; planned_end: string | null };
type Message = { id: string; author_id: string; author_role: string; body: string; created_at: string };
type Applicant = { id: string; name: string; status: string };

const clauseLabels: Record<string, string> = {
  milestones: 'Milestones', evidence_requirements: 'Evidence requirements', data_access: 'Data access', ip: 'Intellectual property',
  security: 'Security and implemented controls', acceptance: 'Acceptance criteria', termination: 'Termination', payment_conditions: 'Payment conditions',
};
const clauseOrder = Object.keys(clauseLabels);

export default function AgreementWorkspacePage() {
  const [params] = useSearchParams();
  const [agreements, setAgreements] = useState<Agreement[]>([]);
  const [agreementId, setAgreementId] = useState(params.get('agreement') ?? '');
  const [versions, setVersions] = useState<Version[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [templates, setTemplates] = useState<Array<{ template_key: string; version: number; label: string; clauses: ClauseMap }>>([]);
  const [apps, setApps] = useState<Applicant[]>([]);
  const [startupId, setStartupId] = useState('');
  const [challengeId, setChallengeId] = useState('MH-MUNI-SC-001');
  const [approvers, setApprovers] = useState<Array<{ id: string; name: string; role: string }>>([]);
  const [approverIds, setApproverIds] = useState<string[]>([]);
  const [clauses, setClauses] = useState<ClauseMap>({});
  const [templateKey, setTemplateKey] = useState('standard-pilot');
  const [versionOne, setVersionOne] = useState<Version | null>(null);
  const [versionTwo, setVersionTwo] = useState<Version | null>(null);
  const [board, setBoard] = useState(false);
  const [milestoneView, setMilestoneView] = useState<'board' | 'timeline'>('board');
  const [questions, setQuestions] = useState<Message[]>([]);
  const [questionBody, setQuestionBody] = useState('');
  const [termsChecked, setTermsChecked] = useState(false);
  const [reason, setReason] = useState('');
  const [changeNote, setChangeNote] = useState('Update clause language after committee review.');
  const [editingNewVersion, setEditingNewVersion] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const role = (() => { try { return JSON.parse(atob((window.localStorage.getItem('pilotproof-token') ?? '').split('.')[1] || 'e30=')).role as string; } catch { return ''; } })();

  const refreshList = async () => {
    const response = await apiFetch('/api/pilots');
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Unable to load agreements.');
    setAgreements(result);
    if (!agreementId && result[0]) setAgreementId(result[0].id);
  };
  const loadAgreement = async (id: string) => {
    if (!id) return;
    const [versionResponse, milestoneResponse, questionResponse] = await Promise.all([
      apiFetch(`/api/pilots/${id}/versions`), apiFetch(`/api/pilots/${id}/milestones`), apiFetch(`/api/pilots/${id}/questions`),
    ]);
    if (versionResponse.ok) {
      const loaded = await versionResponse.json() as Version[];
      setVersions(loaded); setVersionOne(loaded.find((item) => item.version === 1) ?? null); setVersionTwo(loaded.length > 1 ? loaded[loaded.length - 1] : null);
      if (loaded.length) setClauses(loaded[loaded.length - 1].clauses);
    }
    if (milestoneResponse.ok) setMilestones((await milestoneResponse.json()).milestones ?? []);
    if (questionResponse.ok) setQuestions(await questionResponse.json());
  };

  useEffect(() => {
    if (!window.localStorage.getItem('pilotproof-token')) return;
    void Promise.all([
      refreshList(),
      apiFetch('/api/pilots/templates').then((response) => response.json()).then(setTemplates),
      apiFetch('/api/auth/demo-users').then((response) => response.json()).then(setApprovers),
      apiFetch('/api/startups').then((response) => response.json()).then((items) => setApps(items.map((item: Applicant) => item))),
    ]).catch((reason) => setError(reason instanceof Error ? reason.message : 'Unable to load agreement workspace.'));
  }, []);
  useEffect(() => { void loadAgreement(agreementId).catch((reason) => setError(reason instanceof Error ? reason.message : 'Unable to load agreement.')); }, [agreementId]);

  const selected = agreements.find((item) => item.id === agreementId);
  const latest = versions.length ? versions[versions.length - 1] : null;
  const allApproved = Boolean(selected?.approval_chain?.length && selected.approval_chain.every((item) => item.approved));
  const canStart = Boolean(selected?.status === 'Approved' && latest?.approved && selected.terms_accepted);
  const clausesForTemplate = (key: string) => templates.find((item) => item.template_key === key)?.clauses ?? {};

  if (!window.localStorage.getItem('pilotproof-token')) return <div className='space-y-6 p-6'><h1 className='font-heading text-3xl font-bold'>Pilot agreements</h1><DemoLoginPrompt /></div>;

  const createDraft = async () => {
    setBusy(true); setError(''); setMessage('');
    try {
      const response = await apiFetch('/api/pilots/drafts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ startup_id: startupId, challenge_id: challengeId, template_key: templateKey, clauses: Object.keys(clauses).length ? clauses : clausesForTemplate(templateKey), approver_user_ids: approverIds, change_note: 'Initial agreement draft' }) });
      const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Could not create agreement draft.');
      setAgreementId(result.id); setMessage(`Agreement draft ${result.id} created with three milestones.`); await refreshList(); await loadAgreement(result.id);
    } catch (reasonError) { setError(reasonError instanceof Error ? reasonError.message : 'Agreement draft failed.'); }
    finally { setBusy(false); }
  };
  const revise = async () => {
    setBusy(true); setError('');
    try {
      const response = await apiFetch(`/api/pilots/${agreementId}/versions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clauses, change_note: changeNote }) });
      const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Could not create agreement revision.');
      setEditingNewVersion(false); setVersionOne(versions[versions.length - 1] ?? null); setVersionTwo(result.version);
      setMessage(`Version ${result.version.version} created as a draft; all named approvals must be renewed.`); await refreshList(); await loadAgreement(agreementId);
    } catch (reasonError) { setError(reasonError instanceof Error ? reasonError.message : 'Revision failed.'); }
    finally { setBusy(false); }
  };
  const approve = async () => {
    setBusy(true); setError('');
    try {
      const response = await apiFetch(`/api/pilots/${agreementId}/approvals`, { method: 'POST' });
      const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Approval could not be recorded.');
      setMessage(result.all_approved ? 'All named approvers approved this agreement version.' : 'Your named approval was recorded; remaining approvers are still needed.'); await refreshList(); await loadAgreement(agreementId);
    } catch (reasonError) { setError(reasonError instanceof Error ? reasonError.message : 'Approval failed.'); }
    finally { setBusy(false); }
  };
  const startPilot = async () => {
    setBusy(true); setError('');
    try {
      const response = await apiFetch(`/api/pilots/${agreementId}/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }) });
      const result = await response.json(); if (!response.ok) throw new Error(result.detail || 'Pilot cannot start yet.');
      setMessage('Pilot started.'); await refreshList(); await loadAgreement(agreementId);
    } catch (reasonError) { setError(reasonError instanceof Error ? reasonError.message : 'Pilot start failed.'); }
    finally { setBusy(false); }
  };
  const acceptTerms = async () => {
    const response = await apiFetch(`/api/pilots/${agreementId}/terms`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ accepted: termsChecked }) });
    const result = await response.json(); if (!response.ok) { setError(result.detail || 'Terms acceptance failed.'); return; }
    setMessage('Terms acceptance recorded.'); await refreshList(); await loadAgreement(agreementId);
  };
  const postQuestion = async () => {
    if (!questionBody.trim()) return;
    const response = await apiFetch(`/api/pilots/${agreementId}/questions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body: questionBody }) });
    const result = await response.json(); if (!response.ok) { setError(result.detail || 'Could not send question.'); return; }
    setQuestionBody(''); await loadAgreement(agreementId);
  };

  return <div className='mx-auto max-w-7xl space-y-6 p-5 sm:p-8'>
    <header className='hero-wash flex flex-wrap items-end justify-between gap-4 rounded-[1.75rem] border border-border p-6'><div><p className='text-xs uppercase tracking-[0.18em] text-primary'>Agreement builder · versioned terms</p><h1 className='mt-2 font-heading text-3xl font-bold'>Pilot agreement workspace</h1><p className='mt-2 text-sm text-muted'>Review clauses, named approval chain, milestone plan and startup questions before the pilot begins.</p></div><label className='grid gap-1 text-xs text-muted'>Agreement<select className='min-w-64' value={agreementId} onChange={(event) => setAgreementId(event.target.value)}><option value=''>New agreement</option>{agreements.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.status}</option>)}</select></label></header>
    {error && <p role='alert' className='rounded-xl border border-danger/30 bg-danger/5 p-3 text-sm text-danger'>{error}</p>}{message && <p role='status' className='rounded-xl border border-success/30 bg-success/5 p-3 text-sm text-success'>{message}</p>}

    {!agreementId && role === 'officer' && <div className='grid gap-6 lg:grid-cols-[0.9fr_1.1fr]'><Card className='space-y-4 p-5'><h2 className='font-heading text-xl font-semibold'>Start from shortlist</h2><label className='grid gap-1 text-xs text-muted'>Shortlisted startup<select value={startupId} onChange={(event) => setStartupId(event.target.value)}><option value=''>Choose applicant</option>{apps.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.status}</option>)}</select></label><label className='grid gap-1 text-xs text-muted'>Challenge ID<input value={challengeId} onChange={(event) => setChallengeId(event.target.value)} /></label><label className='grid gap-1 text-xs text-muted'>Versioned template<select value={templateKey} onChange={(event) => { setTemplateKey(event.target.value); setClauses(clausesForTemplate(event.target.value)); }}><option value='standard-pilot'>Standard pilot (starter)</option>{templates.map((item) => <option key={`${item.template_key}-${item.version}`} value={item.template_key}>{item.label} · v{item.version}</option>)}</select></label><div><p className='mb-2 text-xs text-muted'>Named approval chain · all must approve</p><div className='space-y-2'>{approvers.map((approver) => <label key={approver.id} className='flex items-center gap-2 rounded-lg border border-border p-2 text-sm'><input type='checkbox' checked={approverIds.includes(approver.id)} onChange={(event) => setApproverIds((current) => event.target.checked ? [...current, approver.id] : current.filter((id) => id !== approver.id))} className='accent-primary' />{approver.name}<span className='ml-auto text-xs text-muted'>{approver.role}</span></label>)}</div></div><Button onClick={() => void createDraft()} disabled={busy || !startupId || approverIds.length === 0}>Create agreement draft</Button></Card><Card className='p-5'><h2 className='mb-4 font-heading text-xl font-semibold'>Clause library · editable before draft</h2><div className='space-y-3'>{clauseOrder.map((key) => <label key={key} className='grid gap-1 text-xs text-muted'>{clauseLabels[key]}<textarea rows={2} value={clauses[key] ?? clausesForTemplate(templateKey)[key] ?? ''} onChange={(event) => setClauses((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div></Card></div>}

    {selected && latest && <>
      <Card className='p-5'><div className='mb-4 flex flex-wrap items-center justify-between gap-3'><div><p className='text-xs uppercase tracking-widest text-muted'>Agreement status</p><h2 className='mt-1 font-heading text-2xl font-bold'>{selected.id} · v{latest.version}</h2><p className='mt-1 text-sm text-muted'>Status: {selected.status} · Terms accepted: {selected.terms_accepted ? 'Yes' : 'No'}</p></div><div className='flex flex-wrap gap-2'><Button variant='outline' onClick={() => setBoard(false)}>Agreement</Button><Button variant='outline' onClick={() => setBoard(true)}>Milestone board</Button></div></div><LifecycleRail currentStage={selected.status === 'Pilot Running' ? 'Pilot Running' : allApproved ? 'Agreement Approved' : 'Agreement Drafted'} blockedStage={!allApproved ? 'Agreement Approved' : !selected.terms_accepted ? 'Pilot Running' : undefined} /></Card>
      {!allApproved && <WhyBlocked dependency='approver' milestone='Agreement approval' />}{allApproved && !selected.terms_accepted && <WhyBlocked dependency='approver' milestone='Startup terms acceptance' />}

      {!board ? <>
        <div className='grid gap-6 xl:grid-cols-[0.95fr_1.05fr]'><Card className='p-5'><div className='mb-4 flex items-center gap-2'><FileCheck2 className='text-primary' /><h2 className='font-heading text-xl font-semibold'>Live agreement preview · v{latest.version}</h2></div><div className='agreement-document max-h-[70vh] space-y-5 overflow-y-auto rounded-xl border border-border bg-surface p-6 shadow-inner sm:p-8'><div className='border-b border-border pb-4 text-center'><p className='text-[10px] uppercase tracking-[0.2em] text-muted'>Pilot Evidence Passport · Agreement</p><h3 className='mt-2 font-heading text-2xl font-bold'>Pilot implementation agreement</h3><p className='mt-2 text-xs text-muted'>Version {latest.version} · {latest.start_date} through {latest.end_date}</p></div>{clauseOrder.map((key, index) => <section key={key}><h4 className='mb-1 text-sm font-bold'>{index + 1}. {clauseLabels[key]}</h4><p className='whitespace-pre-wrap text-sm leading-7 text-muted'>{latest.clauses?.[key] || 'Clause text not provided.'}</p></section>)}<div className='border-t border-border pt-4 text-xs text-muted'>Payment tracking may represent simulated settlement status. Terms do not make legal or regulatory certification claims.</div></div><p className='mt-3 flex items-center gap-2 text-xs text-muted'><Sparkles size={14} className='text-primary' />Version preview is a draft until all named approvers approve it.</p></Card>
          <div className='space-y-6'><Card className='p-5'><div className='mb-3 flex items-center gap-2'><ShieldCheck className='text-success' /><h2 className='font-heading text-xl font-semibold'>Approval chain</h2></div><div className='space-y-2'>{selected.approval_chain.map((item) => <div key={item.user_id} className='flex items-center gap-3 rounded-lg border border-border p-3'><span className={`flex h-7 w-7 items-center justify-center rounded-full ${item.approved ? 'bg-success/15 text-success' : 'bg-warning/10 text-warning'}`}>{item.approved ? <Check size={15} /> : <ChevronDown size={15} />}</span><div><p className='text-sm font-semibold'>{item.name}</p><p className='text-xs text-muted'>{item.role} · {item.approved ? `approved ${item.approved_at}` : 'awaiting approval'}</p></div></div>)}</div>{selected.approval_chain.some((item) => item.user_id === JSON.parse(atob((window.localStorage.getItem('pilotproof-token') ?? '').split('.')[1] || 'e30=')).sub && !item.approved) && <Button className='mt-4' onClick={() => void approve()} disabled={busy}>Approve current agreement version</Button>}</Card>
            {versions.length > 1 && <Card className='p-5'><div className='mb-4 flex items-center gap-2'><FileDiff className='text-primary' /><h2 className='font-heading text-xl font-semibold'>Version redline</h2></div><div className='mb-3 flex gap-2'>{versions.map((version) => <button key={version.version} onClick={() => { setVersionOne(versions[version.version - 2] ?? null); setVersionTwo(version); }} className='rounded-full border border-border px-3 py-1 text-xs'>v{version.version}</button>)}</div><div className='grid gap-3 md:grid-cols-2'><div className='rounded-lg border border-danger/25 bg-danger/5 p-3'><p className='mb-2 text-xs font-bold uppercase tracking-widest text-danger'>{versionOne ? `Previous · v${versionOne.version}` : 'Previous version'}</p>{clauseOrder.map((key) => <div key={key} className='mb-3'><p className='text-xs font-semibold'>{clauseLabels[key]}</p><p className='whitespace-pre-wrap text-xs text-muted'>{versionOne?.clauses[key] ?? 'No previous version'}</p></div>)}</div><div className='rounded-lg border border-success/25 bg-success/5 p-3'><p className='mb-2 text-xs font-bold uppercase tracking-widest text-success'>{versionTwo ? `Current · v${versionTwo.version}` : 'Current version'}</p>{clauseOrder.map((key) => { const oldText = versionOne?.clauses[key] ?? ''; const newText = versionTwo?.clauses[key] ?? latest.clauses[key] ?? ''; const changed = oldText !== newText; return <div key={key} className='mb-3'><p className='text-xs font-semibold'>{clauseLabels[key]}</p><p className={`whitespace-pre-wrap text-xs ${changed ? 'text-success' : 'text-muted'}`}>{newText}</p></div>; })}</div></div><p className='mt-3 text-xs text-muted'>{versionTwo?.change_note ?? latest.change_note}</p></Card>}
            {selected.status === 'Approved' && <Card className='space-y-3 p-5'><h2 className='font-heading text-xl font-semibold'>Startup terms acceptance</h2>{role === 'startup' ? <><label className='flex items-start gap-3 text-sm text-muted'><input type='checkbox' checked={termsChecked} onChange={(event) => setTermsChecked(event.target.checked)} className='mt-1 accent-primary' />I have reviewed agreement v{latest.version} and accept these terms.</label><Button onClick={() => void acceptTerms()} disabled={!termsChecked}>Record acceptance</Button></> : <p className='text-sm text-muted'>{selected.terms_accepted ? 'Startup accepted this version.' : 'Waiting for the startup account to accept the current version.'}</p>}</Card>}
          </div>
        </div>
        {versions.length > 0 && role === 'officer' && latest.approved && <Card className='space-y-4 p-5'><div className='flex flex-wrap items-end gap-3'><label className='grid min-w-72 flex-1 gap-1 text-xs text-muted'>Revision note<input value={changeNote} onChange={(event) => setChangeNote(event.target.value)} /></label><Button variant='outline' onClick={() => { setClauses({ ...latest.clauses }); setVersionOne(latest); setVersionTwo(null); setEditingNewVersion(true); }}><Plus size={15} />Edit clauses for v{latest.version + 1}</Button><Button onClick={() => void revise()} disabled={busy || !editingNewVersion}>Save new version</Button></div>{editingNewVersion && <div className='grid gap-3 md:grid-cols-2'>{clauseOrder.map((key) => <label key={key} className='grid gap-1 text-xs text-muted'>{clauseLabels[key]}<textarea rows={3} value={clauses[key] ?? ''} onChange={(event) => setClauses((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div>}</Card>}
        {allApproved && selected.terms_accepted && selected.status !== 'Pilot Running' && <Card className='flex flex-wrap items-end gap-3 p-5'><label className='grid min-w-72 flex-1 gap-1 text-xs text-muted'>Reason to start the pilot<input value={reason} onChange={(event) => setReason(event.target.value)} placeholder='State readiness confirmation.' /></label><Button onClick={() => void startPilot()} disabled={busy || reason.trim().length < 5}>Start approved pilot</Button></Card>}
      </> : <>
        <Card className='p-5'><div className='mb-4 flex flex-wrap items-center justify-between gap-3'><div><h2 className='font-heading text-xl font-semibold'>Milestone board</h2><p className='text-xs text-muted'>Each milestone shows evidence requirements, acceptance criteria, linked KPIs and planned dates.</p></div><div className='flex gap-2'><Button variant={milestoneView === 'board' ? 'primary' : 'outline'} onClick={() => setMilestoneView('board')}>By state</Button><Button variant={milestoneView === 'timeline' ? 'primary' : 'outline'} onClick={() => setMilestoneView('timeline')}>Gantt-lite</Button></div></div>{milestoneView === 'board' ? <div className='grid gap-4 lg:grid-cols-3'>{['Agreement Approved', 'Pilot Running', 'Evidence Submitted'].map((state) => <div key={state} className='rounded-xl border border-border bg-raised/20 p-3'><h3 className='mb-3 flex items-center justify-between text-sm font-semibold'>{state}<span className='chip chip-neutral'>{milestones.filter((item) => item.lifecycle_state === state).length}</span></h3><div className='space-y-3'>{milestones.filter((item) => item.lifecycle_state === state).map((item) => <Card key={item.id} className='p-4'><div className='flex items-start justify-between gap-2'><div><p className='font-mono text-xs text-primary'>{item.code}</p><h4 className='mt-1 font-semibold'>{item.title}</h4></div><StatusChip status={item.lifecycle_state === 'Pilot Running' ? 'Pending' : 'Needs Verification'} /></div><p className='mt-2 text-xs text-muted'>₹{item.amount.toLocaleString()}</p><p className='mt-2 text-xs text-muted'>{item.planned_start} → {item.planned_end}</p><details className='mt-3 text-xs'><summary className='cursor-pointer text-primary'>Requirements and acceptance</summary><p className='mt-2 text-muted'><b>Evidence:</b> {item.evidence_requirements.join('; ')}</p><p className='mt-1 text-muted'><b>Accept:</b> {item.acceptance_criteria.join('; ')}</p><p className='mt-1 text-muted'><b>Locked KPIs:</b> {item.linked_kpis.join(', ')}</p></details></Card>)}</div></div>)}</div> : <div className='space-y-3'>{milestones.map((item) => { const start = item.planned_start ? new Date(item.planned_start).getTime() : Date.now(); const end = item.planned_end ? new Date(item.planned_end).getTime() : start; const allStart = Math.min(...milestones.map((row) => new Date(row.planned_start ?? item.planned_start ?? '').getTime())); const allEnd = Math.max(...milestones.map((row) => new Date(row.planned_end ?? item.planned_end ?? '').getTime())); const left = allEnd > allStart ? ((start - allStart) / (allEnd - allStart)) * 100 : 0; const width = allEnd > allStart ? Math.max(8, ((end - start) / (allEnd - allStart)) * 100) : 25; return <div key={item.id} className='grid grid-cols-[180px_1fr] items-center gap-3'><div><p className='text-sm font-semibold'>{item.code} · {item.title}</p><p className='text-[10px] text-muted'>{item.planned_start} – {item.planned_end}</p></div><div className='relative h-9 rounded-lg bg-raised'><motion.div initial={{ width: 0 }} animate={{ width: `${width}%` }} className='absolute top-1 h-7 rounded-md bg-gradient-to-r from-primary to-primary' style={{ left: `${left}%` }} /><span className='absolute inset-0 flex items-center justify-center text-[10px] font-medium text-text mix-blend-difference'>{item.lifecycle_state}</span></div></div>; })}</div>}</Card>
        <LifecycleRail currentStage={selected.status === 'Pilot Running' ? 'Pilot Running' : 'Agreement Approved'} />
        {selected.status !== 'Pilot Running' && <WhyBlocked dependency={!allApproved ? 'approver' : 'evidence'} milestone={!allApproved ? 'Agreement approval' : 'Pilot start'} />}
      </>}

      <Card className='p-5'><div className='mb-4 flex items-center gap-2'><MessageCircle className='text-primary' /><h2 className='font-heading text-xl font-semibold'>Startup ↔ officer questions</h2></div><div className='mb-4 max-h-72 space-y-3 overflow-y-auto'>{questions.length ? questions.map((item) => <div key={item.id} className={`max-w-[90%] rounded-xl border p-3 ${item.author_role === 'startup' ? 'border-primary/25 bg-primary/5' : 'ml-auto border-border bg-raised/40'}`}><p className='mb-1 text-[10px] uppercase tracking-widest text-muted'>{item.author_role} · {new Date(item.created_at).toLocaleString()}</p><p className='whitespace-pre-wrap text-sm'>{item.body}</p></div>) : <p className='rounded-lg border border-dashed border-border p-5 text-center text-sm text-muted'>No questions yet. Use this thread to clarify a clause, evidence item or milestone.</p>}</div><div className='flex flex-wrap gap-2'><textarea className='min-h-12 flex-1' rows={2} value={questionBody} onChange={(event) => setQuestionBody(event.target.value)} placeholder='Ask or answer a question about this agreement.' /><Button onClick={() => void postQuestion()} disabled={!questionBody.trim()}><Send size={15} />Send</Button></div></Card>
    </>}
  </div>;
}
