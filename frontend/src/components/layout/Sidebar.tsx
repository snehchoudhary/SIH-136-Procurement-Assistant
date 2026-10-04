import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, LayoutDashboard, Component, ShieldCheck, PanelLeftClose, PanelLeftOpen, Fingerprint, Compass, FilePlus2, CircleHelp, Scale, ClipboardSignature, FileCheck2, ScanSearch, WalletCards, MapPinned, FileKey2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { motion } from 'framer-motion';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, setCollapsed }) => {
  const navItems = [
    { name: 'Home', path: '/', icon: Home },
    { name: 'Dashboard', path: '/workspace', icon: LayoutDashboard },
    { name: 'Define challenge', path: '/challenges/new', icon: FilePlus2 },
    { name: 'Discover startups', path: '/discover', icon: Compass },
    { name: 'Eligibility help', path: '/eligibility', icon: CircleHelp },
    { name: 'Evaluator workspace', path: '/evaluations', icon: Scale },
    { name: 'Committee review', path: '/committee', icon: ClipboardSignature },
    { name: 'Agreements & milestones', path: '/agreements', icon: FileCheck2 },
    { name: 'Evidence verification', path: '/evidence', icon: ScanSearch },
    { name: 'Finance & payments', path: '/finance', icon: WalletCards },
    { name: 'Scale assessment', path: '/scale', icon: MapPinned },
    { name: 'Evidence passport', path: '/passport/demo-agreement', icon: FileKey2 },
    { name: 'Audit trail', path: '/audit', icon: Fingerprint },
    { name: 'Components', path: '/components', icon: Component },
  ];

  return (
    <motion.aside
      animate={{ width: collapsed ? 80 : 260 }}
      className='h-screen shrink-0 bg-surface border-r border-border flex flex-col glass relative z-20 transition-all duration-300 ease-in-out'
    >
      <div className='h-16 flex items-center px-4 border-b border-border overflow-hidden'>
        <ShieldCheck className='w-8 h-8 text-primary shrink-0' />
        <AnimateText show={!collapsed} className='ml-3 font-heading font-bold text-lg whitespace-nowrap'>
          PilotProof
        </AnimateText>
      </div>

      <nav className='flex-1 py-6 px-3 space-y-1 overflow-y-auto overflow-x-hidden'>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              'flex items-center px-3 py-2.5 rounded-md transition-colors relative group',
              isActive ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-raised hover:text-text'
            )}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div layoutId='sidebar-active' className='absolute left-0 top-1 bottom-1 w-1 bg-primary rounded-r-md' />
                )}
                <item.icon className='w-5 h-5 shrink-0' />
                <AnimateText show={!collapsed} className='ml-3 font-medium whitespace-nowrap'>
                  {item.name}
                </AnimateText>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className='p-4 mt-auto overflow-hidden'>
        {!collapsed && (
          <div className='bg-raised rounded-lg p-3 mb-4 border border-border'>
            <h5 className='text-xs font-semibold mb-1 text-text'>Demo environment</h5>
            <div className='flex items-center gap-2 text-xs text-muted'>
              <span className='w-2 h-2 rounded-full bg-warning' /> Synthetic sample records
            </div>
          </div>
        )}
        
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-expanded={!collapsed}
          className='w-full flex items-center justify-center p-2 text-muted hover:text-text hover:bg-raised rounded-md transition-colors'
        >
          {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
        </button>
      </div>
    </motion.aside>
  );
};

const AnimateText = ({ show, children, className }: { show: boolean, children: React.ReactNode, className?: string }) => (
  <motion.span
    initial={false}
    animate={{ opacity: show ? 1 : 0, width: show ? 'auto' : 0 }}
    className={className}
    style={{ display: show ? 'block' : 'none' }}
  >
    {children}
  </motion.span>
);
