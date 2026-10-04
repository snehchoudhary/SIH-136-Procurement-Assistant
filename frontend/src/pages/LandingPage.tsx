import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowRight, Check, ChevronDown, ChevronUp, CircleCheck, ClipboardList, FileCheck2, Fingerprint, LockKeyhole, Shield, UsersRound, Languages, Eye, EyeOff, Sparkles, Scale, FileDown, Activity, type LucideIcon } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { apiFetch } from '../lib/api';

type Entry = { id: string; titleKey: string; roleKey: string; pilotKey: string; timeIndex: number; statusKey: string; reasonKey: string; actor: string; occurred: string };
const entries: Entry[] = [
  { id: 'baseline', titleKey: 'baseline', roleKey: 'officer', pilotKey: 'pp204', timeIndex: 0, statusKey: 'verified', reasonKey: 'reason1', actor: 'Officer Priya Sharma', occurred: '2026-10-04T09:42:00Z' },
  { id: 'field', titleKey: 'field', roleKey: 'startup', pilotKey: 'pp204', timeIndex: 1, statusKey: 'submitted', reasonKey: 'reason2', actor: 'Startup Arjun Mehta', occurred: '2026-10-04T10:18:00Z' },
  { id: 'review', titleKey: 'review', roleKey: 'validator', pilotKey: 'pp198', timeIndex: 2, statusKey: 'reviewed', reasonKey: 'reason3', actor: 'Validator Rajan Patel', occurred: '2026-10-03T14:00:00Z' },
];
const accounts = [
  { roleKey: 'officer', email: 'officer@pilotproof.dev' }, { roleKey: 'startup', email: 'startup@pilotproof.dev' },
  { roleKey: 'evaluator', email: 'evaluator@pilotproof.dev' }, { roleKey: 'validator', email: 'validator@pilotproof.dev' },
  { roleKey: 'finance', email: 'finance@pilotproof.dev' }, { roleKey: 'district', email: 'district@pilotproof.dev' },
];
const roles = ['officer', 'startup', 'validator'] as const;
type Role = typeof roles[number];
const features: { icon: LucideIcon; title: string; description: string; visual: string; span?: string }[] = [
  { icon: ClipboardList, title: 'featureAudit', description: 'featureAuditCopy', visual: 'audit' },
  { icon: UsersRound, title: 'featureRoles', description: 'featureRolesCopy', visual: 'roles', span: 'feature-wide' },
  { icon: Fingerprint, title: 'featureHash', description: 'featureHashCopy', visual: 'hash' },
  { icon: Scale, title: 'featureReasons', description: 'featureReasonsCopy', visual: 'reason' },
  { icon: FileDown, title: 'featureExport', description: 'featureExportCopy', visual: 'export' },
  { icon: Languages, title: 'featureLanguage', description: 'featureLanguageCopy', visual: 'language', span: 'feature-wide' },
];

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

async function hashChain(items: Entry[]): Promise<string[]> {
  if (!globalThis.crypto?.subtle) throw new Error('Secure browser context required for SHA-256. Open this local site on localhost or HTTPS.');
  let previous = 'GENESIS';
  const hashes: string[] = [];
  for (const item of items) {
    const input = `${previous}|${item.id}|${item.titleKey}|${item.roleKey}|${item.pilotKey}|${item.reasonKey}|${item.occurred}`;
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input));
    previous = toHex(digest);
    hashes.push(previous);
  }
  return hashes;
}

function MiniVisual({ kind, t }: { kind: string; t: (key: string) => string }) {
  if (kind === 'audit') return <div className='mini-audit' aria-hidden='true'><span /><span /><span /><i /></div>;
  if (kind === 'roles') return <div className='mini-roles' aria-hidden='true'>{['officer', 'startup', 'validator'].map((role) => <span key={role}>{t(role)}</span>)}</div>;
  if (kind === 'hash') return <div className='mini-hash' aria-hidden='true'><Fingerprint size={19} /><code>7f3a…c91e</code><Check size={14} /></div>;
  if (kind === 'reason') return <div className='mini-reason' aria-hidden='true'><span /><span /><span /></div>;
  if (kind === 'export') return <div className='mini-export' aria-hidden='true'><FileCheck2 size={21} /><span>PP-204.csv</span><ArrowRight size={15} /></div>;
  return <div className='mini-language' aria-hidden='true'><span>English</span><span>मराठी</span></div>;
}

