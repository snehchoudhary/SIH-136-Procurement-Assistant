import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, CircleHelp, Fingerprint, RefreshCw, ShieldCheck } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { apiFetch } from '../lib/api';


type AuditEvent = {
  id: number;
  pilot_id: string;
  sequence: number;
  actor: string;
  role: string;
  reason: string;
  before_state: string;
  after_state: string;
  event_type: string;
  previous_hash: string;
  event_hash: string;
  created_at: string;
};

type Verification = {
  valid: boolean;
  checked_events: number;
  first_broken_sequence: number | null;
  message: string;
  note: string;
};

type LinkState = 'unchecked' | 'valid' | 'broken';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState('all');
  const [verification, setVerification] = useState<Verification | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');
  const [pilotId, setPilotId] = useState('DEMO-001');
  const [linkStates, setLinkStates] = useState<Record<number, LinkState>>({});
  const [email, setEmail] = useState('officer@pilotproof.dev');
  const [password, setPassword] = useState('demo1234');
  const [authToken, setAuthToken] = useState(() => window.localStorage.getItem('pilotproof-token') ?? '');

  const requestHeaders = useMemo<Record<string, string>>(
    (): Record<string, string> => authToken ? { Authorization: `Bearer ${authToken}` } : {},
    [authToken],
  );

  const loadEvents = useCallback(async () => {
    setError('');
    try {
      const response = await apiFetch(`/api/audit/events?pilot_id=${encodeURIComponent(pilotId)}`, { headers: requestHeaders });
      if (!response.ok) throw new Error(`Audit event request failed (${response.status}).`);
      const data = (await response.json()) as AuditEvent[];
      setEvents(data.sort((a, b) => a.sequence - b.sequence));
    } catch (requestError) {
      setEvents([]);
      setError(requestError instanceof Error ? requestError.message : 'Could not load audit events.');
    }
  }, [pilotId, requestHeaders]);

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const visibleEvents = useMemo(
    () => filter === 'all' ? events : events.filter((event) => event.event_type === filter || event.after_state === filter),
    [events, filter],
  );
  const filterOptions = useMemo(() => Array.from(new Set(events.flatMap((event) => [event.event_type, event.after_state]))), [events]);

  const verifyIntegrity = async () => {
    setChecking(true);
    setVerification(null);
    setError('');
    setLinkStates(Object.fromEntries(events.map((event) => [event.sequence, 'unchecked' as LinkState])));
    try {
      const response = await apiFetch(`/api/audit/verify?pilot_id=${encodeURIComponent(pilotId)}`, { headers: requestHeaders });
      if (!response.ok) throw new Error(`Integrity check failed (${response.status}).`);
      const result = (await response.json()) as Verification;
      setVerification(result);
      for (const event of events) {
        const isBroken = !result.valid && event.sequence >= (result.first_broken_sequence ?? Number.MAX_SAFE_INTEGER);
        await new Promise((resolve) => window.setTimeout(resolve, 110));
        setLinkStates((current) => ({ ...current, [event.sequence]: isBroken ? 'broken' : 'valid' }));
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not verify audit chain.');
    } finally {
      setChecking(false);
    }
  };

  const demoLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    try {
      const form = new URLSearchParams({ username: email, password });
      const response = await apiFetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });
      if (!response.ok) throw new Error('Demo login failed. Use the demo email and password demo1234.');
      const result = (await response.json()) as { access_token: string };
      window.localStorage.setItem('pilotproof-token', result.access_token);
      if (result.access_token.endsWith('.local-demo')) window.localStorage.setItem('pilotproof-demo-mode', 'true');
      setAuthToken(result.access_token);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Demo login failed.');
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-muted">Traceability</p>
          <h1 className="mt-2 font-heading text-4xl font-semibold text-text">Audit trail</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted">Recorded lifecycle changes, responsible actors, reasons, and chained integrity hashes.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="sr-only" htmlFor="audit-pilot">Pilot identifier</label>
          <input id="audit-pilot" value={pilotId} onChange={(event) => setPilotId(event.target.value)} className="w-36" aria-label="Pilot identifier" />
          <Button variant="ghost" onClick={() => void loadEvents()} aria-label="Refresh audit events"><RefreshCw className="mr-2 h-4 w-4" />Refresh</Button>
          <Button onClick={() => void verifyIntegrity()} disabled={checking}>
            <ShieldCheck className="mr-2 h-4 w-4" />{checking ? 'Checking links…' : 'Integrity check'}
          </Button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{error}</div>}

      {!authToken && (
        <Card className="border-primary/30 p-4">
          <form onSubmit={demoLogin} className="flex flex-wrap items-end gap-3">
            <div className="mr-auto">
              <p className="font-semibold text-text">Sign in to view the protected audit trail</p>
              <p className="mt-1 text-xs text-muted">Demo access uses the synthetic seeded Officer account.</p>
            </div>
            <label className="grid gap-1 text-xs text-muted">Email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></label>
            <label className="grid gap-1 text-xs text-muted">Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required /></label>
            <Button type="submit">Demo login</Button>
          </form>
        </Card>
      )}

      {verification && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card className={verification.valid ? 'border-success/40 p-4' : 'border-danger/40 p-4'}>
            <div className="flex items-start gap-3">
              {verification.valid ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-success" /> : <AlertTriangle className="mt-0.5 h-5 w-5 text-danger" />}
              <div>
                <p className="font-semibold text-text">{verification.valid ? 'Integrity check passed' : `Integrity break at event ${verification.first_broken_sequence}`}</p>
                <p className="mt-1 text-sm text-muted">{verification.message} Checked {verification.checked_events} event(s).</p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      <Card className="p-5">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-heading text-xl font-semibold text-text">Event chain</h2>
            <p className="mt-1 text-xs text-muted">The chain is checked in sequence for this pilot.</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-muted">
            Filter
            <select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter audit events">
              <option value="all">All events</option>
              {filterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
        </div>

        {visibleEvents.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted">
            <CircleHelp className="mx-auto mb-3 h-5 w-5" />
            {events.length === 0 ? 'No audit events found for this pilot yet.' : 'No events match this filter.'}
          </div>
        ) : (
          <ol className="relative space-y-4 before:absolute before:bottom-5 before:left-[15px] before:top-5 before:w-px before:bg-gradient-to-b before:from-primary before:via-border before:to-transparent">
            <AnimatePresence initial={false}>
              {visibleEvents.map((event) => {
                const state = linkStates[event.sequence] ?? 'unchecked';
                return (
                  <motion.li key={`${event.pilot_id}-${event.sequence}`} layout initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} className="relative pl-10">
                    <span className={`absolute left-1 top-3 z-10 h-5 w-5 rounded-full border-2 border-surface ${state === 'valid' ? 'bg-success' : state === 'broken' ? 'bg-danger' : 'bg-primary'}`} />
                    <div className={`rounded-xl border bg-surface/70 p-4 ${state === 'broken' ? 'border-danger/60' : state === 'valid' ? 'border-success/30' : 'border-border'}`}>
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-mono text-muted">#{event.sequence} · {event.pilot_id} · {event.event_type}</p>
                          <h3 className="mt-1 font-semibold text-text">{event.before_state} <span className="text-primary">→</span> {event.after_state}</h3>
                          <p className="mt-1 text-sm text-muted">{event.reason || 'No additional reason recorded.'}</p>
                          <p className="mt-2 text-xs text-muted">{event.actor} · {event.role} · {new Date(event.created_at).toLocaleString()}</p>
                        </div>
                        <Fingerprint className={`h-4 w-4 ${state === 'valid' ? 'text-success' : state === 'broken' ? 'text-danger' : 'text-muted'}`} aria-label={`Hash link ${state}`} />
                      </div>
                      <details className="mt-3 text-xs">
                        <summary className="cursor-pointer text-muted">Show hash link</summary>
                        <div className="mt-2 space-y-1 break-all font-mono text-[10px] text-muted">
                          <p>Previous: {event.previous_hash}</p>
                          <p>Current: {event.event_hash}</p>
                        </div>
                      </details>
                    </div>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ol>
        )}
      </Card>

      <p className="rounded-xl border border-border bg-raised/40 p-4 text-sm text-muted">{verification?.note ?? 'Hashes detect changes. They do not prove a measurement was truthful.'}</p>
    </div>
  );
}
