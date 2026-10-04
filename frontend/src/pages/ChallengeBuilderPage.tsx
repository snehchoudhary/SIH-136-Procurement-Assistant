import { ArrowLeft, ArrowRight, Check, ClipboardCheck, FilePlus2, Languages, LoaderCircle, Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { apiFetch } from '../lib/api';

type Draft = {
  title: string;
  department: string;
  district: string;
  sector: string;
  problem_statement: string;
  outcomes: string[];
  metrics: string[];
  baseline: string;
  test_plan: string;
  test_duration_days: number | null;
  acceptance_criteria: string[];
  budget: number | null;
  deadline: string;
  input_language: 'en' | 'mr';
};

type SavedVersion = {
  version: number;
  title: string;
  problem_statement: string;
  outcomes: string[];
  metrics: string[];
  baseline: string;
  test_plan: string;
  acceptance_criteria: string[];
  change_note: string;
  is_published: boolean;
};

const emptyDraft: Draft = {
  title: '', department: 'Maharashtra State Innovation Society', district: 'Maharashtra', sector: '',
  problem_statement: '', outcomes: [], metrics: [], baseline: 'Baseline unavailable', test_plan: '',
  test_duration_days: null, acceptance_criteria: [], budget: null, deadline: '', input_language: 'en',
};

const copy = {
  en: {
    steps: ['Problem', 'Outcomes and metrics', 'Baseline and test plan', 'Review and publish'],
    eyebrow: 'Define · Challenge builder', title: 'Shape a measurable public problem',
    sub: 'A short guided flow creates a reviewable challenge. Nothing is published without officer approval.',
    titleLabel: 'Challenge title', problemLabel: 'Problem statement', dept: 'Department', district: 'District', sector: 'Sector',
    outcomes: 'Intended outcomes (one per line)', metrics: 'Measures (one per line)', baseline: 'Baseline evidence',
    baselineHint: 'Use observed figures only. If unavailable, keep “Baseline unavailable”.', plan: 'Test plan', duration: 'Pilot duration (days)',
    acceptance: 'Acceptance criteria (one per line)', budget: 'Indicative budget (₹)', deadline: 'Application deadline',
    draftAi: 'Draft with AI', aiNotice: 'AI-Drafted, needs review', save: 'Save draft', publish: 'Approve and publish',
    saveFirst: 'Save the challenge draft before requesting suggestions.', approve: 'I reviewed and approve this exact measurement plan for publication.',
    unavailable: 'Not provided', saved: 'Draft saved', publishMessage: 'Challenge published; measurement plan is locked.', publishedLabel: 'Published',
    diff: 'Review proposed edits', previous: 'Current', proposed: 'AI proposal', noInvent: 'No baseline was supplied. The proposal keeps it unavailable instead of inventing a number.',
    step: 'Step', continue: 'Continue', back: 'Back', signIn: 'Sign in with the synthetic demo Officer account to save and publish.',
    locale: 'Input language',
    revision: 'Create revised version', history: 'Version history and diff', published: 'Published', draftVersion: 'Draft version',
    from: 'Previous version', to: 'New version', revisionNote: 'Describe what changed',
  },
  mr: {
    steps: ['समस्या', 'परिणाम आणि मोजमाप', 'आधारभूत स्थिती आणि चाचणी योजना', 'तपासणी आणि प्रकाशन'],
    eyebrow: 'व्याख्या · आव्हान तयार करा', title: 'मोजता येणारी सार्वजनिक समस्या ठरवा',
    sub: 'हा मार्गदर्शित फॉर्म तपासता येणारे आव्हान तयार करतो. अधिकाऱ्याच्या मंजुरीशिवाय काहीही प्रकाशित होत नाही.',
    titleLabel: 'आव्हानाचे शीर्षक', problemLabel: 'समस्येचे वर्णन', dept: 'विभाग', district: 'जिल्हा', sector: 'क्षेत्र',
    outcomes: 'अपेक्षित परिणाम (प्रत्येक ओळीत एक)', metrics: 'मोजमाप (प्रत्येक ओळीत एक)', baseline: 'आधारभूत पुरावा',
    baselineHint: 'फक्त निरीक्षित आकडे वापरा. उपलब्ध नसल्यास “Baseline unavailable” ठेवा.', plan: 'चाचणी योजना', duration: 'पायलट कालावधी (दिवस)',
    acceptance: 'स्वीकृती निकष (प्रत्येक ओळीत एक)', budget: 'सूचक अर्थसंकल्प (₹)', deadline: 'अर्जाची अंतिम तारीख',
    draftAi: 'एआय मसुदा तयार करा', aiNotice: 'एआय-मसुदा, तपासणी आवश्यक', save: 'मसुदा जतन करा', publish: 'मंजूर करून प्रकाशित करा',
    saveFirst: 'सूचना मागण्यापूर्वी आव्हानाचा मसुदा जतन करा.', approve: 'मी हा मोजमाप आराखडा तपासला आणि प्रकाशित करण्यास मंजूर करतो/करते.',
    unavailable: 'दिलेली नाही', saved: 'मसुदा जतन झाला', publishMessage: 'आव्हान प्रकाशित झाले; मोजमाप आराखडा लॉक झाला.', publishedLabel: 'प्रकाशित',
    diff: 'सुचवलेले बदल तपासा', previous: 'सध्याचे', proposed: 'एआय सूचना', noInvent: 'आधारभूत आकडे दिलेले नाहीत. एआयने आकडा न बनवता उपलब्ध नाही असे ठेवले आहे.',
    step: 'पायरी', continue: 'पुढे', back: 'मागे', signIn: 'जतन व प्रकाशनासाठी कृत्रिम डेमो अधिकारी खात्यात प्रवेश करा.',
    locale: 'माहितीची भाषा',
    revision: 'नवीन सुधारित आवृत्ती तयार करा', history: 'आवृत्ती इतिहास आणि तुलना', published: 'प्रकाशित', draftVersion: 'मसुदा आवृत्ती',
    from: 'मागील आवृत्ती', to: 'नवीन आवृत्ती', revisionNote: 'काय बदलले ते लिहा',
  },
};

function lines(value: string): string[] {
  return value.split('\n').map((line) => line.trim()).filter(Boolean);
}

export default function ChallengeBuilderPage() {
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [challengeId, setChallengeId] = useState('');
  const [activeVersion, setActiveVersion] = useState(1);
  const [challengeStatus, setChallengeStatus] = useState('Draft');
  const [versions, setVersions] = useState<SavedVersion[]>([]);
  const [approved, setApproved] = useState(false);
  const [aiBefore, setAiBefore] = useState<Draft | null>(null);
  const [busy, setBusy] = useState<'save' | 'ai' | 'publish' | ''>('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const language = draft.input_language;
  const t = copy[language];
  const steps = t.steps;
  const token = window.localStorage.getItem('pilotproof-token');
  const draftExists = Boolean(challengeId);

  const refreshVersions = async (id: string) => {
    const response = await apiFetch(`/api/challenges/${id}/versions`);
    if (response.ok) setVersions(await response.json() as SavedVersion[]);
  };

  useEffect(() => {
    if (challengeId) void refreshVersions(challengeId);
  }, [challengeId]);

  const serialized = useMemo(() => ({
    ...draft,
    budget: draft.budget || null,
    deadline: draft.deadline || null,
    change_note: 'Measurement plan prepared in guided builder',
  }), [draft]);

  const update = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((current) => ({ ...current, [key]: value }));

  const saveDraft = async () => {
    setBusy('save'); setError(''); setMessage('');
    try {
      const isRevision = activeVersion > 1 || challengeStatus === 'Open';
      const response = await apiFetch(challengeId ? isRevision ? `/api/challenges/${challengeId}/versions/${activeVersion}` : `/api/challenges/${challengeId}/draft` : '/api/challenges/draft', {
        method: challengeId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(challengeId ? serialized : { ...serialized, title: draft.title || 'Untitled challenge' }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not save draft.');
      setChallengeId(result.id);
      setChallengeStatus(result.status);
      setActiveVersion(result.version.version);
      await refreshVersions(result.id);
      setMessage(`${t.saved} · ${result.id} · v${result.version.version}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save challenge draft.');
    } finally { setBusy(''); }
  };

  const draftWithAI = async () => {
    if (!draftExists) { setError(t.saveFirst); return; }
    setBusy('ai'); setError(''); setMessage('');
    const previous = { ...draft };
    try {
      const response = await apiFetch('/api/challenges/ai-draft', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_statement: draft.problem_statement, input_language: language }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'AI drafting is unavailable.');
      const proposal = result.proposal;
      setAiBefore(previous);
      setDraft((current) => ({
        ...current,
        outcomes: proposal.outcomes ?? current.outcomes,
        metrics: proposal.metrics ?? current.metrics,
        baseline: proposal.baseline || 'Baseline unavailable',
        test_plan: proposal.test_plan ?? current.test_plan,
        test_duration_days: proposal.test_duration_days ?? null,
        acceptance_criteria: proposal.acceptance_criteria ?? current.acceptance_criteria,
      }));
      setMessage(t.aiNotice);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'AI draft request failed.');
    } finally { setBusy(''); }
  };

  const publish = async () => {
    if (!approved) { setError(t.approve); return; }
    if (!draftExists) { setError(t.saveFirst); return; }
    setBusy('publish'); setError('');
    try {
      setBusy('publish');
      const saveResponse = await apiFetch(activeVersion > 1 || challengeStatus === 'Open' ? `/api/challenges/${challengeId}/versions/${activeVersion}` : `/api/challenges/${challengeId}/draft`, {
        method: activeVersion > 1 || challengeStatus === 'Open' ? 'PUT' : 'PUT',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(serialized),
      });
      const savedResult = await saveResponse.json();
      if (!saveResponse.ok) throw new Error(savedResult.detail || 'Could not save the measurement plan before publishing.');
      const response = await apiFetch(`/api/challenges/${challengeId}/publish`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ officer_approved: true }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not publish challenge.');
      setChallengeStatus('Open');
      await refreshVersions(challengeId);
      setMessage(t.publishMessage);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not publish challenge.');
    } finally { setBusy(''); }
  };

  const createRevision = async () => {
    if (!challengeId || challengeStatus !== 'Open') return;
    setBusy('save'); setError(''); setMessage('');
    try {
      const response = await apiFetch(`/api/challenges/${challengeId}/versions`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...serialized, change_note: draft.test_plan || 'Measurement plan revision' }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Could not create revised version.');
      setActiveVersion(result.version.version);
      setChallengeStatus('Version draft');
      setApproved(false);
      await refreshVersions(challengeId);
      setStep(3);
      setMessage(`${t.draftVersion} · v${result.version.version}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not create revised version.');
    } finally { setBusy(''); }
  };

  if (!token) return <div className='mx-auto max-w-5xl space-y-8 p-6'><h1 className='font-heading text-3xl font-bold'>{t.title}</h1><p className='text-muted'>{t.signIn}</p><DemoLoginPrompt /></div>;

  return (
    <div className='mx-auto max-w-5xl space-y-7 p-5 pb-16 sm:p-8'>
      <header className='hero-wash relative overflow-hidden rounded-[1.75rem] border border-border p-6 sm:p-8'>
        <div className='relative z-10 flex flex-wrap items-start justify-between gap-4'>
          <div><p className='text-xs font-semibold uppercase tracking-[0.2em] text-primary'>{t.eyebrow}</p><h1 className='mt-3 max-w-2xl font-heading text-3xl font-bold sm:text-4xl'>{t.title}</h1><p className='mt-3 max-w-2xl text-sm text-muted sm:text-base'>{t.sub}</p></div>
          <button className='btn btn-ghost' type='button' onClick={() => update('input_language', language === 'en' ? 'mr' : 'en')}><Languages size={16} />{language === 'en' ? 'मराठी' : 'English'}</button>
        </div>
        <div className='mt-8 grid grid-cols-2 gap-2 sm:grid-cols-4'>
          {steps.map((label, index) => <button key={label} type='button' onClick={() => setStep(index)} className={`rounded-xl border p-3 text-left transition-all ${step === index ? 'border-primary/50 bg-primary/10 text-text' : index < step ? 'border-success/30 bg-success/5 text-muted' : 'border-border bg-surface/50 text-muted'}`}><span className='mb-2 flex items-center gap-2 text-[10px] uppercase tracking-widest'><span className='flex h-5 w-5 items-center justify-center rounded-full bg-raised'>{index < step ? <Check size={12} /> : index + 1}</span>{t.step} {index + 1}</span><span className='text-sm font-semibold'>{label}</span></button>)}
        </div>
      </header>

      <div className='grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]'>
        <Card className='p-5 sm:p-7'>
          <div className='mb-6 flex items-center justify-between'><div><p className='text-xs uppercase tracking-[0.17em] text-muted'>{t.step} {step + 1} / 4</p><h2 className='mt-1 font-heading text-2xl font-semibold'>{steps[step]}</h2></div>{busy && <LoaderCircle className='animate-spin text-primary' />}</div>

          {step === 0 && <div className='grid gap-4 sm:grid-cols-2'>
            <label className='grid gap-1.5 text-sm text-muted sm:col-span-2'>{t.titleLabel}<input value={draft.title} onChange={(e) => update('title', e.target.value)} placeholder={language === 'en' ? 'e.g. Faster village water quality reporting' : 'उदा. गावातील पाणी गुणवत्ता अहवाल सुधारणा'} /></label>
            <label className='grid gap-1.5 text-sm text-muted sm:col-span-2'>{t.problemLabel}<textarea rows={5} value={draft.problem_statement} onChange={(e) => update('problem_statement', e.target.value)} placeholder={language === 'en' ? 'Describe who is affected, where the issue occurs, and what current process is difficult.' : 'कोण प्रभावित आहे, समस्या कुठे उद्भवते आणि सध्याची प्रक्रिया का कठीण आहे ते लिहा.'} /></label>
            <label className='grid gap-1.5 text-sm text-muted'>{t.dept}<input value={draft.department} onChange={(e) => update('department', e.target.value)} /></label>
            <label className='grid gap-1.5 text-sm text-muted'>{t.district}<input value={draft.district} onChange={(e) => update('district', e.target.value)} /></label>
            <label className='grid gap-1.5 text-sm text-muted'>{t.sector}<input value={draft.sector} onChange={(e) => update('sector', e.target.value)} /></label>
          </div>}

          {step === 1 && <div className='space-y-5'>
            <label className='grid gap-1.5 text-sm text-muted'>{t.outcomes}<textarea rows={5} value={draft.outcomes.join('\n')} onChange={(e) => update('outcomes', lines(e.target.value))} placeholder={'Faster service response\nFewer repeat visits'} /></label>
            <label className='grid gap-1.5 text-sm text-muted'>{t.metrics}<textarea rows={5} value={draft.metrics.join('\n')} onChange={(e) => update('metrics', lines(e.target.value))} placeholder={'Median time from request to resolution\nShare completed within agreed window'} /></label>
            <p className='rounded-xl border border-primary/25 bg-primary/5 p-3 text-xs text-muted'>Measures should name a unit, source, sample and observation window. Do not publish unexplained percentages.</p>
          </div>}

          {step === 2 && <div className='space-y-5'>
            <label className='grid gap-1.5 text-sm text-muted'>{t.baseline}<textarea rows={3} value={draft.baseline} onChange={(e) => update('baseline', e.target.value)} /></label>
            <p className='-mt-3 text-xs text-muted'>{t.baselineHint}</p>
            <div className='grid gap-4 sm:grid-cols-2'>
              <label className='grid gap-1.5 text-sm text-muted sm:col-span-2'>{t.plan}<textarea rows={4} value={draft.test_plan} onChange={(e) => update('test_plan', e.target.value)} placeholder='Locations, sample, data source, review cadence, and risks' /></label>
              <label className='grid gap-1.5 text-sm text-muted'>{t.duration}<input type='number' min='1' max='365' value={draft.test_duration_days ?? ''} onChange={(e) => update('test_duration_days', e.target.value ? Number(e.target.value) : null)} placeholder={t.unavailable} /></label>
              <label className='grid gap-1.5 text-sm text-muted'>{t.budget}<input type='number' min='0' value={draft.budget ?? ''} onChange={(e) => update('budget', e.target.value ? Number(e.target.value) : null)} placeholder={t.unavailable} /></label>
              <label className='grid gap-1.5 text-sm text-muted'>{t.deadline}<input type='date' value={draft.deadline} onChange={(e) => update('deadline', e.target.value)} /></label>
              <label className='grid gap-1.5 text-sm text-muted sm:col-span-2'>{t.acceptance}<textarea rows={4} value={draft.acceptance_criteria.join('\n')} onChange={(e) => update('acceptance_criteria', lines(e.target.value))} placeholder={'Evidence source and measurement method accepted\nOutcome reviewed by named validator'} /></label>
            </div>
          </div>}

          {step === 3 && <div className='space-y-5'>
            <div className='rounded-xl border border-border bg-raised/40 p-4'><p className='text-xs uppercase tracking-widest text-muted'>{t.problemLabel}</p><p className='mt-2 text-sm'>{draft.problem_statement || '—'}</p></div>
            <div className='grid gap-4 sm:grid-cols-2'><div className='rounded-xl border border-border p-4'><p className='text-xs uppercase tracking-widest text-muted'>{t.outcomes}</p><ul className='mt-2 list-disc space-y-1 pl-5 text-sm'>{draft.outcomes.map((item) => <li key={item}>{item}</li>)}</ul></div><div className='rounded-xl border border-border p-4'><p className='text-xs uppercase tracking-widest text-muted'>{t.metrics}</p><ul className='mt-2 list-disc space-y-1 pl-5 text-sm'>{draft.metrics.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
            <div className='rounded-xl border border-border p-4'><p className='text-xs uppercase tracking-widest text-muted'>{t.baseline}</p><p className='mt-2 text-sm'>{draft.baseline}</p><p className='mt-3 text-xs text-muted'>{draft.test_plan || 'Test plan not specified'}{draft.test_duration_days ? ` · ${draft.test_duration_days} days` : ''}</p></div>
            {aiBefore && <Card className='border-primary/30 p-4'><div className='mb-3 flex items-center gap-2 text-primary'><Sparkles size={16} /><span className='text-sm font-semibold'>{t.diff}</span><span className='chip chip-ai'>{t.aiNotice}</span></div><p className='mb-3 text-xs text-muted'>{t.noInvent}</p><div className='grid gap-3 sm:grid-cols-2'>{[
              ['Outcomes', aiBefore.outcomes.join('\n'), draft.outcomes.join('\n')],['Metrics', aiBefore.metrics.join('\n'), draft.metrics.join('\n')],['Baseline', aiBefore.baseline, draft.baseline],['Test plan', aiBefore.test_plan, draft.test_plan],['Acceptance', aiBefore.acceptance_criteria.join('\n'), draft.acceptance_criteria.join('\n')],
            ].map(([label, before, proposed]) => <div key={label} className='rounded-lg border border-border p-3'><p className='mb-2 text-xs font-semibold uppercase tracking-widest text-muted'>{label}</p><p className='text-xs text-muted line-through decoration-danger/70'>{before || t.unavailable}</p><p className='mt-1 whitespace-pre-wrap text-sm text-success'>{proposed || t.unavailable}</p></div>)}</div></Card>}
            <label className='flex items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4 text-sm'><input className='mt-1 accent-primary' type='checkbox' checked={approved} onChange={(e) => setApproved(e.target.checked)} /><span>{t.approve}</span></label>
          </div>}

          {error && <p role='alert' className='mt-5 rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger'>{error}</p>}
          {message && <p role='status' className='mt-5 rounded-lg border border-success/30 bg-success/5 p-3 text-sm text-success'>{message}</p>}
          {step === 3 && versions.length > 0 && <div className='mt-6 space-y-3'>
            <h3 className='font-heading text-lg font-semibold'>{t.history}</h3>
            <div className='flex flex-wrap gap-2'>{versions.map((version) => <span key={version.version} className={`rounded-full border px-3 py-1 text-xs ${version.is_published ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'}`}>v{version.version} · {version.is_published ? t.publishedLabel : t.draftVersion}</span>)}</div>
            {versions.length > 1 && (() => {
              const before = versions[versions.length - 2];
              const after = versions[versions.length - 1];
              const rows: Array<[string, string, string]> = [
                ['Problem', before.problem_statement, after.problem_statement],
                ['Outcomes', before.outcomes.join('\n'), after.outcomes.join('\n')],
                ['Metrics', before.metrics.join('\n'), after.metrics.join('\n')],
                ['Baseline', before.baseline, after.baseline],
                ['Test plan', before.test_plan, after.test_plan],
                ['Acceptance criteria', before.acceptance_criteria.join('\n'), after.acceptance_criteria.join('\n')],
              ];
              return <div className='overflow-hidden rounded-xl border border-border'><div className='grid grid-cols-[140px_1fr_1fr] bg-raised/60 px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-muted'><span>Field</span><span>{t.from} · v{before.version}</span><span>{t.to} · v{after.version}</span></div>{rows.map(([label, oldValue, newValue]) => <div key={label} className='grid grid-cols-[140px_1fr_1fr] gap-2 border-t border-border px-3 py-3 text-xs'><span className='font-semibold text-muted'>{label}</span><span className='whitespace-pre-wrap text-danger'>{oldValue || t.unavailable}</span><span className='whitespace-pre-wrap text-success'>{newValue || t.unavailable}</span></div>)}</div>;
            })()}
            {challengeStatus === 'Open' && <Button variant='outline' onClick={() => void createRevision()} disabled={busy !== ''}><FilePlus2 size={16} />{t.revision}</Button>}
          </div>}

          <div className='mt-7 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5'>
            <Button variant='outline' disabled={step === 0} onClick={() => setStep((current) => current - 1)}><ArrowLeft size={16} />{t.back}</Button>
            <div className='flex flex-wrap gap-2'>
              {step === 0 && <Button variant='outline' onClick={() => void saveDraft()} disabled={busy !== '' || (challengeStatus === 'Open' && activeVersion === 1)}><FilePlus2 size={16} />{t.save}</Button>}
              {step > 0 && step < 3 && <Button variant='outline' onClick={() => void saveDraft()} disabled={busy !== '' || (challengeStatus === 'Open' && activeVersion === 1)}>{t.save}</Button>}
              {step === 2 && <Button variant='outline' onClick={() => void draftWithAI()} disabled={busy !== ''}><Sparkles size={16} />{t.draftAi}</Button>}
              {step < 3 ? <Button onClick={() => { setError(''); setStep((current) => Math.min(3, current + 1)); }}><ArrowRight size={16} />{t.continue}</Button> : <Button onClick={() => void publish()} disabled={busy !== '' || !approved}><ClipboardCheck size={16} />{t.publish}</Button>}
            </div>
          </div>
        </Card>

        <aside className='space-y-4'>
          <Card className='p-5'><p className='text-xs uppercase tracking-widest text-muted'>Measurement integrity</p><h3 className='mt-2 font-heading text-lg font-semibold'>No invented baseline</h3><p className='mt-2 text-sm text-muted'>When evidence is missing, the form preserves “Baseline unavailable”. Targets and durations remain blank until an officer sets them.</p></Card>
          <Card className='p-5'><p className='text-xs uppercase tracking-widest text-muted'>Versioning</p><h3 className='mt-2 font-heading text-lg font-semibold'>Lock on publish</h3><p className='mt-2 text-sm text-muted'>Publishing locks this measurement version. Later changes must be saved as a new version and approved before publication.</p>{challengeId && <p className='mt-3 font-mono text-xs text-primary'>{challengeId}</p>}</Card>
          <Link className='btn btn-ghost w-full' to='/discover'>Review applicant discovery <ArrowRight size={15} /></Link>
        </aside>
      </div>
    </div>
  );
}
