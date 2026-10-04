import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck } from 'lucide-react';

export default function NotFoundPage() {
  return <main className='grid min-h-screen place-items-center bg-bg px-6 py-16 text-center'><section className='max-w-lg'><span className='mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-primary/20 bg-primary/10 text-primary'><ShieldCheck size={27}/></span><p className='mt-7 text-xs font-semibold uppercase tracking-[.2em] text-primary'>PilotProof</p><h1 className='mt-3 font-heading text-5xl font-bold tracking-tight text-text'>Page not found</h1><p className='mt-4 text-muted'>This link doesn’t point to a PilotProof page. Head back to the workspace and continue from there.</p><Link to='/workspace' className='mt-7 inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 font-semibold text-on-primary shadow-sm transition hover:brightness-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2'><ArrowLeft size={17}/> Back to workspace</Link></section></main>;
}
