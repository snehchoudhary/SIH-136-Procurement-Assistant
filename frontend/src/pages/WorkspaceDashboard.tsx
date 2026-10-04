import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowRight, FileCheck2, Fingerprint, MapPinned, RefreshCw, ScanSearch, WalletCards } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { PageHeader } from '../components/ui/PageHeader';
import { Skeleton } from '../components/ui/Skeleton';

type Pilot = { id: string; startup_name?: string; challenge_title?: string; status?: string; state?: string; created_at?: string };
type Milestone = { id: string; code?: string; title?: string; state: string; why_blocked?: string; days_in_state?: number };
type PilotPayload = Pilot[] | { items?: Pilot[] };
type MilestonePayload = Milestone[] | { items?: Milestone[] };

function listFrom<T>(value: T[] | { items?: T[] }): T[] { return Array.isArray(value) ? value : value.items || []; }

const shortcuts = [
  { to: '/evidence', label: 'Review evidence', detail: 'Inspect submissions, findings, and recomputed KPIs', icon: ScanSearch },
  { to: '/finance', label: 'Track payments', detail: 'View invoice and simulated settlement stages', icon: WalletCards },
  { to: '/scale', label: 'Assess transfer', detail: 'Compare pilot conditions with a receiving district', icon: MapPinned },
  { to: '/audit', label: 'Check audit trail', detail: 'Review recorded actions and chain integrity', icon: Fingerprint },
];

export default function WorkspaceDashboard() {
  const [pilots, setPilots] = useState<Pilot[] | null>(null);
  const [milestones, setMilestones] = useState<Milestone[] | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [pilotResponse, milestoneResponse] = await Promise.all([apiFetch('/api/pilots'), apiFetch('/api/milestones')]);
      const [pilotBody, milestoneBody] = await Promise.all([pilotResponse.json(), milestoneResponse.json()]);
      if (!pilotResponse.ok) throw new Error(pilotBody.detail || 'Could not load pilot records.');
      if (!milestoneResponse.ok) throw new Error(milestoneBody.detail || 'Could not load milestone records.');
      setPilots(listFrom<Pilot>(pilotBody)); setMilestones(listFrom<Milestone>(milestoneBody));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Workspace data could not be loaded.'); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const openMilestones = milestones?.filter((item) => item.state !== 'Payment Confirmed') || [];
  return <div className='mx-auto max-w-7xl space-y-8 p-5 sm:p-7 lg:p-9'>
    <PageHeader title='Your PilotProof workspace' eyebrow='PILOT LIFECYCLE' description='Follow pilot evidence, decisions, funding milestones, and transfer assessments from one place.' actionSlot={<button onClick={() => void load()} disabled={loading} aria-label='Refresh workspace data' className='inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text transition hover:bg-raised disabled:opacity-60'><RefreshCw size={16} className={loading ? 'animate-spin' : ''}/> Refresh</button>} />
    {error && <div role='alert' className='flex flex-wrap items-center justify-between gap-3 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-text'><span>{error}</span><button onClick={() => void load()} className='font-semibold text-primary underline underline-offset-2'>Try again</button></div>}
    <section aria-label='Pilot records' className='grid gap-4 md:grid-cols-2'>
      <article className='rounded-2xl border border-border bg-surface p-5 shadow-sm'><div className='flex items-start justify-between'><div><p className='text-xs font-semibold uppercase tracking-[.14em] text-muted'>Pilot agreements</p><p className='mt-2 text-3xl font-semibold tracking-tight text-text'>{loading ? '—' : pilots?.length ?? 0}</p></div><span className='rounded-xl bg-primary/10 p-3 text-primary'><FileCheck2 size={20}/></span></div><p className='mt-3 text-sm text-muted'>Agreements and approved pilot scopes recorded in this workspace.</p></article>
      <article className='rounded-2xl border border-border bg-surface p-5 shadow-sm'><div className='flex items-start justify-between'><div><p className='text-xs font-semibold uppercase tracking-[.14em] text-muted'>Open milestones</p><p className='mt-2 text-3xl font-semibold tracking-tight text-text'>{loading ? '—' : openMilestones.length}</p></div><span className='rounded-xl bg-warning/10 p-3 text-warning'><Activity size={20}/></span></div><p className='mt-3 text-sm text-muted'>Items still moving through validation, acceptance, and payment.</p></article>
    </section>
    <section><div className='mb-4'><p className='text-xs font-semibold uppercase tracking-[.16em] text-muted'>Workspace tools</p><h2 className='mt-1 font-heading text-xl font-semibold text-text'>Continue where the work happens</h2></div><div className='grid gap-3 sm:grid-cols-2 xl:grid-cols-4'>{shortcuts.map(({to,label,detail,icon:Icon})=><Link key={to} to={to} className='group rounded-2xl border border-border bg-surface p-5 transition duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'><span className='inline-flex rounded-xl bg-primary/10 p-2.5 text-primary'><Icon size={20}/></span><h3 className='mt-4 flex items-center justify-between font-semibold text-text'>{label}<ArrowRight size={16} className='text-muted transition group-hover:translate-x-1 group-hover:text-primary'/></h3><p className='mt-1 text-sm leading-relaxed text-muted'>{detail}</p></Link>)}</div></section>
    <section className='rounded-2xl border border-border bg-surface p-5 sm:p-6'><div className='mb-4 flex items-center justify-between gap-4'><div><p className='text-xs font-semibold uppercase tracking-[.16em] text-muted'>Live records</p><h2 className='mt-1 font-heading text-xl font-semibold text-text'>Recent milestones</h2></div><Link to='/agreements' className='text-sm font-semibold text-primary hover:underline'>Open agreements</Link></div>
      {loading ? <div className='space-y-3'><Skeleton className='h-16'/><Skeleton className='h-16'/></div> : openMilestones.length ? <ul className='divide-y divide-border'>{openMilestones.slice(0,5).map((item)=><li key={item.id} className='flex flex-wrap items-center justify-between gap-3 py-4 first:pt-1'><div className='min-w-0'><p className='truncate font-medium text-text'>{item.code ? `${item.code} · ` : ''}{item.title || 'Pilot milestone'}</p><p className='mt-1 text-xs text-muted'>{item.why_blocked || 'No blocker details recorded.'}</p></div><span className='rounded-full border border-border bg-raised px-3 py-1 text-xs font-medium text-text'>{item.state}</span></li>)}</ul> : !error ? <div className='rounded-xl border border-dashed border-border bg-raised/50 px-5 py-8 text-center'><p className='font-medium text-text'>No milestones recorded yet</p><p className='mt-1 text-sm text-muted'>Once an approved pilot agreement is created, its progress will appear here.</p><Link to='/agreements' className='mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary'>Open agreements <ArrowRight size={15}/></Link></div> : null}
    </section>
  </div>;
}
