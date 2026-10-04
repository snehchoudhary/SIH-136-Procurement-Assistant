import { isLocalDemoToken, isReadOnlyDemoRequest, maySendBearerTokenToBackend, isSampleAccount, parseCredentialForm } from './demoMode';

export const API_URL = import.meta.env.VITE_API_URL || '';

const demoData = {
  challenge: { id: 'MH-MUNI-SC-001', title: 'Municipal Service-Centre Wait-Time and Routing Pilot (Synthetic)', department: 'Maharashtra State Innovation Society', district: 'Pune Urban', sector: 'Public service', status: 'Open', budget: 2500000, deadline: '2026-12-31', metric: 'Median request-to-routing time; repeat-referral count', description: 'Synthetic challenge: improve queue visibility and service-request routing at municipal service centres.', problem_statement: 'Residents face uncertain waits and repeated referrals when requesting municipal services.', outcomes: ['Make service-centre wait and routing evidence reviewable.'], target_pct: null },
  startups: [
    { id: 'demo-aqua', name: 'AquaMap Systems (Synthetic)', city: 'Pune', sector: 'Water', founded_year: 2021, annual_turnover_lakhs: 48, dpiit_recognised: true, capability_tags: ['water leakage detection', 'IoT sensors', 'GIS mapping'], domain_experience: 'Two municipal pilot deployments in water networks.', languages_supported: ['Marathi', 'English'], deployment_readiness: 'Pilot-ready; field installation checklist available.', eligibility: { bucket: 'Eligible', rules: [] } },
    { id: 'demo-jal', name: 'JalRakshak Analytics (Synthetic)', city: 'Aurangabad', sector: 'Water', founded_year: 2020, annual_turnover_lakhs: 85, dpiit_recognised: true, capability_tags: ['water quality', 'sensor telemetry', 'offline sync'], domain_experience: 'Water-quality field experience stated; references pending.', languages_supported: ['Marathi', 'English'], deployment_readiness: 'Pilot package documented; connectivity checks pending.', eligibility: { bucket: 'Needs Review', rules: [] } },
    { id: 'demo-civic', name: 'CivicQueue Labs (Synthetic)', city: 'Mumbai', sector: 'Public service', founded_year: 2022, annual_turnover_lakhs: 36, dpiit_recognised: true, capability_tags: ['service centre workflow', 'queue management', 'analytics'], domain_experience: 'Service-centre references attached.', languages_supported: ['Marathi', 'English', 'Hindi'], deployment_readiness: 'Production support rota documented.', eligibility: { bucket: 'Eligible', rules: [] } },
  ],
  policies: [{ id: 'demo-policy', title: 'Pilot eligibility conditions (synthetic demo policy)', jurisdiction: 'Maharashtra (demo only)', version: 'ELIG-DEMO-1.0', effective_date: '2026-01-01', policy_type: 'eligibility', notes: 'Synthetic demo condition. Not an official policy.' }],
};

function response(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'X-PilotProof-Demo': 'true' } });
}

