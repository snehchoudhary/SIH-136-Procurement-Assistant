import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Activity, ArrowDownRight, ArrowRight, Check, ChevronDown, CircleHelp, MapPinned, Play, RotateCcw, Sparkles, Wifi } from 'lucide-react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import { apiFetch } from '../lib/api';
import { PageHeader } from '../components/ui/PageHeader';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';

type District = { id: string; name: string; daily_case_volume: number; bandwidth_mbps: number; language_mix: Record<string, number>; infrastructure: string[]; staffing_level: number; security_requirements: string[]; product_version: string; simulated: boolean };
type Finding = { dimension: string; decision: string; reason: string; additional_test?: string | null };
type Result = { findings: Finding[]; technical_suitability: string; additional_tests: string[]; source: Record<string, unknown>; receiving: Record<string, unknown>; procurement_route_status: string; notice?: string; id?: string };
type LanguageMix = Record<string, number>;
const defaultMix = { Marathi: .78, Hindi: .15, Gondi: .07 };
const EVIDENCE_KEYS = ['load', 'connectivity', 'language', 'infrastructure', 'staffing', 'security', 'product_version'];
const sourceCondition = (source: Record<string, unknown>, receiving: Record<string, unknown>, key: string) => {
  if (key === 'load') return Number(source.capacity_per_day || 0);
  if (key === 'connectivity') return Number(source.bandwidth_mbps || 0);
  if (key === 'language') return Object.keys((source.language_mix as object) || {}).length;
  if (key === 'staffing') return Number(source.demonstrated_staffing_level || 0);
  return key === 'product_version' ? String(source.product_version || '') : ((source[`demonstrated_${key}`] as string[]) || []).length;
};

