import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Command, Languages, LogOut, Moon, Search, Sun, UserRound } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { CommandPalette } from '../ui/CommandPalette';
import { Outlet } from 'react-router-dom';
import { isLocalDemoToken } from '../../lib/demoMode';
import i18n from '../../i18n';

const routeNames: Record<string, string> = {
  '/workspace': 'Workspace overview', '/components': 'Components', '/audit': 'Audit trail',
  '/challenges/new': 'Define challenge', '/discover': 'Discover startups', '/eligibility': 'Eligibility help',
  '/evaluations': 'Evaluator workspace', '/committee': 'Committee review', '/agreements': 'Agreements & milestones',
  '/evidence': 'Evidence verification', '/finance': 'Finance & payments', '/scale': 'Scale assessment',
};

export const AppShell: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const location = useLocation();
  const [theme, setTheme] = useState<'light' | 'dark'>(() => window.localStorage.getItem('pilotproof-theme') === 'dark' ? 'dark' : 'light');
  const [userRole] = useState(() => (JSON.parse(window.localStorage.getItem('pilotproof-user') || '{}') as { role?: string }).role || 'guest');
  const syntheticOffline = isLocalDemoToken(window.localStorage.getItem('pilotproof-token'));
  const currentPage = routeNames[location.pathname] || (location.pathname.startsWith('/passport/') ? 'Evidence passport' : 'Workspace');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('pilotproof-theme', theme);
  }, [theme]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setCmdOpen((open) => !open); }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  return (
    <div className='flex h-screen overflow-hidden bg-bg'>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className='flex min-w-0 flex-1 flex-col'>
        <header className='sticky top-0 z-10 flex h-16 shrink-0 items-center justify-between border-b border-border bg-surface/90 px-4 backdrop-blur-md sm:px-6'>
          <div className='truncate text-sm text-muted'><span>Workspace</span><span className='mx-2'>/</span><span className='font-medium text-text'>{currentPage}</span></div>
          <div className='flex items-center gap-2 sm:gap-3'>
            <button onClick={() => setCmdOpen(true)} aria-label='Search workspace and actions' className='flex items-center gap-2 rounded-lg border border-border bg-raised px-3 py-2 text-sm text-muted transition-colors hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'>
              <Search size={16} /><span className='hidden sm:inline'>Search</span><span className='ml-1 hidden items-center gap-1 font-mono text-[10px] opacity-60 sm:flex'><Command size={10}/>K</span>
            </button>
            <label className='sr-only' htmlFor='workspace-language'>Workspace language</label>
            <span className='hidden text-muted sm:inline'><Languages size={17}/></span>
            <select id='workspace-language' aria-label='Workspace language' value={i18n.language.startsWith('mr') ? 'mr' : 'en'} onChange={(event) => { void i18n.changeLanguage(event.target.value); document.documentElement.lang = event.target.value; }} className='h-9 max-w-[5.5rem] rounded-lg border border-border bg-surface px-2 text-xs text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'>
              <option value='en'>English</option><option value='mr'>मराठी</option>
            </select>
            <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} className='rounded-lg p-2 text-muted transition-colors hover:bg-raised hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'>
              {theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}
            </button>
            <button onClick={() => { window.localStorage.removeItem('pilotproof-token'); window.localStorage.removeItem('pilotproof-user'); window.localStorage.removeItem('pilotproof-demo-mode'); window.location.assign('/'); }} aria-label={`Sign out ${userRole} and choose another role`} title={`Current role: ${userRole}. Sign out to choose another role.`} className='inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-2.5 py-2 text-xs font-medium capitalize text-text transition-colors hover:bg-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'><UserRound size={15}/><span className='hidden sm:inline'>{userRole}</span><LogOut size={14} className='text-muted'/></button>
          </div>
        </header>
        {syntheticOffline && <div role='status' className='shrink-0 border-b border-warning/30 bg-warning/10 px-6 py-2 text-center text-xs font-medium text-text'>Synthetic offline demo · actions are not saved to the backend</div>}
        <main className='min-h-0 flex-1 overflow-auto'><Outlet /></main>
      </div>
      <CommandPalette isOpen={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
};
