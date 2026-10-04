import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { apiFetch } from '../../lib/api';
import { Button } from './Button';
import { Card } from './Card';

export function DemoLoginPrompt() {
  const [email, setEmail] = useState('officer@pilotproof.dev');
  const [password, setPassword] = useState('demo1234');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const signIn = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const body = new URLSearchParams({ username: email, password });
      const response = await apiFetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      });
      if (!response.ok) throw new Error('Email or password is incorrect. For a local demo, use password demo1234.');
      const result = await response.json() as { access_token: string };
      window.localStorage.setItem('pilotproof-token', result.access_token);
      if (result.access_token.endsWith('.local-demo')) window.localStorage.setItem('pilotproof-demo-mode', 'true');
      else window.localStorage.removeItem('pilotproof-demo-mode');
      window.location.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign in failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className='mx-auto max-w-xl border-primary/30 p-6'>
      <div className='mb-4 flex items-center gap-3'>
        <span className='rounded-xl bg-primary/10 p-2 text-primary'><KeyRound className='h-5 w-5' /></span>
        <div>
          <h2 className='font-heading text-xl font-semibold text-text'>Officer demo access</h2>
          <p className='text-sm text-muted'>Sign in to create challenges and review synthetic startup profiles.</p>
        </div>
      </div>
      <form className='grid gap-3 sm:grid-cols-[1fr_1fr_auto]' onSubmit={signIn}>
        <label className='grid gap-1 text-xs text-muted'>Email<input type='email' required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label className='grid gap-1 text-xs text-muted'>Password<input type='password' required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        <Button className='self-end' type='submit' isLoading={busy}>Sign in</Button>
      </form>
      {error && <p role='alert' className='mt-3 text-sm text-danger'>{error}</p>}
    </Card>
  );
}
