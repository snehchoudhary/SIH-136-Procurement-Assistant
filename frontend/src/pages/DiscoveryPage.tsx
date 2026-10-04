import { AnimatePresence, motion } from 'framer-motion';
import { Building2, Check, ChevronDown, GitCompareArrows, Search, ShieldCheck, Upload, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { DemoLoginPrompt } from '../components/ui/DemoLoginPrompt';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { StatusChip } from '../components/ui/StatusChip';
import { apiFetch } from '../lib/api';

type Rule = { rule: string; status: string; reason: string; source: string; version: string; condition: string; fix_document: string | null };
type Startup = {
  id: string; name: string; city: string; sector: string; founded_year: number; turnover_lakhs: number;
  capability_tags: string[]; evidence_snippets: string[]; matched_evidence: string[]; synthetic: boolean;
  eligibility: { bucket: string; rules: Rule[]; exceptions: Array<{ exception: string; status: string; source: string; version: string; condition: string; human_review_required: boolean }> };
  fit_breakdown: Record<string, { label: string; value: number; explanation: string; evidence: string | null }>;
};
type DiscoveryResponse = { items: Startup[]; notice: string; policy_sources: Array<{ title: string; version: string; effective_date?: string; policy_type: string }> };

const factors = ['capability_evidence', 'domain_experience', 'language_support', 'deployment_readiness'];

function BucketChip({ bucket }: { bucket: string }) {
  const tone = bucket === 'Eligible' ? 'border-success/30 bg-success/10 text-success' : bucket === 'Not eligible' ? 'border-danger/30 bg-danger/10 text-danger' : 'border-warning/30 bg-warning/10 text-warning';
  return <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${tone}`}><span aria-hidden='true'>{bucket === 'Eligible' ? '✓' : bucket === 'Not eligible' ? '!' : '◷'}</span>{bucket}</span>;
}

function FitBreakdown({ startup }: { startup: Startup }) {
  return <div className='space-y-3'>
    <h4 className='text-xs font-semibold uppercase tracking-[0.15em] text-muted'>Fit breakdown · explainable factors</h4>
    {factors.map((key) => {
      const factor = startup.fit_breakdown[key];
      return <div key={key} title={factor.explanation} className='group/factor'>
        <div className='mb-1 flex items-center justify-between gap-2 text-xs'><span className='font-medium text-text'>{factor.label}</span><span className='font-mono text-muted'>{factor.value}/100</span></div>
        <div className='h-2 overflow-hidden rounded-full bg-raised' role='meter' aria-label={factor.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={factor.value}><div className='h-full rounded-full bg-gradient-to-r from-primary to-primary transition-[width] duration-700 ease-out' style={{ width: `${factor.value}%` }} /></div>
        <p className='mt-1 text-[11px] leading-relaxed text-muted'>{factor.explanation}{factor.evidence ? ` Evidence: “${factor.evidence}”` : ''}</p>
      </div>;
    })}
  </div>;
}

export default function DiscoveryPage() {
  const [data, setData] = useState<DiscoveryResponse | null>(null);
  const [query, setQuery] = useState('');
  const [sector, setSector] = useState('');
  const [eligibility, setEligibility] = useState('');
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStartup, setUploadStartup] = useState('');
  const [uploadAdapter, setUploadAdapter] = useState('GeM');
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const token = window.localStorage.getItem('pilotproof-token');

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    const load = async () => {
      setLoading(true); setError('');
      try {
        const params = new URLSearchParams();
        if (query.trim()) params.set('q', query.trim());
        if (sector) params.set('sector', sector);
        if (eligibility) params.set('eligibility', eligibility);
        const response = await apiFetch(`/api/discovery/startups?${params.toString()}`, { signal: controller.signal });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Unable to load startup discovery.');
        setData(result);
        setUploadStartup((current) => current || result.items?.[0]?.id || '');
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Unable to load startup profiles.');
      } finally { if (!controller.signal.aborted) setLoading(false); }
    };
    const timer = window.setTimeout(() => void load(), 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [token, query, sector, eligibility]);

  const startups = data?.items ?? [];
  const compared = useMemo(() => startups.filter((startup) => compareIds.includes(startup.id)), [startups, compareIds]);
  const toggleCompare = (id: string) => setCompareIds((current) => current.includes(id) ? current.filter((item) => item !== id) : current.length < 3 ? [...current, id] : current);

  const submitManualUpload = async () => {
    if (!uploadFile || !uploadStartup) return;
    setUploadBusy(true); setUploadMessage(''); setError('');
    try {
      const body = new FormData();
      body.append('document', uploadFile);
      const response = await apiFetch(`/api/discovery/startups/${encodeURIComponent(uploadStartup)}/manual-verification-upload?source_adapter=${encodeURIComponent(uploadAdapter)}`, {
        method: 'POST', body,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Manual-verification upload failed.');
      setUploadMessage(`Simulated ${result.source_adapter} adapter · ${result.adapter_status} · ${result.filename} stored for human review · SHA-256 ${result.sha256}`);
      setUploadFile(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Manual-verification upload failed.');
    } finally { setUploadBusy(false); }
  };

  if (!token) return <div className='space-y-6 p-6'><div><p className='text-xs uppercase tracking-widest text-primary'>Discover</p><h1 className='mt-2 font-heading text-3xl font-bold'>Evidence-backed startup matching</h1></div><DemoLoginPrompt /></div>;

  return (
    <div className='mx-auto max-w-[1500px] space-y-6 p-5 sm:p-7'>
      <header className='hero-wash relative overflow-hidden rounded-[1.75rem] border border-border p-6 sm:p-8'>
        <div className='relative z-10 flex flex-wrap items-end justify-between gap-4'><div><p className='text-xs font-semibold uppercase tracking-[0.2em] text-primary'>Discover · Applicant matching</p><h1 className='mt-3 font-heading text-3xl font-bold sm:text-4xl'>Find evidence that fits the challenge</h1><p className='mt-3 max-w-3xl text-sm text-muted'>Eligibility is rule-by-rule and source-linked. Capability fit shows four labelled factors—never a single unexplained rank.</p></div><Button variant='outline' disabled={compareIds.length === 0} onClick={() => setDrawerOpen(true)}><GitCompareArrows size={16} />Compare ({compareIds.length}/3)</Button></div>
      </header>

      <div className='grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)]'>
        <aside className='space-y-4'>
          <Card className='space-y-4 p-5'><div className='flex items-center gap-2'><ChevronDown size={16} className='text-primary' /><h2 className='font-heading text-lg font-semibold'>Filters</h2></div>
            <label className='grid gap-1.5 text-xs text-muted'>Search capability, sector or experience<div className='relative'><Search className='absolute left-3 top-3 h-4 w-4 text-muted' /><input className='w-full pl-9' value={query} onChange={(event) => setQuery(event.target.value)} placeholder='e.g. water, Marathi' /></div></label>
            <label className='grid gap-1.5 text-xs text-muted'>Sector<select value={sector} onChange={(event) => setSector(event.target.value)}><option value=''>All sectors</option>{['Water', 'Health', 'Education', 'Mobility', 'Agriculture'].map((item) => <option key={item}>{item}</option>)}</select></label>
            <label className='grid gap-1.5 text-xs text-muted'>Eligibility bucket<select value={eligibility} onChange={(event) => setEligibility(event.target.value)}><option value=''>All buckets</option><option>Eligible</option><option>Needs verification</option><option>Not eligible</option></select></label>
            <p className='border-t border-border pt-3 text-[11px] leading-relaxed text-muted'>Search uses PostgreSQL full-text matching when available; local test databases use a text fallback.</p>
          </Card>
          <Card className='p-5'><div className='flex items-center gap-2'><ShieldCheck className='h-4 w-4 text-success' /><h3 className='font-semibold'>Rule source</h3></div>{(data?.policy_sources ?? []).map((source) => <div key={`${source.title}-${source.version}`} className='mt-3 rounded-lg border border-border bg-raised/50 p-3'><p className='text-sm font-medium text-text'>{source.title}</p><p className='mt-1 font-mono text-xs text-muted'>Version {source.version}</p>{source.policy_type === 'eligibility' && <p className='mt-2 text-[11px] text-muted'>Synthetic demo rule, not an official government policy.</p>}</div>)}</Card>
        </aside>

        <section className='space-y-4'>
          <div className='flex items-center justify-between'><p className='text-sm text-muted'>{loading ? 'Refreshing matches…' : `${startups.length} synthetic startup profiles`}</p>{loading && <span className='h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent' />}</div>
          {error && <p role='alert' className='rounded-xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger'>{error}</p>}
          {!loading && startups.length === 0 && !error && <Card className='p-10 text-center'><Building2 className='mx-auto mb-3 text-muted' /><h2 className='font-heading text-xl font-semibold'>No profiles match these filters</h2><p className='mt-2 text-sm text-muted'>Try another sector or search term.</p></Card>}
          {startups.map((startup) => <Card key={startup.id} className='card-interactive p-5 sm:p-6'>
            <div className='grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]'>
              <div className='space-y-4'>
                <div className='flex flex-wrap items-start justify-between gap-3'><div><div className='flex items-center gap-2'><Building2 size={16} className='text-primary' /><h2 className='font-heading text-xl font-bold'>{startup.name}</h2></div><p className='mt-1 text-sm text-muted'>{startup.city} · {startup.sector} · Founded {startup.founded_year}</p></div><BucketChip bucket={startup.eligibility.bucket} /></div>
                <div className='flex flex-wrap gap-2'>{startup.capability_tags.map((tag) => <span key={tag} className='rounded-full border border-border bg-raised/60 px-2.5 py-1 text-xs text-muted'>{tag}</span>)}</div>
                <div className='space-y-2'><h3 className='text-xs font-semibold uppercase tracking-widest text-muted'>Eligibility rules and reasons</h3>{startup.eligibility.rules.map((rule) => <details key={rule.rule} className='rounded-lg border border-border bg-raised/30 p-3'><summary className='flex cursor-pointer list-none items-center justify-between gap-2 text-sm font-medium'><span>{rule.rule} · {rule.status}</span><ChevronDown size={14} className='text-muted' /></summary><p className='mt-2 text-xs text-muted'>{rule.reason}</p><p className='mt-2 text-[11px] text-muted'><span className='font-semibold text-text'>Source/version:</span> {rule.source} · {rule.version}</p><p className='mt-1 text-[11px] text-muted'><span className='font-semibold text-text'>Condition:</span> {rule.condition}</p>{rule.fix_document && <p className='mt-2 text-xs text-warning'><span className='font-semibold'>Next:</span> {rule.fix_document}</p>}</details>)}</div>
                {startup.eligibility.exceptions.map((exception) => <div key={exception.exception} className='rounded-lg border border-warning/35 bg-warning/5 p-3 text-xs'><p className='font-semibold text-warning'>{exception.exception} · human review required</p><p className='mt-1 text-muted'>{exception.source} · {exception.version} · {exception.condition}</p></div>)}
                <div className='space-y-2'><h3 className='text-xs font-semibold uppercase tracking-widest text-muted'>Matched evidence snippets</h3>{(startup.matched_evidence.length ? startup.matched_evidence : startup.evidence_snippets.slice(0, 2)).map((snippet) => <blockquote key={snippet} className='border-l-2 border-primary/50 pl-3 text-xs leading-relaxed text-muted'>“{snippet}”</blockquote>)}</div>
              </div>
              <div className='space-y-5 rounded-xl border border-border bg-raised/25 p-4'><FitBreakdown startup={startup} /><button className='flex items-center gap-2 text-xs font-medium text-primary' onClick={() => toggleCompare(startup.id)}><span className='flex h-4 w-4 items-center justify-center rounded border border-current'>{compareIds.includes(startup.id) && <Check size={12} />}</span>{compareIds.includes(startup.id) ? 'Added to comparison' : compareIds.length >= 3 ? 'Comparison full (3 maximum)' : 'Add to compare'}</button></div>
            </div>
          </Card>)}

          <Card className='p-5'><div className='mb-4 flex items-center gap-2'><Upload className='h-4 w-4 text-primary' /><h2 className='font-heading text-lg font-semibold'>Simulated adapters</h2></div><p className='mb-4 text-xs text-muted'>External integrations are mock adapters only. Uploaded documents are stored for human review; adapter verification is not automated.</p><div className='grid gap-3 md:grid-cols-3'>{['GeM', 'Startup India', 'DigiLocker'].map((adapter) => <div key={adapter} className='rounded-xl border border-border bg-raised/35 p-3'><div className='flex items-center justify-between gap-2'><span className='text-sm font-semibold'>{adapter}</span><StatusChip status='Simulated' /></div><p className='mt-2 text-xs text-muted'>No live external data connection.</p></div>)}</div><div className='mt-4 grid gap-3 sm:grid-cols-2'><label className='grid gap-1 text-xs text-muted'>Applicant<select value={uploadStartup} onChange={(event) => setUploadStartup(event.target.value)}>{startups.map((startup) => <option key={startup.id} value={startup.id}>{startup.name}</option>)}</select></label><label className='grid gap-1 text-xs text-muted'>Source adapter<select value={uploadAdapter} onChange={(event) => setUploadAdapter(event.target.value)}>{['GeM', 'Startup India', 'DigiLocker'].map((adapter) => <option key={adapter}>{adapter}</option>)}</select></label></div><label className='mt-4 flex cursor-pointer flex-wrap items-center gap-3 rounded-xl border border-dashed border-border p-4 text-sm text-muted hover:border-primary/50'><Upload size={16} />{uploadFile?.name || 'Attach source document for manual verification'}<input className='sr-only' type='file' accept='.pdf,.png,.jpg,.jpeg,.csv,.xlsx,.doc,.docx' onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} /></label><Button className='mt-3' variant='outline' onClick={() => void submitManualUpload()} disabled={!uploadFile || !uploadStartup || uploadBusy} isLoading={uploadBusy}><Upload size={15} />Submit for manual verification</Button>{uploadMessage && <p role='status' className='mt-3 break-all rounded-lg border border-success/30 bg-success/5 p-3 text-xs text-success'>{uploadMessage}</p>}</Card>
          <p className='text-xs leading-relaxed text-muted'>{data?.notice}</p>
        </section>
      </div>

      <AnimatePresence>{drawerOpen && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className='fixed inset-0 z-50 flex justify-end bg-text/65' onClick={() => setDrawerOpen(false)}><motion.aside initial={{ x: 500 }} animate={{ x: 0 }} exit={{ x: 500 }} transition={{ duration: 0.24 }} className='h-full w-full max-w-3xl overflow-y-auto border-l border-border bg-surface p-5 shadow-2xl sm:p-7' onClick={(event) => event.stopPropagation()}><div className='mb-6 flex items-center justify-between'><div><p className='text-xs uppercase tracking-widest text-muted'>Evidence comparison</p><h2 className='mt-1 font-heading text-2xl font-bold'>Compare startups</h2></div><button className='rounded-lg border border-border p-2 hover:bg-raised' onClick={() => setDrawerOpen(false)} aria-label='Close compare drawer'><X size={18} /></button></div><div className='grid gap-4 md:grid-cols-2'>{compared.map((startup) => <Card key={startup.id} className='p-4'><div className='flex items-start justify-between gap-2'><div><h3 className='font-heading font-semibold'>{startup.name}</h3><p className='mt-1 text-xs text-muted'>{startup.sector} · {startup.city}</p></div><button onClick={() => toggleCompare(startup.id)} aria-label={`Remove ${startup.name}`} className='text-muted hover:text-danger'><X size={16} /></button></div><div className='my-3'><BucketChip bucket={startup.eligibility.bucket} /></div><FitBreakdown startup={startup} /><ul className='mt-4 space-y-2 text-xs text-muted'>{startup.eligibility.rules.map((rule) => <li key={rule.rule}><span className='font-semibold text-text'>{rule.rule}:</span> {rule.status} — {rule.reason}</li>)}</ul></Card>)}</div></motion.aside></motion.div>}</AnimatePresence>
    </div>
  );
}