function EvidenceChain({ role, t, tArray }: { role: Role; t: (key: string) => string; tArray: (key: string) => string[] }) {
  const reducedMotion = useReducedMotion();
  const [hashes, setHashes] = useState<string[]>([]);
  const [visible, setVisible] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>('baseline');
  const [tampered, setTampered] = useState(false);
  const [error, setError] = useState('');
  const initialHashes = useRef<string[]>([]);
  const tamperedEntries = useMemo(() => entries.map((entry) => entry.id === 'field' && tampered ? { ...entry, reasonKey: 'tamper' } : entry), [tampered]);

  useEffect(() => {
    let cancelled = false;
    void hashChain(entries).then((values) => {
      if (cancelled) return;
      initialHashes.current = values;
      setHashes(values);
      if (reducedMotion) { setVisible(values); return; }
      setVisible(['', '', '']);
      values.forEach((value, row) => {
        const prefix = `${value.slice(0, 4)}…${value.slice(-4)}`;
        let char = 0;
        window.setTimeout(() => {
          const ticker = window.setInterval(() => {
            char += 1;
            setVisible((current) => current.map((text, index) => index === row ? prefix.slice(0, char) : text));
            if (char >= prefix.length) window.clearInterval(ticker);
          }, 24);
        }, row * 150);
      });
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Unable to calculate hashes.'));
    return () => { cancelled = true; };
  }, [reducedMotion]);

  const currentHashes = useMemo(() => hashes.length ? tampered ? hashChain(tamperedEntries) : Promise.resolve(hashes) : Promise.resolve([]), [hashes, tampered, tamperedEntries]);
  const [editedHashes, setEditedHashes] = useState<string[]>([]);
  useEffect(() => { let live = true; void currentHashes.then((values) => { if (live) setEditedHashes(values); }); return () => { live = false; }; }, [currentHashes]);
  const changedIndices = tampered && editedHashes.length ? editedHashes.map((hash, index) => hash === initialHashes.current[index] ? -1 : index).filter((index) => index >= 0) : [];
  const roleIndices: Record<Role, number[]> = { officer: [0], startup: [1], validator: [2] };

  return <Card elevated className='chain-card' aria-label={t('chainTitle')}>
    <div className='chain-header'><div><p className='chain-kicker'><span className='chain-live-dot' />{t('chain')}</p><h2>{t('chainTitle')}</h2></div><span className='chip chip-info'>{t('synthetic')}</span></div>
    <ol className='chain-list' aria-label={t('chain')}>
      {entries.map((entry, index) => {
        const Icon = [Check, FileCheck2, Shield][index];
        const open = expanded === entry.id;
        const changed = changedIndices.includes(index);
        const selected = roleIndices[role].includes(index);
        const hash = tampered ? editedHashes[index] : hashes[index];
        const shortHash = visible[index] || (hash ? `${hash.slice(0, 4)}…${hash.slice(-4)}` : t('hashPending'));
        return <li key={entry.id} className={`chain-row ${selected ? 'is-role-active' : ''} ${changed ? 'is-tampered' : ''}`}>
          {index > 0 && <div className={`chain-connector ${changedIndices.includes(index) ? 'connector-broken' : ''}`} aria-hidden='true' />}
          <button type='button' className='chain-entry' aria-expanded={open} onClick={() => setExpanded(open ? null : entry.id)}>
            <span className='chain-icon'><Icon size={18} /></span>
            <span className='chain-entry-copy'><span className='chain-entry-title'>{t(entry.titleKey)}</span><span className='chain-entry-meta'>{t(entry.roleKey)} · {t(entry.pilotKey)}</span></span>
            <span className='chain-entry-side'><time dateTime={entry.occurred}>{tArray('eventTimes')[entry.timeIndex]}</time><span className={`chain-status status-${entry.statusKey}`}>{t(entry.statusKey)}</span></span>
            {open ? <ChevronUp className='chain-chevron' size={16} /> : <ChevronDown className='chain-chevron' size={16} />}
          </button>
          <div className='chain-hash-row'><span className={`mono chain-hash ${changed ? 'hash-red' : ''}`}>{shortHash}</span>{changed && <span className='chain-mismatch'>{t('mismatch')}</span>}</div>
          {open && <div className='chain-detail'><p><b>{t('actor')}:</b> {entry.actor}</p><p><b>{t('reason')}:</b> {t(tampered && entry.id === 'field' ? 'tamperReason' : entry.reasonKey)}</p><dl><div><dt>{t('previous')}</dt><dd className='mono'>{index ? `${(tampered ? editedHashes[index - 1] : hashes[index - 1])?.slice(0, 4)}…${(tampered ? editedHashes[index - 1] : hashes[index - 1])?.slice(-4)}` : 'GENESIS'}</dd></div><div><dt>{t('hash')}</dt><dd className='mono'>{shortHash}</dd></div></dl></div>}
        </li>;
      })}
    </ol>
    <div className='chain-controls'><button className='btn btn-ghost btn-sm' type='button' onClick={() => { setTampered((value) => !value); setError(''); }}>{tampered ? t('restore') : t('tamper')}</button><p aria-live='polite'>{tampered ? t('tamperLive') : t('tamperCaption')}</p></div>
    {error && <p role='status' className='chain-error'>{error}</p>}
  </Card>;
}

function RoleTabs({ role, setRole, t }: { role: Role; setRole: (role: Role) => void; t: (key: string) => string }) {
  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const index = roles.indexOf(role);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? roles.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : roles.length - 1)) % roles.length;
    setRole(roles[next]);
    document.getElementById(`role-tab-${roles[next]}`)?.focus();
  };
  return <section className='roles-section reveal' aria-labelledby='roles-heading'><div className='roles-heading'><div><p className='section-eyebrow'>{t('eyebrow')}</p><h2 id='roles-heading'>{t('roleTitle')}</h2></div><div className='role-tabs' role='tablist' aria-label={t('roleTitle')} onKeyDown={onKeyDown}>{roles.map((item) => <button key={item} id={`role-tab-${item}`} type='button' role='tab' aria-selected={role === item} aria-controls='role-description' tabIndex={role === item ? 0 : -1} onClick={() => setRole(item)}>{t(item)}</button>)}</div></div><p className='role-description' id='role-description' role='tabpanel' aria-labelledby={`role-tab-${role}`}>{t(`${role}Copy`)}</p></section>;
}