export default function TransferAssessmentPage() {
  const [districts, setDistricts] = useState<District[]>([]);
  const [district, setDistrict] = useState<District | null>(null);
  const [bandwidth, setBandwidth] = useState(2);
  const [volume, setVolume] = useState(120);
  const [mix, setMix] = useState<LanguageMix>(defaultMix);
  const [productVersion, setProductVersion] = useState('v1.0');
  const [included, setIncluded] = useState<Record<string, boolean>>(Object.fromEntries(EVIDENCE_KEYS.map((key) => [key, true])));
  const [result, setResult] = useState<Result | null>(null);
  const [previous, setPrevious] = useState<Result | null>(null);
  const [assessmentId, setAssessmentId] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const loadDistricts = useCallback(async () => {
    try { const response = await apiFetch('/api/transfer/districts'); if (!response.ok) throw new Error('Could not load district profiles.'); const rows = await response.json() as District[]; setDistricts(rows); if (rows.length) { setDistrict((current) => current ? rows.find((x) => x.id === current.id) || rows[0] : rows[0]); setBandwidth(rows[0].bandwidth_mbps); setVolume(rows[0].daily_case_volume); setMix(rows[0].language_mix || defaultMix); setProductVersion(rows[0].product_version || 'v1.0'); } }
    catch (e) { setError(e instanceof Error ? e.message : 'District profiles unavailable.'); }
  }, []);
  useEffect(() => { void loadDistricts(); }, [loadDistricts]);
  useEffect(() => {
    if (!district) return;
    const timer = window.setTimeout(async () => {
      setBusy(true);
      try {
        const response = await apiFetch('/api/transfer/assess/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agreement_id: 'demo-agreement', district_id: district.id, bandwidth_mbps: bandwidth, daily_case_volume: volume, language_mix: mix, product_version: productVersion, included_evidence: included }) });
        const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Transfer preview could not be calculated.');
        setPrevious((current) => current || body); setResult((current) => { if (current) setPrevious(current); return body; }); setError('');
      } catch (e) { setError(e instanceof Error ? e.message : 'Transfer preview could not be calculated.'); }
      finally { setBusy(false); }
    }, 160);
    return () => window.clearTimeout(timer);
  }, [district, bandwidth, volume, mix, productVersion, included]);
  const changed = useMemo(() => new Set((result?.findings || []).filter((item) => previous?.findings.find((prior) => prior.dimension === item.dimension)?.decision !== item.decision).map((item) => item.dimension)), [result, previous]);
  const radar = useMemo(() => {
    if (!result) return [];
    const source = result.source as Record<string, unknown>, receiving = result.receiving as Record<string, unknown>;
    return [{ dimension: 'Daily volume', source: Math.min(100, Number(source.capacity_per_day || 0) / 3), receiving: Math.min(100, Number(receiving.daily_case_volume || 0) / 3) },
      { dimension: 'Bandwidth', source: Math.min(100, Number(source.bandwidth_mbps || 0) * 20), receiving: Math.min(100, Number(receiving.bandwidth_mbps || 0) * 20) },
      { dimension: 'Languages', source: Math.min(100, Object.keys((source.language_mix as object) || {}).length * 25), receiving: Math.min(100, Object.keys((receiving.language_mix as object) || {}).length * 25) },
      { dimension: 'Infrastructure', source: Math.min(100, ((source.demonstrated_infrastructure as string[]) || []).length * 30), receiving: Math.min(100, ((receiving.infrastructure as string[]) || []).length * 30) },
      { dimension: 'Staffing', source: Math.min(100, Number(source.demonstrated_staffing_level || 0) * 15), receiving: Math.min(100, Number(receiving.staffing_level || 0) * 15) },
      { dimension: 'Security', source: Math.min(100, ((source.demonstrated_security_requirements as string[]) || []).length * 35), receiving: Math.min(100, ((receiving.security_requirements as string[]) || []).length * 35) }];
  }, [result]);
  const persistAssessment = async () => {
    if (!district) return;
    setBusy(true); setError('');
    try { const response = await apiFetch('/api/transfer/assess', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agreement_id: 'demo-agreement', district_id: district.id, procurement_route_status: 'Not assessed', procurement_note: 'Technical suitability assessed independently; procurement route pending local review.' }) }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Assessment could not be saved.'); setAssessmentId(body.id); setResult(body); setNotice('Transfer assessment saved. Procurement route remains a separate decision.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Assessment could not be saved.'); }
    finally { setBusy(false); }
  };
  const createTests = async () => {
    if (!assessmentId) { setError('Save the assessment before creating test milestones.'); return; }
    setBusy(true); setError('');
    try { const response = await apiFetch(`/api/transfer/assessments/${assessmentId}/create-tests`, { method: 'POST' }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Test milestones could not be created.'); setNotice(body.created?.length ? `Created ${body.created.length} additional test milestone(s).` : 'All required additional test milestones already exist.'); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not create additional tests.'); }
    finally { setBusy(false); }
  };
  const toggleEvidence = (key: string) => setIncluded((state) => ({ ...state, [key]: !state[key] }));
  const updateShare = (language: string, share: number) => setMix((state) => ({ ...state, [language]: share }));
  const reset = () => { if (!district) return; setBandwidth(district.bandwidth_mbps); setVolume(district.daily_case_volume); setMix(district.language_mix || defaultMix); setProductVersion(district.product_version || 'v1.0'); setIncluded(Object.fromEntries(EVIDENCE_KEYS.map((key) => [key, true]))); setPrevious(null); setNotice('Scenario reset to receiving-district profile.'); };
  const resultTone = (value?: string) => value === 'Evidence reusable' ? 'border-success/30 bg-success/10 text-success' : value === 'Additional test needed' ? 'border-accent/40 bg-accent/10 text-text' : 'border-border bg-raised text-muted';
  return <div className='mx-auto max-w-7xl space-y-6 p-6 lg:p-9'>
    <PageHeader title='Will it travel?' eyebrow='Scale assessment · Gadchiroli' description='Compare the original pilot conditions with a receiving district, then see exactly which evidence still holds.' actionSlot={<Button onClick={()=>void persistAssessment()} disabled={busy || !result}><Check size={16}/>Save assessment</Button>}/>
    <div className='grid gap-6 xl:grid-cols-[.9fr_1.1fr]'>
      <section className='space-y-5 rounded-2xl border border-border bg-surface p-5 shadow-sm'>
        <div className='flex items-center justify-between'><div><h2 className='font-semibold text-text'>Receiving district conditions</h2><p className='text-sm text-muted'>Change an input to rerun assessment live.</p></div><button onClick={reset} className='inline-flex items-center gap-1 text-xs text-muted hover:text-text'><RotateCcw size={14}/>Reset</button></div>
        {!district ? <Skeleton className='h-52'/> : <>
          <label className='block text-sm font-medium text-text'>District profile<select aria-label='Receiving district' value={district.id} onChange={(event)=>{ const selected=districts.find((x)=>x.id===event.target.value); if (selected) {setDistrict(selected);setBandwidth(selected.bandwidth_mbps);setVolume(selected.daily_case_volume);setMix(selected.language_mix||defaultMix);setProductVersion(selected.product_version||'v1.0');} }} className='mt-2 w-full rounded-xl border border-border bg-bg px-3 py-2.5'>{districts.map((x)=><option value={x.id} key={x.id}>{x.name}{x.simulated?' · synthetic':''}</option>)}</select></label>
          <div className='rounded-xl bg-inverse-surface p-4 text-inverse-text'><div className='mb-3 flex items-center gap-2 text-sm font-semibold'><Wifi size={16} className='text-accent'/> Connectivity <span className='ml-auto rounded-full bg-inverse-text/10 px-2 py-0.5 text-[10px] uppercase tracking-wider'>Live</span></div><div className='flex items-center gap-4'><input aria-label='Bandwidth Mbps' type='range' min='0.1' max='10' step='0.1' value={bandwidth} onChange={(e)=>setBandwidth(Number(e.target.value))} className='w-full accent-accent'/><output className='w-20 text-right font-mono text-lg'>{bandwidth.toFixed(1)}<small className='ml-1 text-xs text-inverse-text/50'>Mbps</small></output></div><p className='mt-2 text-xs text-inverse-text/55'>Pilot threshold: {String((result?.source as Record<string, unknown>)?.bandwidth_mbps ?? '—')} Mbps</p></div>
          <div><div className='mb-2 flex justify-between text-sm'><label htmlFor='volume' className='font-medium text-text'>Daily service volume</label><span className='font-mono text-muted'>{volume} cases/day</span></div><input id='volume' type='range' min='20' max='500' step='10' value={volume} onChange={(e)=>setVolume(Number(e.target.value))} className='w-full accent-accent'/></div>
          <div><h3 className='mb-2 text-sm font-medium text-text'>Language mix</h3>{Object.keys(mix).map((lang)=><label key={lang} className='mb-2 flex items-center gap-3 text-xs text-muted'><span className='w-16'>{lang}</span><input aria-label={`${lang} share`} type='range' min='0' max='1' step='.01' value={mix[lang]||0} onChange={(e)=>updateShare(lang,Number(e.target.value))} className='flex-1 accent-accent'/><span className='w-10 text-right font-mono'>{Math.round((mix[lang]||0)*100)}%</span></label>)}</div>
          <label className='block text-sm font-medium text-text'>Product version<select value={productVersion} onChange={(e)=>setProductVersion(e.target.value)} className='mt-2 w-full rounded-xl border border-border bg-bg px-3 py-2.5'><option value='v1.0'>v1.0 · tested</option><option value='v1.1'>v1.1 · newer release</option><option value='v2.0'>v2.0 · major update</option></select></label>
          <div><div className='mb-2 flex items-center gap-1 text-sm font-medium text-text'>Evidence rows used <CircleHelp size={14} className='text-muted'/></div><div className='grid grid-cols-2 gap-2'>{EVIDENCE_KEYS.map((key)=><button key={key} onClick={()=>toggleEvidence(key)} aria-pressed={included[key]} className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs capitalize transition-colors ${included[key]?'border-success/30 bg-success/10 text-success':'border-border bg-raised text-muted'}`}>{key.replace('_',' ')}<span>{included[key]?'Included':'Excluded'}</span></button>)}</div></div>
        </>}
      </section>
      <div className='space-y-5'>
        <section className='rounded-2xl border border-border bg-surface p-5 shadow-sm'><div className='flex flex-wrap items-center justify-between gap-3'><div><p className='text-xs font-semibold uppercase tracking-[.16em] text-muted'>Technical suitability · {district?.name || 'Receiving district'}</p><h2 className='mt-1 text-2xl font-semibold text-text'>{busy?'Recalculating…':result?.technical_suitability || 'Loading assessment'}</h2></div><span className='rounded-full border border-border bg-raised px-3 py-1 text-xs font-medium text-text'>Procurement route: {result?.procurement_route_status || 'Not assessed'}</span></div><p className='mt-2 text-xs text-muted'>Technical reuse and procurement route approval are reviewed separately.</p>
          <div className='mt-5 grid gap-3 sm:grid-cols-2'>{result?.findings.map((finding)=><AnimatePresence mode='wait' key={finding.dimension}><motion.article key={`${finding.dimension}-${finding.decision}`} initial={{opacity:.35,y:7,scale:.99}} animate={{opacity:1,y:0,scale:1}} transition={{duration:.35}} className={`rounded-xl border p-3 ${resultTone(finding.decision)} ${changed.has(finding.dimension)?'ring-2 ring-accent shadow-[0_0_22px_rgb(var(--accent)/.2)]':''}`}><div className='flex items-center justify-between gap-2'><h3 className='text-sm font-semibold capitalize'>{finding.dimension.replace('_',' ')}</h3>{changed.has(finding.dimension)&&<Sparkles size={15} className='text-accent'/>}</div><p className='mt-1 text-xs font-semibold'>{finding.decision}</p><p className='mt-1.5 text-xs leading-relaxed opacity-80'>{finding.reason}</p>{finding.additional_test&&<p className='mt-2 inline-flex items-center gap-1 text-[11px] font-semibold'><ArrowDownRight size={13}/>{finding.additional_test}</p>}</motion.article></AnimatePresence>)}</div>
          {!result && <Skeleton className='mt-5 h-56'/>}
        </section>
        <section className='grid gap-5 lg:grid-cols-2'>
          <div className='rounded-2xl border border-border bg-surface p-5'><div className='flex items-center gap-2'><Activity size={17} className='text-primary'/><h2 className='font-semibold text-text'>Conditions at a glance</h2></div><p className='text-xs text-muted'>Source pilot vs receiving district · indexed view</p><div className='mt-2 h-60'>{radar.length>0?<ResponsiveContainer width='100%' height='100%'><RadarChart data={radar}><PolarGrid stroke='rgb(var(--border))'/><PolarAngleAxis dataKey='dimension' tick={{fontSize:10,fill:'rgb(var(--muted))'}}/><Tooltip/><Radar name='Source pilot' dataKey='source' stroke='rgb(var(--primary))' fill='rgb(var(--primary))' fillOpacity={.25}/><Radar name='Receiving district' dataKey='receiving' stroke='rgb(var(--accent))' fill='rgb(var(--accent))' fillOpacity={.25}/></RadarChart></ResponsiveContainer>:<Skeleton className='h-full'/>}</div><div className='flex justify-center gap-4 text-[11px] text-muted'><span className='text-primary'>● Source pilot</span><span className='text-accent'>● Receiving district</span></div></div>
          <div className='rounded-2xl border border-border bg-surface p-5'><div className='flex items-center gap-2'><MapPinned size={17} className='text-primary'/><h2 className='font-semibold text-text'>Before → after</h2></div><p className='text-xs text-muted'>Each decision has an evidence-backed reason.</p><div className='mt-4 space-y-2'>{(result?.findings||[]).slice(0,5).map((item)=><div key={item.dimension} className='grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg bg-bg px-3 py-2 text-[11px]'><span className='capitalize text-muted'>{item.dimension.replace('_',' ')}</span><span className='text-muted'><ArrowRight size={13}/></span><span className={`truncate rounded-md px-2 py-1 text-center font-semibold ${resultTone(item.decision)}`}>{item.decision}</span></div>)}</div><div className='mt-4 rounded-xl border border-dashed border-border p-3 text-xs text-muted'>Change bandwidth to see whether the pilot’s connectivity result can travel. The reason updates with the decision.</div></div>
        </section>
        <section className='rounded-2xl border border-accent/40 bg-accent/10 p-5'><div className='flex flex-wrap items-center justify-between gap-3'><div><h2 className='font-semibold text-text'>Additional tests</h2><p className='mt-1 text-sm text-muted'>{result?.additional_tests.length ? 'Create traceable milestones for the receiving-district retests.' : 'No additional test is currently recommended.'}</p></div><Button onClick={()=>void createTests()} disabled={busy || !assessmentId || !result?.additional_tests.length}><Play size={15}/>Create test milestones</Button></div>{result?.additional_tests.length ? <div className='mt-3 flex flex-wrap gap-2'>{result.additional_tests.map((test)=><span key={test} className='rounded-full border border-accent/40 bg-surface px-3 py-1.5 text-xs font-medium text-text'>{test}</span>)}</div>:null}</section>
      </div>
    </div>
    <AnimatePresence>{(error||notice)&&<motion.div initial={{opacity:0,y:6}} animate={{opacity:1,y:0}} exit={{opacity:0}} role={error?'alert':'status'} className={`fixed bottom-5 right-5 z-50 max-w-md rounded-xl border px-4 py-3 text-sm shadow-xl ${error?'border-danger/30 bg-danger/10 text-danger':'border-success/30 bg-success/10 text-success'}`}>{error||notice}<button className='ml-3 font-semibold' onClick={()=>{setError('');setNotice('')}} aria-label='Dismiss message'>×</button></motion.div>}</AnimatePresence>
  </div>;
}
