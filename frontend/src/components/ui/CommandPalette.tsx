import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, FileCheck2, Fingerprint, LogOut, MapPinned, Search, X } from 'lucide-react';
import { Modal } from './Modal';
import { apiFetch } from '../../lib/api';

export interface CommandPaletteProps { isOpen: boolean; onClose: () => void }
type Command = { id:string; name:string; detail:string; path?:string; action?:'verify'|'signout' };
const commands:Command[]=[
  {id:'demo',name:'Open evidence review',detail:'Review the available evidence and demo datasets',path:'/evidence'},
  {id:'challenges',name:'Challenges and startups',detail:'Browse pilot opportunities',path:'/discover'},
  {id:'milestones',name:'Agreements and milestones',detail:'Review pilot agreements',path:'/agreements'},
  {id:'finance',name:'Finance pipeline',detail:'Invoices and simulated settlement',path:'/finance'},
  {id:'transfer',name:'Gadchiroli transfer simulator',detail:'Run a receiving-district what-if',path:'/scale'},
  {id:'passport',name:'Pilot evidence passport',detail:'Open demo passport and exports',path:'/passport/demo-agreement'},
  {id:'audit',name:'Audit trail',detail:'Review integrity events',path:'/audit'},
  {id:'verify',name:'Run integrity check',detail:'Verify the demo agreement audit chain',action:'verify'},
  {id:'role',name:'Sign out / change role',detail:'Return to sign-in and choose a different role',action:'signout'},
];
export const CommandPalette:React.FC<CommandPaletteProps>=({isOpen,onClose})=>{
  const [query,setQuery]=useState('');const [message,setMessage]=useState('');const navigate=useNavigate();
  const filtered=useMemo(()=>commands.filter(item=>`${item.name} ${item.detail}`.toLowerCase().includes(query.toLowerCase())),[query]);
  const run=async(item:Command)=>{
    if(item.action==='verify'){
      setMessage('Checking…');
      try{const res=await apiFetch('/api/audit/verify?pilot_id=demo-agreement');const result=await res.json();if(!res.ok)throw new Error(result.detail||'Integrity check could not run.');setMessage(result.valid?`Integrity chain verified · ${result.checked_events} events checked.`:`Integrity issue: ${result.message}`)}catch(e){setMessage(e instanceof Error?e.message:'Integrity check unavailable.')}
      return;
    }
    if(item.action==='signout'){localStorage.removeItem('pilotproof-token');localStorage.removeItem('pilotproof-user');localStorage.removeItem('pilotproof-demo-mode');navigate('/');onClose();return;}
    if(item.path){navigate(item.path);setQuery('');setMessage('');onClose();}
  };
  return <Modal isOpen={isOpen} onClose={()=>{onClose();setMessage('')}} title='Go to…' className='max-w-xl p-0 overflow-hidden'>
    <div className='flex items-center border-b border-border px-4'><Search className='mr-3 text-muted' size={19}/><input aria-label='Search workspaces and actions' value={query} onChange={e=>setQuery(e.target.value)} placeholder='Search pages and actions…' className='h-14 flex-1 bg-transparent text-base text-text outline-none placeholder:text-muted' autoFocus/><button onClick={()=>setQuery('')} aria-label='Clear search' className='rounded-md p-1 text-muted hover:text-text'><X size={16}/></button></div>
    <div className='max-h-[55vh] space-y-1 overflow-auto p-2'>{filtered.length?filtered.map((item)=><button key={item.id} onClick={()=>void run(item)} className='group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary'><span className='rounded-lg bg-raised p-2 text-muted group-hover:text-primary'>{item.path==='/scale'?<MapPinned size={16}/>:item.path==='/finance'?<Activity size={16}/>:item.path?.includes('passport')?<FileCheck2 size={16}/>:item.action==='verify'?<Fingerprint size={16}/>:item.action==='signout'?<LogOut size={16}/>:<ArrowRight size={16}/>}</span><span className='min-w-0 flex-1'><strong className='block text-sm font-medium text-text'>{item.name}</strong><span className='block truncate text-xs text-muted'>{item.detail}</span></span><ArrowRight size={15} className='text-muted opacity-0 transition group-hover:opacity-100'/></button>):<p className='p-8 text-center text-sm text-muted'>No matching page or action.</p>}</div>
    {message&&<div role='status' className='border-t border-border bg-raised/60 px-4 py-3 text-sm text-text'>{message}</div>}
    <p className='border-t border-border px-4 py-2 text-[10px] text-muted'>Keyboard shortcut · Ctrl/⌘ K</p>
  </Modal>;
};