function PilotStory({ t, tArray }: { t: (key: string) => string; tArray: (key: string) => string[] }) {
  const sectionRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  useEffect(() => {
    const root = sectionRef.current;
    if (!root || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver((records) => records.forEach((record) => { if (record.isIntersecting) setActive(Number((record.target as HTMLElement).dataset.step || 0)); }), { rootMargin: '-35% 0px -45% 0px' });
    root.querySelectorAll<HTMLElement>('[data-step]').forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);
  const labels = ['step1', 'step2', 'step3', 'step4'];
  const descriptions = ['step1copy', 'step2copy', 'step3copy', 'step4copy'];
  const visuals = ['baselineMetric', 'evidenceFiles', 'reviewStatus', 'decision'];
  const values = ['metricValue', 'filesValue', 'reviewStatusValue', 'decisionValue'];
  return <section ref={sectionRef} id='how-it-works' className='pilot-story' aria-labelledby='story-heading'><div className='story-intro'><p className='section-eyebrow'>{t('storyEyebrow')}</p><h2 id='story-heading'>{t('storyTitle')}</h2><p>{t('trustLine')}</p></div><div className='story-steps'>{labels.map((label, index) => <article key={label} data-step={index} className={`story-step ${active === index ? 'story-step-active' : ''}`}><span className='story-step-index'>{tArray('stepLabels')[index]}</span><h3>{t(label)}</h3><p>{t(descriptions[index])}</p></article>)}</div><div className='story-visual' aria-live='polite'><div className='story-visual-top'><span className='story-visual-mark'><Shield size={17} /></span><span>{t('stepVisual')}</span><span className='chip chip-neutral'>{t('synthetic')}</span></div><div className='story-visual-content'><p className='story-visual-label'>{t(visuals[active])}</p><h3>{t(values[active])}</h3><div className='story-meter'><span style={{ width: `${[68, 78, 91, 100][active]}%` }} /></div><div className='story-visual-foot'><span>{tArray('stepLabels')[active]}</span><span className='mono'>PP-204 · 2026</span></div></div><div className='story-step-dots' aria-label={`${active + 1} of 4`}>{labels.map((label, index) => <button key={label} aria-label={t(label)} aria-current={active === index ? 'step' : undefined} onClick={() => { setActive(index); document.querySelector(`[data-step="${index}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }} />)}</div></div></section>;
}

export default function LandingPage() {
  const { t: translate, i18n } = useTranslation();
  const t = (key: string, options?: Record<string, unknown>) => translate(`landingV2.${key}`, options as never) as unknown as string;
  const tArray = (key: string) => translate(`landingV2.${key}`, { returnObjects: true }) as unknown as string[];
  const navigate = useNavigate();
  const [role, setRole] = useState<Role>('officer');
  const [loginOpen, setLoginOpen] = useState(false);
  const [email, setEmail] = useState(accounts[0].email);
  const [password, setPassword] = useState('demo1234');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const reducedMotion = useReducedMotion();
  const motionInitial = reducedMotion ? false : { opacity: 0, y: 12 };
  const changeLanguage = (language: string) => { void i18n.changeLanguage(language); document.documentElement.lang = language; };

  const submitLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setLoading(true); setError('');
    try {
      const body = new URLSearchParams({ username: email, password });
      const response = await apiFetch('/api/auth/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
      if (!response.ok) throw new Error(t('loginError'));
      const result = await response.json() as { access_token: string; user: { email: string; role: string } };
      window.localStorage.setItem('pilotproof-token', result.access_token);
      window.localStorage.setItem('pilotproof-user', JSON.stringify(result.user));
      if (result.access_token.endsWith('.local-demo')) window.localStorage.setItem('pilotproof-demo-mode', 'true');
      else window.localStorage.removeItem('pilotproof-demo-mode');
      setLoginOpen(false); navigate('/workspace');
    } catch (reason) { setError(reason instanceof Error ? reason.message : t('loginError')); }
    finally { setLoading(false); }
  };

  return <div className='landing-page'>
    <a className='skip-link' href='#main-content'>{t('skip')}</a>
    <header className='landing-nav glass'><Link to='/' className='brand-lockup' aria-label={t('brand')}><span className='brand-mark'><Shield size={19} /></span><span>{t('brand')}</span></Link><nav aria-label={t('brand')}><label className='sr-only' htmlFor='landing-language'>{t('language')}</label><select id='landing-language' className='language-select' value={i18n.language.startsWith('mr') ? 'mr' : 'en'} onChange={(event) => changeLanguage(event.target.value)}><option value='en'>{t('english')}</option><option value='mr'>{t('marathi')}</option></select><button className='nav-login' type='button' onClick={() => setLoginOpen(true)}>{t('login')}</button><Button variant='primary' className='nav-cta' rightIcon={<ArrowRight size={16} />} onClick={() => navigate('/workspace')}>{t('openDemo')}</Button></nav></header>
    <main id='main-content'>
      <section className='hero-section' aria-labelledby='hero-heading'><motion.div className='hero-copy' initial={motionInitial} animate={{ opacity: 1, y: 0 }} transition={{ duration: reducedMotion ? 0 : .48, ease: 'easeOut' }}><p className='hero-eyebrow'><Sparkles size={15} />{t('eyebrow')}</p><h1 id='hero-heading'>{t('headline')}</h1><p className='hero-subhead'>{t('subhead')}</p><div className='hero-actions'><Button variant='primary' size='lg' rightIcon={<ArrowRight size={17} />} onClick={() => navigate('/workspace')}>{t('openDemo')}</Button><a href='#how-it-works'>{t('howLink')} <ArrowRight size={15} /></a></div><ul className='proof-points'><li><Check size={15} />{t('proof1')}</li><li><Check size={15} />{t('proof2')}</li><li><Check size={15} />{t('proof3')}</li></ul></motion.div><motion.div className='hero-demo' initial={motionInitial} animate={{ opacity: 1, y: 0 }} transition={{ duration: reducedMotion ? 0 : .5, delay: reducedMotion ? 0 : .1 }}><EvidenceChain role={role} t={t} tArray={tArray} /></motion.div></section>
      <RoleTabs role={role} setRole={setRole} t={t} />
      <PilotStory t={t} tArray={tArray} />
      <section className='feature-section' aria-labelledby='features-heading'><div className='section-heading'><p className='section-eyebrow'>{t('featuresEyebrow')}</p><h2 id='features-heading'>{t('featuresTitle')}</h2></div><div className='feature-grid'>{features.map(({ icon: Icon, title, description, visual, span }) => <article key={title} className={`feature-tile card ${span || ''}`}><div className='feature-icon'><Icon size={19} /></div><h3>{t(title)}</h3><p>{t(description)}</p><MiniVisual kind={visual} t={t} /></article>)}</div></section>
      <section className='integrity-section' aria-labelledby='integrity-heading'><div className='integrity-orbit' aria-hidden='true'><span /><span /><span /><Fingerprint size={45} /></div><div className='integrity-copy'><p className='section-eyebrow'>{t('securityEyebrow')}</p><h2 id='integrity-heading'>{t('securityTitle')}</h2><p className='integrity-lede'>{t('securityCopy')}</p><div className='integrity-points'><article><Check size={17} /><div><h3>{t('securityDoes')}</h3><p>{t('securityDoesCopy')}</p></div></article><article><CircleCheck size={17} /><div><h3>{t('securityNot')}</h3><p>{t('securityNotCopy')}</p></div></article><article><LockKeyhole size={17} /><div><h3>{t('securityAccess')}</h3><p>{t('securityAccessCopy')}</p></div></article></div></div></section>
      <section className='final-cta' aria-labelledby='final-heading'><p className='section-eyebrow'>{t('finalEyebrow')}</p><h2 id='final-heading'>{t('finalTitle')}</h2><Button variant='primary' size='lg' rightIcon={<ArrowRight size={17} />} onClick={() => navigate('/workspace')}>{t('finalCta')}</Button><span className='final-synthetic'><span />{t('synthetic')}</span></section>
    </main>
    <footer className='landing-footer'><Link to='/' className='brand-lockup'><span className='brand-mark'><Shield size={17} /></span><span>{t('brand')}</span></Link><p>{t('footer')}</p><span>© 2026 PilotProof</span></footer>
    <Modal isOpen={loginOpen} onClose={() => setLoginOpen(false)} title={t('loginTitle')} className='max-w-[880px]'><div className='login-layout'><aside className='login-aside'><span className='login-aside__brand'><Shield size={19} /> PilotProof</span><div><span className='login-aside__eyebrow'>{t('synthetic')}</span><h3>{t('headline')}</h3><p>{t('loginIntro')}</p></div><div className='login-aside__proof'><LockKeyhole size={15} /><span>{t('loginDisclaimer')}</span></div></aside><form onSubmit={submitLogin} className='login-form'><label htmlFor='demo-account'>{t('roleLabel')}</label><select id='demo-account' value={email} onChange={(event) => setEmail(event.target.value)} className='w-full'>{accounts.map((account) => <option key={account.email} value={account.email}>{t(account.roleKey)} · {account.email}</option>)}</select><label htmlFor='demo-password'>{t('password')}</label><div className='login-password'><input id='demo-password' type={showPassword ? 'text' : 'password'} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete='current-password' required /><button type='button' onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? t('hidePassword') : t('showPassword')} title={showPassword ? t('hidePassword') : t('showPassword')}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div><p className='login-hint'>{t('demoPassword')} <code>demo1234</code></p>{error && <p role='alert' className='rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger'>{error}</p>}<Button type='submit' variant='primary' size='lg' className='w-full' isLoading={loading} rightIcon={!loading ? <ArrowRight size={17} /> : undefined}>{loading ? t('loading') : t('continue')}</Button><p className='login-disclaimer'>{t('loginDisclaimer')}</p></form></div></Modal>
  </div>;
}