function encodeTokenPart(value: unknown): string {
  return btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function isLocalDemo(): boolean {
  return isLocalDemoToken(window.localStorage.getItem('pilotproof-token'));
}

function offlineDemoFetch(path: string, init: RequestInit): Response | null {
  if (!isLocalDemo()) return null;
  // Never pretend a write reached durable storage. Demo mode is read-only.
  if (!isReadOnlyDemoRequest(init.method)) {
    return response({ detail: 'Synthetic offline demo only: this action was not sent to or saved by the backend.' }, 501);
  }
  const route = path.split('?')[0];
  if (route === '/api/health') return response({ status: 'ok', service: 'pilotproof-local-demo' });
  if (route === '/api/challenges' || route.startsWith('/api/challenges/')) return response(route.endsWith('/versions') ? [{ version: 1, ...demoData.challenge }] : [demoData.challenge]);
  if (route === '/api/discovery/startups') return response({ items: demoData.startups.map((item) => ({ ...item, turnover_lakhs: item.annual_turnover_lakhs, evidence_snippets: item.capability_tags, matched_evidence: item.capability_tags, synthetic: true, fit_breakdown: { capability_evidence: { label: 'Capability evidence', value: 78, explanation: 'Based on listed synthetic capabilities.', evidence: item.capability_tags[0] }, domain_experience: { label: 'Domain experience', value: 72, explanation: 'Synthetic experience summary.', evidence: item.domain_experience }, language_support: { label: 'Language support', value: 85, explanation: 'Languages listed in synthetic profile.', evidence: item.languages_supported.join(', ') }, deployment_readiness: { label: 'Deployment readiness', value: 70, explanation: item.deployment_readiness, evidence: null } }, eligibility: { bucket: item.eligibility.bucket, rules: [], exceptions: [] } })), policy_sources: demoData.policies, notice: 'Local synthetic demonstration data.' });
  if (route === '/api/startups') return response(demoData.startups);
  if (route === '/api/policies') return response(demoData.policies);
  if (route === '/api/audit' || route === '/api/audit/events') return response([
    { id: 'demo-1', sequence: 1, action: 'pilot.baseline_approved', event_type: 'pilot.baseline_approved', actor_role: 'officer', actor_email: 'officer@pilotproof.dev', entity_type: 'Pilot', entity_id: 'PP-204', summary: 'Pilot baseline approved', details: {}, created_at: '2026-10-04T09:42:00Z' },
    { id: 'demo-2', sequence: 2, action: 'evidence.submitted', event_type: 'evidence.submitted', actor_role: 'startup', actor_email: 'startup@pilotproof.dev', entity_type: 'Pilot', entity_id: 'PP-204', summary: 'Field evidence received', details: {}, created_at: '2026-10-04T10:18:00Z' },
    { id: 'demo-3', sequence: 3, action: 'evidence.reviewed', event_type: 'evidence.reviewed', actor_role: 'validator', actor_email: 'validator@pilotproof.dev', entity_type: 'Pilot', entity_id: 'PP-198', summary: 'Independent review recorded', details: {}, created_at: '2026-10-03T14:00:00Z' },
  ]);
  if (route === '/api/audit/verify') return response({ valid: true, checked_events: 3, first_broken_sequence: null, message: 'Local demo chain looks consistent.', note: 'Synthetic demonstration records only.' });
  if (route === '/api/auth/me') return response(JSON.parse(window.localStorage.getItem('pilotproof-user') || '{}'));
  if (route === '/api/auth/demo-users') return response([{ id: 'demo-officer', name: 'Officer Priya Sharma', role: 'officer' }, { id: 'demo-validator', name: 'Validator Rajan Patel', role: 'validator' }, { id: 'demo-finance', name: 'Finance Deepa Rao', role: 'finance' }]);
  if (route === '/api/pilots' || route.startsWith('/api/pilots/')) return response(route.endsWith('/templates') ? [{ key: 'standard', name: 'Standard pilot agreement', clauses: {} }] : []);
  if (route === '/api/milestones') return response({ items: [
    { id: 'demo-milestone-evidence', agreement_id: 'demo-agreement', code: 'PP-204-M2', title: 'Evidence verification (synthetic)', state: 'Evidence Submitted', days_in_state: 2, why_blocked: 'Synthetic demo record. A validator review is required before acceptance.' },
    { id: 'demo-milestone-payment', agreement_id: 'demo-agreement', code: 'PP-204-M3', title: 'Simulated settlement (synthetic)', state: 'Validated', days_in_state: 1, why_blocked: 'Synthetic demo record. Officer acceptance is required before invoice processing.' },
  ], states: ['Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated', 'Payment Confirmed'], settlement_notice: 'Simulated settlement. No real funds move.', funds_notice: 'Synthetic demo records only.' });
  if (route.startsWith('/api/evaluations/')) return response(route.includes('committee') ? { items: [], decisions: [], challenge_id: 'MH-MUNI-SC-001' } : route.includes('rubric') ? { version: 1, criteria: [] } : []);
  if (route === '/api/discovery/eligibility/me') return response({ items: [], startup: null, synthetic: true });
  if (route.startsWith('/api/discovery/startups/') && init.method === 'POST') return response({ detail: 'Uploads are disabled in local demo mode.' }, 501);
  return response({ detail: 'This screen is unavailable in the synthetic offline demo. No backend request was made.' }, 503);
}

export function authHeaders(): HeadersInit {
  const token = window.localStorage.getItem('pilotproof-token');
  return maySendBearerTokenToBackend(token) ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (path.split('?')[0] === '/api/auth/token') {
    try {
      const live = await fetch(`${API_URL}${path}`, init);
      if (![404, 500, 502, 503, 504].includes(live.status)) {
        if (live.status !== 401) return live;
        const values = parseCredentialForm(init.body as string | URLSearchParams | null | undefined);
        if (!isSampleAccount(values.get('username'), values.get('password'))) return live;
      }
    } catch {
      // Continue into the explicit local demo credential check below.
    }
    const values = parseCredentialForm(init.body as string | URLSearchParams | null | undefined);
    const email = (values.get('username') || '').trim().toLowerCase();
    const role = email.split('@')[0];
    if (!isSampleAccount(email, values.get('password'))) return response({ detail: 'Incorrect email or password' }, 401);
    const user = { email, role, name: `${role} Demo`, sub: `demo:${email}`, demo: true };
    const token = `${encodeTokenPart({ alg: 'none', typ: 'JWT' })}.${encodeTokenPart(user)}.local-demo`;
    window.localStorage.setItem('pilotproof-demo-mode', 'true');
    return response({ access_token: token, token_type: 'bearer', user });
  }

  if (isLocalDemo()) {
    return offlineDemoFetch(path, init)!;
  }

  const headers = new Headers(authHeaders());
  new Headers(init.headers).forEach((value, key) => headers.set(key, value));
  try {
    const live = await fetch(`${API_URL}${path}`, { ...init, headers });
    return live;
  } catch (error) {
    const demo = offlineDemoFetch(path, init);
    if (demo) return demo;
    throw error;
  }
}
