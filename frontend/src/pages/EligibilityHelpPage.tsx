import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ClipboardCheck, FileCheck2, Upload } from 'lucide-react';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Card } from '../components/ui/Card';
import { StatusChip } from '../components/ui/StatusChip';
import { apiFetch } from '../lib/api';
import { Button } from '../components/ui/Button';

type Rule = { rule: string; status: string; reason: string; source: string; version: string; condition: string; fix_document: string | null };
type Applicant = { id: string; name: string; city: string; sector: string; eligibility: { bucket: string; rules: Rule[]; exceptions: Array<{ exception: string; source: string; version: string; condition: string; human_review_required: boolean }> } };

export default function EligibilityHelpPage() {
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [token] = useState(() => window.localStorage.getItem('pilotproof-token'));

  useEffect(() => {
    if (!token) return;
    void apiFetch('/api/discovery/eligibility/me').then(async (response) => {
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Unable to load eligibility details.');
      setApplicants(result.items ?? []);
      setNotice(result.notice ?? '');
      setSelectedId(result.items?.[0]?.id ?? '');
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to load eligibility details.'));
  }, [token]);

  if (!token) return <div className='space-y-6 p-6'><div><p className='text-xs uppercase tracking-widest text-primary'>Applicant help</p><h1 className='mt-2 font-heading text-3xl font-bold'>Why was I not eligible?</h1></div><DemoLoginPrompt /></div>;
  const selected = applicants.find((startup) => startup.id === selectedId);

  return (
    <div className='mx-auto max-w-5xl space-y-6 p-5 sm:p-8'>
      <header className='hero-wash rounded-[1.75rem] border border-border p-6 sm:p-8'><p className='text-xs font-semibold uppercase tracking-[0.2em] text-primary'>Startup view · Explainable checks</p><h1 className='mt-3 font-heading text-3xl font-bold sm:text-4xl'>Why was I not eligible?</h1><p className='mt-3 max-w-3xl text-sm text-muted'>See the exact condition, source version, and document that could resolve each gap. This is a synthetic demo explanation, not a government determination.</p></header>
      {error && <p role='alert' className='rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger'>{error}</p>}
      {notice && <p className='rounded-xl border border-border bg-raised/30 p-4 text-sm text-muted'>{notice}</p>}
      <Card className='p-5'><label className='grid max-w-xl gap-2 text-sm text-muted'>Synthetic applicant profile<select value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>{applicants.map((startup) => <option key={startup.id} value={startup.id}>{startup.name}</option>)}</select></label></Card>
      {!selected && !error && <Card className='p-6 text-sm text-muted'>No startup profile is linked to this account yet. Ask an officer to link your organization before requesting an eligibility explanation.</Card>}
      {selected && <>
        <div className='grid gap-4 sm:grid-cols-3'><Card className='p-4'><p className='text-xs uppercase tracking-widest text-muted'>Applicant</p><p className='mt-2 font-semibold'>{selected.name}</p><p className='text-xs text-muted'>{selected.city} · {selected.sector}</p></Card><Card className='p-4'><p className='text-xs uppercase tracking-widest text-muted'>Eligibility result</p><div className='mt-3'><StatusChip status={selected.eligibility.bucket === 'Eligible' ? 'Verified' : selected.eligibility.bucket === 'Not eligible' ? 'Disputed' : 'Needs Verification'} /></div></Card><Card className='p-4'><p className='text-xs uppercase tracking-widest text-muted'>Synthetic profile</p><p className='mt-2 flex items-center gap-2 text-sm text-warning'><AlertTriangle size={15} />Manual documents still need review</p></Card></div>
        <Card className='p-5 sm:p-6'><h2 className='mb-4 font-heading text-xl font-semibold'>Rule-by-rule explanation</h2><div className='space-y-4'>{selected.eligibility.rules.map((rule) => <article key={rule.rule} className='rounded-xl border border-border bg-raised/25 p-4'><div className='flex flex-wrap items-start justify-between gap-3'><div><h3 className='font-semibold'>{rule.rule}</h3><p className='mt-1 text-sm text-muted'>{rule.reason}</p></div><span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${rule.status === 'Eligible' ? 'border-success/30 bg-success/10 text-success' : rule.status === 'Not eligible' ? 'border-danger/30 bg-danger/10 text-danger' : 'border-warning/30 bg-warning/10 text-warning'}`}>{rule.status}</span></div><div className='mt-4 grid gap-3 text-xs sm:grid-cols-2'><p><span className='font-semibold'>Source and version:</span> {rule.source} · {rule.version}</p><p><span className='font-semibold'>Exact condition:</span> {rule.condition}</p></div>{rule.fix_document && <div className='mt-4 flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/5 p-3 text-sm'><FileCheck2 className='mt-0.5 h-4 w-4 shrink-0 text-warning' /><div><p className='font-semibold text-warning'>What could resolve this</p><p className='mt-1 text-muted'>{rule.fix_document}</p></div></div>}</article>)}</div>
          {selected.eligibility.exceptions.map((exception) => <div key={exception.exception} className='mt-4 rounded-xl border border-warning/35 bg-warning/5 p-4'><p className='font-semibold text-warning'>{exception.exception} · human review required</p><p className='mt-2 text-sm text-muted'>{exception.source} v{exception.version}: {exception.condition}</p></div>)}
        </Card>

        <Card className='p-5 sm:p-6'><div className='mb-4 flex items-center gap-2'><ClipboardCheck className='h-5 w-5 text-primary' /><h2 className='font-heading text-xl font-semibold'>Readiness checklist</h2></div><div className='grid gap-3 sm:grid-cols-2'>{['Current DPIIT recognition document', 'Audited turnover evidence for the stated financial year', 'Capability evidence tied to the challenge problem', 'Domain deployment references and contacts', 'Marathi/English support documentation', 'Deployment and field-support plan'].map((item) => <div key={item} className='flex items-start gap-2 rounded-lg border border-border bg-raised/25 p-3 text-sm'><CheckCircle2 className='mt-0.5 h-4 w-4 text-muted' />{item}</div>)}</div><label className='mt-5 flex cursor-pointer flex-wrap items-center gap-3 rounded-xl border border-dashed border-border p-4 text-sm text-muted hover:border-primary/50'><Upload size={16} />{fileName || 'Select document for manual verification'}<input type='file' className='sr-only' onChange={(event) => setFileName(event.target.files?.[0]?.name ?? '')} /></label>{fileName && <p className='mt-2 text-xs text-warning'>Selected: {fileName}. The demo records file selection locally; upload storage is not configured.</p>}<Button className='mt-4' variant='outline' disabled={!fileName}><Upload size={15} />Request manual verification</Button></Card>
      </>}
    </div>
  );
}
