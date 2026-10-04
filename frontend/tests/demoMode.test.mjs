import test from 'node:test';
import assert from 'node:assert/strict';
import { isLocalDemoToken, isReadOnlyDemoRequest, maySendBearerTokenToBackend, isSampleAccount, parseCredentialForm } from '../src/lib/demoMode.ts';

test('synthetic demo tokens cannot be forwarded to the backend', () => {
  const token = 'header.payload.local-demo';
  assert.equal(isLocalDemoToken(token), true);
  assert.equal(maySendBearerTokenToBackend(token), false);
  assert.equal(maySendBearerTokenToBackend('signed-backend-jwt'), true);
});

test('offline demo mode is read-only and defaults to GET', () => {
  assert.equal(isReadOnlyDemoRequest(undefined), true);
  assert.equal(isReadOnlyDemoRequest('get'), true);
  assert.equal(isReadOnlyDemoRequest('POST'), false);
  assert.equal(isReadOnlyDemoRequest('DELETE'), false);
});

test('sample sign-in reads URLSearchParams form bodies and accepts valid demo roles', () => {
  const form = parseCredentialForm(new URLSearchParams({ username: 'officer@pilotproof.dev', password: 'demo1234' }));
  assert.equal(isSampleAccount(form.get('username'), form.get('password')), true);
  assert.equal(isSampleAccount('startup@pilotproof.dev', 'wrong'), false);
  assert.equal(isSampleAccount('someone@example.com', 'demo1234'), false);
});

test('sample sign-in also parses encoded string form bodies', () => {
  const form = parseCredentialForm('username=finance%40pilotproof.dev&password=demo1234');
  assert.equal(isSampleAccount(form.get('username'), form.get('password')), true);
});
