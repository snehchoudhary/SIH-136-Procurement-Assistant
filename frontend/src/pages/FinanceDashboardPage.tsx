import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BadgeCheck, Banknote, Clock3, FileCheck2, FileUp, LockKeyhole, RefreshCw, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusChip } from '../components/ui/StatusChip';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type Item = { id: string; agreement_id: string; code: string; title: string; amount: number; state: string; days_in_state: number; why_blocked: string; invoice: null | { id: string; amount: number; approval_status: string; reference?: string; sha256?: string }; payment: null | { id: string; status: string; reference?: string; simulated: boolean } };
type Payload = { items: Item[]; settlement_notice: string; funds_notice: string; states: string[] };
const financeRole = () => (JSON.parse(localStorage.getItem('pilotproof-user') || '{}') as { role?: string }).role || 'officer';

export default function FinanceDashboardPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const role = financeRole();
  const load = useCallback(async () => {
    setError('');
    try { const res = await apiFetch('/api/milestones'); if (!res.ok) throw new Error((await res.json()).detail || 'Could not load finance pipeline.'); setData(await res.json()); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not reach finance service.'); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const perform = async (item: Item, action: string, payload?: Record<string, string | number>) => {
    setBusy(`${item.id}:${action}`); setError('');
    try {
      let init: RequestInit = { method: 'POST' }, path = `/api/milestones/${item.id}/${action}`;
      if (action === 'invoice') {
        const input = document.querySelector<HTMLInputElement>(`#invoice-${item.id}`);
        const file = input?.files?.[0];
        const amount = Number(document.querySelector<HTMLInputElement>(`#amount-${item.id}`)?.value || 0);
        if (!file) throw new Error('Choose an invoice file first.');
        const form = new FormData(); form.append('file', file); form.append('amount', String(amount)); form.append('reference', `INV-${item.code}`); init.body = form;
      } else if (payload) {
        const params = new URLSearchParams(payload as Record<string, string>);
        path += `?${params.toString()}`;
      }
      const res = await apiFetch(path, init); const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.detail || 'Action could not be completed.');
      await load();
    } catch (e) { setError(e instanceof Error ? e.message : 'Action could not be completed.'); }
    finally { setBusy(''); }
  };
  const stages = useMemo(() => (data?.states || []).map((state) => ({ name: state.replace('Payment ', ''), count: data?.items.filter((item) => item.state === state).length || 0 })), [data]);
  const total = data?.items.length || 0;
  return <div className='mx-auto max-w-7xl space-y-6 p-6 lg:p-9'>
    <PageHeader title='Finance & settlement' description='A milestone moves through validation, acceptance, invoice approval, and simulated settlement in order.' />
    <div className='grid gap-3 md:grid-cols-3'>
      <div className='rounded-2xl border border-warning/30 bg-warning/10 px-5 py-4 text-text md:col-span-2'><div className='flex items-center gap-2 font-semibold'><ShieldAlert size={18}/> Simulated settlement. No real funds move.</div><p className='mt-1 text-sm text-warning'>The platform tracks sanctioned funding and acceptance; it does not hold public money.</p></div>
      <div className='flex items-center justify-between rounded-2xl border border-border bg-surface px-5 py-4'><div><p className='text-xs uppercase tracking-[.16em] text-muted'>Milestones tracked</p><p className='mt-1 text-2xl font-semibold text-text'>{total}</p></div><Banknote className='text-primary'/></div>
    </div>
    {error && <div role='alert' className='rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger'>{error}</div>}
    <section className='grid gap-6 lg:grid-cols-[1.5fr_1fr]'>
      <div className='rounded-2xl border border-border bg-surface p-5'><div className='mb-4 flex items-center justify-between'><div><h2 className='font-semibold text-text'>Funding pipeline</h2><p className='text-sm text-muted'>Milestones grouped by their explicit state</p></div><button onClick={() => void load()} className='rounded-lg p-2 text-muted hover:bg-raised' aria-label='Refresh finance data'><RefreshCw size={17}/></button></div>
        {!data ? <div className='space-y-3'><Skeleton className='h-10'/><Skeleton className='h-48'/></div> : <div className='h-64'><ResponsiveContainer width='100%' height='100%'><BarChart data={stages} margin={{ left: -20, right: 8, bottom: 18 }}><CartesianGrid vertical={false} strokeDasharray='3 4' stroke='rgb(var(--border))'/><XAxis dataKey='name' angle={-18} textAnchor='end' interval={0} tick={{ fontSize: 10, fill: 'rgb(var(--muted))' }} axisLine={false} tickLine={false}/><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'rgb(var(--muted))' }} axisLine={false} tickLine={false}/><Tooltip/><Bar dataKey='count' fill='rgb(var(--primary))' radius={[6,6,0,0]} isAnimationActive animationDuration={650}/></BarChart></ResponsiveContainer></div>}
      </div>
      <div className='rounded-2xl border border-border bg-surface p-5'><div className='flex items-center gap-2'><Clock3 size={18} className='text-primary'/><h2 className='font-semibold text-text'>Aging at a glance</h2></div><p className='mb-4 mt-1 text-sm text-muted'>Current days in state by milestone</p>{data?.items.length ? <div className='space-y-3'>{data.items.slice(0,5).map((x)=><div key={x.id}><div className='mb-1 flex justify-between text-xs'><span className='truncate text-text'>{x.code} · {x.title}</span><strong className='text-muted'>{x.days_in_state}d</strong></div><div className='h-1.5 rounded-full bg-raised'><div className='h-full rounded-full bg-gradient-to-r from-warning to-danger' style={{width:`${Math.min(100, Math.max(6, x.days_in_state*6))}%`}}/></div></div>)}</div>:<p className='rounded-xl bg-raised p-4 text-sm text-muted'>No milestones to age yet.</p>}</div>
    </section>
    <section className='space-y-3'><div><h2 className='text-lg font-semibold text-text'>Milestone ledger</h2><p className='text-sm text-muted'>Each action unlocks only after the preceding record exists.</p></div>
      {!data ? <Skeleton className='h-40'/> : data.items.length === 0 ? <div className='rounded-2xl border border-dashed border-border bg-surface p-8 text-center text-sm text-muted'>No milestones recorded yet. Start with an approved pilot agreement.</div> : data.items.map((item) => <article key={item.id} className='rounded-2xl border border-border bg-surface p-5 shadow-sm'><div className='flex flex-wrap items-start justify-between gap-3'><div><p className='text-xs font-semibold uppercase tracking-[.15em] text-muted'>{item.code} · {item.agreement_id}</p><h3 className='mt-1 font-semibold text-text'>{item.title}</h3></div><span className='rounded-full border border-border bg-raised px-3 py-1 text-xs font-medium text-text'>{item.state}</span></div><p className='mt-3 flex items-start gap-2 text-sm text-muted'><LockKeyhole size={15} className='mt-0.5 shrink-0'/>{item.why_blocked}</p>
        {item.invoice && <p className='mt-2 text-xs text-muted'>Invoice {item.invoice.reference || item.invoice.id.slice(0,8)} · ₹{item.invoice.amount.toLocaleString('en-IN')} · {item.invoice.approval_status}{item.invoice.sha256 ? ` · SHA-256 ${item.invoice.sha256.slice(0,12)}…` : ''}</p>}
        {item.payment && <p className='mt-2 rounded-lg bg-success/10 px-3 py-2 text-xs font-medium text-success'>Mock bank reference {item.payment.reference} · {item.payment.status} · Simulated</p>}
        <div className='mt-4 flex flex-wrap items-center gap-3'>
          {item.state === 'Validated' && role === 'officer' && <Button disabled={!!busy} onClick={()=>void perform(item,'accept-evidence')}><BadgeCheck size={16}/>Accept validated evidence</Button>}
          {item.state === 'Accepted' && role === 'startup' && <div className='flex flex-wrap items-end gap-3'><label className='text-xs text-muted'>Invoice amount (₹)<input id={`amount-${item.id}`} type='number' min='1' defaultValue={item.amount || ''} className='mt-1 block w-36 rounded-lg border border-border bg-bg px-3 py-2 text-sm text-text'/></label><label className='text-xs text-muted'>Invoice file<input id={`invoice-${item.id}`} type='file' accept='.pdf,.png,.jpg,.jpeg' className='mt-1 block max-w-56 text-xs text-muted'/></label><Button disabled={!!busy} onClick={()=>void perform(item,'invoice')}><FileUp size={16}/>Submit invoice</Button></div>}
          {item.state === 'Accepted' && item.invoice && item.invoice.approval_status === 'Submitted' && role === 'finance' && <Button disabled={!!busy} onClick={()=>void perform(item,'approve-invoice',{invoice_id:item.invoice!.id})}><FileCheck2 size={16}/>Approve invoice</Button>}
          {item.state === 'Invoice Approved' && item.invoice && role === 'finance' && <Button disabled={!!busy} onClick={()=>void perform(item,'initiate-payment',{invoice_id:item.invoice!.id,idempotency_key:`finance-${item.id}-${item.invoice!.id}`})}><Banknote size={16}/>Create payment request</Button>}
          {item.state === 'Payment Initiated' && item.payment && role === 'finance' && <Button disabled={!!busy} onClick={()=>void perform(item,'confirm-payment',{payment_id:item.payment!.id})}><BadgeCheck size={16}/>Confirm simulated settlement</Button>}
          {busy.startsWith(`${item.id}:`) && <span className='text-xs text-muted'>Saving…</span>}
        </div>
      </article>)}
    </section>
  </div>;
}
