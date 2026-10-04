export function isLocalDemoToken(token: string | null | undefined): boolean {
  return token?.endsWith('.local-demo') === true;
}

export function isReadOnlyDemoRequest(method: string | undefined): boolean {
  return (method || 'GET').toUpperCase() === 'GET';
}

export function maySendBearerTokenToBackend(token: string | null | undefined): boolean {
  return Boolean(token) && !isLocalDemoToken(token);
}

export function parseCredentialForm(body: string | URLSearchParams | null | undefined): URLSearchParams {
  if (body instanceof URLSearchParams) return body;
  return new URLSearchParams(typeof body === 'string' ? body : '');
}

export function isSampleAccount(email: string | null, password: string | null): boolean {
  if (!email || password !== 'demo1234') return false;
  const normalizedEmail = email.trim().toLowerCase();
  const role = normalizedEmail.split('@')[0];
  return normalizedEmail.endsWith('@pilotproof.dev') && ['officer', 'startup', 'evaluator', 'validator', 'finance', 'district'].includes(role);
}
