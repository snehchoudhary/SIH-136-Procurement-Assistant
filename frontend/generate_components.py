import os

base_dir = r'c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\frontend\src'
files = {
    'components/ui/Button.tsx': '''import React from \'react\';
import { cva, type VariantProps } from \'class-variance-authority\';
import { Loader2 } from \'lucide-react\';
import { cn } from \'../../lib/utils\';

const buttonVariants = cva(
  \'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/50 disabled:opacity-50 disabled:pointer-events-none\',
  {
    variants: {
      variant: {
        default: \'bg-gradient-to-r from-saffron to-rose text-white hover:opacity-90 shadow-sm\',
        primary: \'bg-gradient-to-r from-saffron to-rose text-white hover:opacity-90 shadow-glow\',
        outline: \'border border-border hover:bg-surface text-text\',
        ghost: \'hover:bg-surface text-text\',
        danger: \'bg-rose text-white hover:bg-rose/90 shadow-sm\',
      },
      size: {
        default: \'h-10 py-2 px-4\',
        sm: \'h-8 px-3 rounded-md text-xs\',
        lg: \'h-12 px-8 rounded-md text-base\',
        icon: \'h-10 w-10\',
      },
    },
    defaultVariants: {
      variant: \'default\',
      size: \'default\',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, leftIcon, rightIcon, children, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <Loader2 className=\'mr-2 h-4 w-4 animate-spin\' />}
        {!isLoading && leftIcon && <span className=\'mr-2\'>{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className=\'ml-2\'>{rightIcon}</span>}
      </button>
    );
  }
);
Button.displayName = \'Button\';
''',
    'components/ui/Card.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  glow?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, elevated, glow, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          \'rounded-card border border-border bg-surface text-text relative overflow-hidden transition-all duration-300\',
          elevated && \'shadow-lg bg-raised\',
          glow && \'shadow-glow hover:shadow-[0_0_0_1px_rgba(255,176,32,0.4),0_20px_50px_rgba(10,15,30,0.5)]\',
          className
        )}
        {...props}
      >
        <div className=\'absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay bg-[url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")]\'></div>
        <div className=\'relative z-10\'>{children}</div>
      </div>
    );
  }
);
Card.displayName = \'Card\';
''',
    'components/ui/StatusChip.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

type Status = \'Verified\' | \'Pending\' | \'Disputed\' | \'Needs Verification\' | \'AI-Drafted\' | \'Simulated\';

export interface StatusChipProps extends React.HTMLAttributes<HTMLDivElement> {
  status: Status;
}

const statusStyles: Record<Status, string> = {
  Verified: \'bg-teal/10 text-teal border-teal/20\',
  Pending: \'bg-amber/10 text-amber border-amber/20\',
  Disputed: \'bg-rose/10 text-rose border-rose/20\',
  \'Needs Verification\': \'bg-saffron/10 text-saffron border-saffron/20\',
  \'AI-Drafted\': \'bg-violet/10 text-violet border-violet/20\',
  Simulated: \'bg-muted/10 text-muted border-muted/20\',
};

const dotColors: Record<Status, string> = {
  Verified: \'bg-teal\',
  Pending: \'bg-amber animate-pulse\',
  Disputed: \'bg-rose animate-pulse\',
  \'Needs Verification\': \'bg-saffron animate-pulse\',
  \'AI-Drafted\': \'bg-violet\',
  Simulated: \'bg-muted\',
};

export const StatusChip: React.FC<StatusChipProps> = ({ status, className, ...props }) => {
  return (
    <div
      className={cn(
        \'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border\',
        statusStyles[status],
        className
      )}
      {...props}
    >
      <span className={cn(\'h-1.5 w-1.5 rounded-full\', dotColors[status])} />
      {status}
    </div>
  );
};
''',
    'components/ui/StatTile.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';
import { useCountUp } from \'../../hooks/useCountUp\';

export interface StatTileProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  trend?: number;
}

export const StatTile: React.FC<StatTileProps> = ({ title, value, prefix = \'\', suffix = \'\', trend, className, ...props }) => {
  const count = useCountUp(value, 1200);

  return (
    <div
      className={cn(
        \'p-5 rounded-card bg-surface border border-border hover:border-saffron/50 transition-colors group relative overflow-hidden\',
        className
      )}
      {...props}
    >
      <div className=\'absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity\'>
        <svg viewBox=\'0 0 100 50\' className=\'w-16 h-8 stroke-saffron fill-none stroke-2\'>
          <path d=\'M0 50 Q 25 25, 50 25 T 100 0\' />
        </svg>
      </div>
      <p className=\'text-sm font-medium text-muted mb-2\'>{title}</p>
      <div className=\'flex items-baseline gap-2\'>
        <h3 className=\'text-3xl font-heading font-bold text-text\'>
          {prefix}{count.toLocaleString()}{suffix}
        </h3>
        {trend !== undefined && (
          <span className={cn(\'text-sm font-medium\', trend >= 0 ? \'text-teal\' : \'text-rose\')}>
            {trend >= 0 ? \'+\' : \'\'}{trend}%
          </span>
        )}
      </div>
    </div>
  );
};
''',
    'components/ui/DataTable.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
  className?: string;
}

export function DataTable<T>({ data, columns, onRowClick, emptyState, className }: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return (
      <div className={cn(\'flex items-center justify-center p-8 border border-border rounded-lg text-muted bg-surface/50\', className)}>
        {emptyState || \'No data available.\'}
      </div>
    );
  }

  return (
    <div className={cn(\'w-full overflow-auto border border-border rounded-lg bg-surface\', className)}>
      <table className=\'w-full text-sm text-left\'>
        <thead className=\'bg-raised text-muted uppercase tracking-wider text-[10px] font-semibold border-b border-border\'>
          <tr>
            {columns.map((col, idx) => (
              <th key={col.key || idx} className={cn(\'px-4 py-3\', col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className=\'divide-y divide-border\'>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              onClick={() => onRowClick?.(row)}
              className={cn(
                \'group hover:bg-raised/50 transition-colors\',
                rowIndex % 2 === 0 ? \'bg-transparent\' : \'bg-surface/30\',
                onRowClick && \'cursor-pointer\'
              )}
            >
              {columns.map((col, colIndex) => (
                <td key={col.key || colIndex} className={cn(\'px-4 py-3\', col.className)}>
                  {col.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
''',
    'components/ui/Timeline.tsx': '''import React from \'react\';
import { motion } from \'framer-motion\';
import { cn } from \'../../lib/utils\';

export interface TimelineEvent {
  id: string;
  title: string;
  description: string;
  date: string;
  isActive?: boolean;
}

export interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ events, className }) => {
  return (
    <div className={cn(\'relative pl-6\', className)}>
      <div className=\'absolute left-2 top-2 bottom-2 w-px bg-border\'>
        <motion.div
          className=\'absolute top-0 left-0 w-full bg-saffron\'
          initial={{ height: 0 }}
          animate={{ height: \'100%\' }}
          transition={{ duration: 1.5, ease: \'easeInOut\' }}
        />
      </div>
      
      <div className=\'space-y-6 relative\'>
        {events.map((event, index) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.15 + 0.3 }}
            className=\'relative\'
          >
            <div className={cn(
              \'absolute -left-[30px] top-1.5 w-3 h-3 rounded-full border-2 bg-bg\',
              event.isActive ? \'border-saffron animate-pulse shadow-[0_0_8px_rgba(255,176,32,0.6)]\' : \'border-muted\'
            )} />
            <div className={cn(\'p-4 rounded-lg border bg-surface transition-colors\', event.isActive ? \'border-saffron/50\' : \'border-border\')}>
              <div className=\'flex justify-between items-start mb-1\'>
                <h4 className=\'font-semibold text-text\'>{event.title}</h4>
                <span className=\'text-xs text-muted font-mono\'>{event.date}</span>
              </div>
              <p className=\'text-sm text-muted\'>{event.description}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
''',
    'components/ui/Modal.tsx': '''import React from \'react\';
import { motion, AnimatePresence } from \'framer-motion\';
import { X } from \'lucide-react\';
import { cn } from \'../../lib/utils\';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children, footer, className }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className=\'fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm\'
            onClick={onClose}
          />
          <div className=\'fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none\'>
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: \'spring\', damping: 25, stiffness: 300 }}
              className={cn(\'bg-surface border border-border rounded-card shadow-2xl w-full max-w-lg pointer-events-auto overflow-hidden flex flex-col\', className)}
            >
              <div className=\'flex justify-between items-center p-4 border-b border-border\'>
                <h3 className=\'font-semibold text-lg text-text\'>{title}</h3>
                <button onClick={onClose} className=\'p-1 text-muted hover:text-text rounded-md hover:bg-raised transition-colors\'>
                  <X size={20} />
                </button>
              </div>
              <div className=\'p-4 flex-1 overflow-y-auto\'>
                {children}
              </div>
              {footer && (
                <div className=\'p-4 border-t border-border bg-raised/50 flex justify-end gap-2\'>
                  {footer}
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};
''',
    'components/ui/Toast.tsx': '''import React, { useState, useEffect } from \'react\';
import { motion, AnimatePresence } from \'framer-motion\';
import { X, CheckCircle, AlertCircle, Info } from \'lucide-react\';

export type ToastType = \'success\' | \'error\' | \'info\';

export interface ToastProps {
  id: string;
  title: string;
  message?: string;
  type?: ToastType;
  duration?: number;
  onDismiss: (id: string) => void;
}

const icons = {
  success: <CheckCircle className=\'text-teal\' size={20} />,
  error: <AlertCircle className=\'text-rose\' size={20} />,
  info: <Info className=\'text-violet\' size={20} />,
};

export const Toast: React.FC<ToastProps> = ({ id, title, message, type = \'info\', duration = 5000, onDismiss }) => {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (duration <= 0) return;
    
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    const updateProgress = () => {
      const now = Date.now();
      const remaining = Math.max(0, endTime - now);
      setProgress((remaining / duration) * 100);
      
      if (remaining > 0) {
        requestAnimationFrame(updateProgress);
      } else {
        onDismiss(id);
      }
    };
    
    const animId = requestAnimationFrame(updateProgress);
    return () => cancelAnimationFrame(animId);
  }, [id, duration, onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 50, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
      transition={{ type: \'spring\', damping: 25, stiffness: 300 }}
      className=\'bg-surface border border-border shadow-lg rounded-lg p-4 mb-3 w-80 relative overflow-hidden flex items-start gap-3 pointer-events-auto glass\'
    >
      <div className=\'shrink-0 mt-0.5\'>{icons[type]}</div>
      <div className=\'flex-1\'>
        <h4 className=\'text-sm font-semibold text-text\'>{title}</h4>
        {message && <p className=\'text-xs text-muted mt-1\'>{message}</p>}
      </div>
      <button onClick={() => onDismiss(id)} className=\'text-muted hover:text-text shrink-0\'>
        <X size={16} />
      </button>
      
      {duration > 0 && (
        <div className=\'absolute bottom-0 left-0 h-1 bg-border w-full\'>
          <div 
            className=\'h-full bg-saffron transition-all ease-linear\'
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </motion.div>
  );
};
''',
    'components/ui/CommandPalette.tsx': '''import React, { useState } from \'react\';
import { Search, Command, X } from \'lucide-react\';
import { Modal } from \'./Modal\';
import { cn } from \'../../lib/utils\';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState(\'\');

  const groups = [
    {
      name: \'Workspaces\',
      items: [{ id: \'w1\', name: \'Global Supply Chain\' }, { id: \'w2\', name: \'Acme Corp Vendor Mgt\' }]
    },
    {
      name: \'Actions\',
      items: [{ id: \'a1\', name: \'Create new claim\' }, { id: \'a2\', name: \'Invite member\' }]
    }
  ];

  const filteredGroups = query 
    ? groups.map(g => ({ ...g, items: g.items.filter(i => i.name.toLowerCase().includes(query.toLowerCase())) })).filter(g => g.items.length > 0)
    : groups;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title=\'Command Palette\' className=\'p-0 border-none bg-surface max-w-2xl overflow-hidden\'>
      <div className=\'flex items-center p-3 border-b border-border\'>
        <Search className=\'w-5 h-5 text-muted mr-2\' />
        <input 
          type=\'text\' 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder=\'Type a command or search...\'
          className=\'flex-1 bg-transparent border-none focus:ring-0 text-lg py-2 outline-none text-text\'
          autoFocus
        />
        {query && (
          <button onClick={() => setQuery(\'\')} className=\'p-1 text-muted hover:text-text rounded\'>
            <X className=\'w-4 h-4\' />
          </button>
        )}
        <div className=\'hidden sm:flex items-center gap-1 ml-4 text-xs text-muted font-mono bg-raised px-2 py-1 rounded\'>
          <Command className=\'w-3 h-3\' /> <span>K</span>
        </div>
      </div>
      
      <div className=\'max-h-[60vh] overflow-y-auto p-2\'>
        {filteredGroups.length === 0 ? (
          <div className=\'py-12 flex flex-col items-center justify-center text-muted\'>
            <div className=\'w-16 h-16 bg-raised rounded-full flex items-center justify-center mb-4\'>
               <Search className=\'w-8 h-8 opacity-50\' />
            </div>
            <p>No results found for "{query}"</p>
          </div>
        ) : (
          filteredGroups.map((group, idx) => (
            <div key={idx} className=\'mb-4\'>
              <h4 className=\'text-xs font-semibold text-muted uppercase tracking-wider px-3 mb-2\'>{group.name}</h4>
              <ul className=\'space-y-1\'>
                {group.items.map(item => (
                  <li key={item.id}>
                    <button className=\'w-full text-left px-3 py-2 rounded-md hover:bg-saffron/10 hover:text-saffron transition-colors text-sm text-text\'>
                      {item.name}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </div>
    </Modal>
  );
};
''',
    'components/layout/Sidebar.tsx': '''import React from \'react\';
import { NavLink } from \'react-router-dom\';
import { Home, LayoutDashboard, Component, Settings, ShieldCheck, HelpCircle, PanelLeftClose, PanelLeftOpen } from \'lucide-react\';
import { cn } from \'../../lib/utils\';
import { motion } from \'framer-motion\';

interface SidebarProps {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, setCollapsed }) => {
  const navItems = [
    { name: \'Home\', path: \'/\', icon: Home },
    { name: \'Dashboard\', path: \'/workspace\', icon: LayoutDashboard },
    { name: \'Components\', path: \'/components\', icon: Component },
  ];

  return (
    <motion.aside
      animate={{ width: collapsed ? 80 : 260 }}
      className=\'h-screen shrink-0 bg-surface border-r border-border flex flex-col glass relative z-20 transition-all duration-300 ease-in-out\'
    >
      <div className=\'h-16 flex items-center px-4 border-b border-border overflow-hidden\'>
        <ShieldCheck className=\'w-8 h-8 text-saffron shrink-0\' />
        <AnimateText show={!collapsed} className=\'ml-3 font-heading font-bold text-lg whitespace-nowrap\'>
          PilotProof
        </AnimateText>
      </div>

      <nav className=\'flex-1 py-6 px-3 space-y-1 overflow-y-auto overflow-x-hidden\'>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              \'flex items-center px-3 py-2.5 rounded-md transition-colors relative group\',
              isActive ? \'bg-saffron/10 text-saffron\' : \'text-muted hover:bg-raised hover:text-text\'
            )}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <motion.div layoutId=\'sidebar-active\' className=\'absolute left-0 top-1 bottom-1 w-1 bg-saffron rounded-r-md\' />
                )}
                <item.icon className=\'w-5 h-5 shrink-0\' />
                <AnimateText show={!collapsed} className=\'ml-3 font-medium whitespace-nowrap\'>
                  {item.name}
                </AnimateText>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className=\'p-4 mt-auto overflow-hidden\'>
        {!collapsed && (
          <div className=\'bg-raised rounded-lg p-3 mb-4 border border-border\'>
            <h5 className=\'text-xs font-semibold mb-1 text-text\'>System Status</h5>
            <div className=\'flex items-center gap-2 text-xs text-teal\'>
              <span className=\'w-2 h-2 rounded-full bg-teal animate-pulse\' /> All systems operational
            </div>
          </div>
        )}
        
        <button
          onClick={() => setCollapsed(!collapsed)}
          className=\'w-full flex items-center justify-center p-2 text-muted hover:text-text hover:bg-raised rounded-md transition-colors\'
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
    animate={{ opacity: show ? 1 : 0, width: show ? \'auto\' : 0 }}
    className={className}
    style={{ display: show ? \'block\' : \'none\' }}
  >
    {children}
  </motion.span>
);
''',
    'components/layout/AppShell.tsx': '''import React, { useState } from \'react\';
import { Sidebar } from \'./Sidebar\';
import { Bell, Search, Command } from \'lucide-react\';
import { CommandPalette } from \'../ui/CommandPalette\';
import { Outlet } from \'react-router-dom\';

export const AppShell: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === \'k\' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCmdOpen((open) => !open);
      }
    };
    document.addEventListener(\'keydown\', down);
    return () => document.removeEventListener(\'keydown\', down);
  }, []);

  return (
    <div className=\'flex h-screen bg-bg overflow-hidden\'>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      
      <div className=\'flex-1 flex flex-col min-w-0\'>
        <header className=\'h-16 shrink-0 bg-surface/80 backdrop-blur-md border-b border-border flex items-center justify-between px-6 z-10 sticky top-0\'>
          <div className=\'flex items-center text-sm text-muted\'>
            <span className=\'hover:text-text cursor-pointer transition-colors\'>Workspace</span>
            <span className=\'mx-2\'>/</span>
            <span className=\'text-text font-medium\'>Dashboard</span>
          </div>

          <div className=\'flex items-center gap-4\'>
            <button 
              onClick={() => setCmdOpen(true)}
              className=\'flex items-center gap-2 px-3 py-1.5 bg-raised border border-border rounded-md text-sm text-muted hover:text-text transition-colors focus-ring\'
            >
              <Search size={16} />
              <span>Search...</span>
              <div className=\'flex items-center gap-0.5 ml-2 text-[10px] font-mono opacity-60\'>
                <Command size={10} /> <span>K</span>
              </div>
            </button>
            
            <button className=\'relative p-2 text-muted hover:text-text rounded-full hover:bg-raised transition-colors focus-ring\'>
              <Bell size={20} />
              <span className=\'absolute top-1.5 right-1.5 w-2 h-2 bg-rose rounded-full border border-surface\'></span>
            </button>
            
            <div className=\'w-8 h-8 rounded-full bg-gradient-to-tr from-saffron to-rose cursor-pointer shadow-glow\'></div>
          </div>
        </header>
        
        <main className=\'flex-1 overflow-auto\'>
          <Outlet />
        </main>
      </div>

      <CommandPalette isOpen={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
};
''',
    'components/ui/Badge.tsx': '''import React from \'react\';
import { cva, type VariantProps } from \'class-variance-authority\';
import { cn } from \'../../lib/utils\';

const badgeVariants = cva(
  \'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-saffron/50 focus:ring-offset-2\',
  {
    variants: {
      variant: {
        default: \'border border-border bg-surface text-text\',
        success: \'border-transparent bg-teal/20 text-teal\',
        warning: \'border-transparent bg-amber/20 text-amber\',
        error: \'border-transparent bg-rose/20 text-rose\',
        info: \'border-transparent bg-violet/20 text-violet\',
      },
    },
    defaultVariants: {
      variant: \'default\',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
''',
    'components/ui/Input.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: boolean;
  success?: boolean;
  helperText?: string;
  leftSlot?: React.ReactNode;
  rightSlot?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, success, helperText, leftSlot, rightSlot, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className=\'flex flex-col gap-1 w-full relative group\'>
        {label && (
          <label htmlFor={inputId} className=\'text-sm font-medium text-muted mb-1 ml-1 group-focus-within:text-saffron transition-colors -translate-y-0.5\'>
            {label}
          </label>
        )}
        <div className=\'relative flex items-center w-full\'>
          {leftSlot && <div className=\'absolute left-3 text-muted\'>{leftSlot}</div>}
          <input
            id={inputId}
            ref={ref}
            className={cn(
              \'w-full\',
              leftSlot ? \'pl-10\' : \'pl-3\',
              rightSlot ? \'pr-10\' : \'pr-3\',
              error && \'border-rose focus:ring-rose/50 focus:border-rose\',
              success && \'border-teal focus:ring-teal/50 focus:border-teal\',
              className
            )}
            {...props}
          />
          {rightSlot && <div className=\'absolute right-3 text-muted\'>{rightSlot}</div>}
        </div>
        {helperText && (
          <span className={cn(\'text-xs ml-1 mt-1\', error ? \'text-rose\' : success ? \'text-teal\' : \'text-muted\')}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);
Input.displayName = \'Input\';
''',
    'components/ui/PageHeader.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

export interface PageHeaderProps {
  title: string;
  description?: string;
  eyebrow?: string;
  actionSlot?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, description, eyebrow, actionSlot, className }) => {
  return (
    <div className={cn(\'flex flex-col sm:flex-row sm:items-start justify-between gap-4 pb-6 mb-6 border-b border-border\', className)}>
      <div className=\'flex-1 slide-up\'>
        {eyebrow && <span className=\'text-saffron text-sm font-medium uppercase tracking-wider block mb-1\'>{eyebrow}</span>}
        <h1 className=\'text-3xl font-heading font-bold text-text\'>{title}</h1>
        {description && <p className=\'text-muted mt-2 max-w-2xl\'>{description}</p>}
      </div>
      {actionSlot && <div className=\'shrink-0 flex items-center gap-2 slide-up\' style={{ animationDelay: \'0.1s\' }}>{actionSlot}</div>}
    </div>
  );
};
''',
    'components/ui/LoadingSpinner.tsx': '''import React from \'react\';
import { cn } from \'../../lib/utils\';

interface LoadingSpinnerProps {
  size?: \'sm\' | \'md\' | \'lg\';
  className?: string;
}

const sizeClasses = {
  sm: \'w-4 h-4 border-2\',
  md: \'w-8 h-8 border-[3px]\',
  lg: \'w-12 h-12 border-4\',
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = \'md\', className }) => {
  return (
    <div
      className={cn(
        \'rounded-full animate-spin border-border border-t-saffron\',
        sizeClasses[size],
        className
      )}
    />
  );
};
''',
    'hooks/useCountUp.ts': '''import { useState, useEffect } from \'react\';

export function useCountUp(end: number, duration: number = 1200): number {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number | null = null;
    let animationFrame: number;

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      // easeOutExpo
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      
      setCount(Math.floor(easeProgress * end));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(step);
      } else {
        setCount(end);
      }
    };

    animationFrame = requestAnimationFrame(step);
    
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return count;
}
''',
    'pages/LandingPage.tsx': '''import React from \'react\';
import { motion } from \'framer-motion\';
import { ArrowRight, Shield, Zap, Search, ChevronRight } from \'lucide-react\';
import { Button } from \'../components/ui/Button\';
import { Card } from \'../components/ui/Card\';

export default function LandingPage() {
  return (
    <div className=\'min-h-screen bg-bg relative overflow-hidden flex flex-col\'>
      <div className=\'absolute top-0 right-0 -mr-40 -mt-40 w-[800px] h-[800px] bg-saffron/10 rounded-full blur-[100px] pointer-events-none\' />
      <div className=\'absolute bottom-0 left-0 -ml-40 -mb-40 w-[600px] h-[600px] bg-violet/10 rounded-full blur-[100px] pointer-events-none\' />
      
      <header className=\'container mx-auto px-6 py-6 flex justify-between items-center z-10 glass rounded-b-3xl sticky top-0\'>
        <div className=\'font-heading font-bold text-2xl flex items-center gap-2 text-text\'>
          <Shield className=\'text-saffron\' /> PilotProof
        </div>
        <div className=\'flex gap-4\'>
          <Button variant=\'ghost\'>Log in</Button>
          <Button variant=\'primary\'>Get Started</Button>
        </div>
      </header>

      <main className=\'flex-1 container mx-auto px-6 py-20 z-10\'>
        <div className=\'grid lg:grid-cols-2 gap-16 items-center\'>
          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <h1 className=\'text-5xl lg:text-7xl font-bold font-heading leading-tight mb-6\'>
              Evidence-backed <br/><span className=\'text-transparent bg-clip-text bg-gradient-to-r from-saffron to-rose\'>procurement.</span>
            </h1>
            <p className=\'text-xl text-muted mb-10 max-w-lg\'>
              Streamline your vendor evaluation process with verifiable claims, AI-drafted briefs, and undisputed evidence tracking.
            </p>
            <div className=\'flex gap-4\'>
              <Button size=\'lg\' variant=\'primary\' rightIcon={<ArrowRight size={18} />}>Start free trial</Button>
              <Button size=\'lg\' variant=\'outline\'>View documentation</Button>
            </div>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }} 
            animate={{ opacity: 1, scale: 1 }} 
            transition={{ duration: 0.6, delay: 0.2 }}
            className=\'relative perspective-1000\'
          >
            <Card glow elevated className=\'p-8 transform rotate-y-[-5deg] rotate-x-[5deg] transition-transform hover:rotate-0 duration-500 bg-surface/80 backdrop-blur-md\'>
               <h3 className=\'text-lg font-semibold mb-4 border-b border-border pb-2 text-text\'>Recent Verification Chain</h3>
               <div className=\'space-y-4\'>
                 {[1,2,3].map((i) => (
                   <div key={i} className=\'flex items-center gap-4 p-3 bg-raised rounded-md shimmer border border-border/50\'>
                     <div className=\'w-10 h-10 rounded bg-surface border border-border flex items-center justify-center text-saffron shrink-0\'>
                       <Shield size={20} />
                     </div>
                     <div className=\'flex-1\'>
                       <div className=\'h-4 w-1/2 bg-surface rounded mb-2\'></div>
                       <div className=\'h-3 w-3/4 bg-surface rounded\'></div>
                     </div>
                   </div>
                 ))}
               </div>
            </Card>
          </motion.div>
        </div>

        <section className=\'mt-32 mb-20\'>
          <h2 className=\'text-3xl font-heading font-bold text-center mb-16\'>How it works</h2>
          <div className=\'grid md:grid-cols-3 gap-8\'>
            {[
              { icon: Search, title: \'1. Discover\', desc: \'Find vendors matching your exact criteria using our AI semantic search.\' },
              { icon: Zap, title: \'2. Verify\', desc: \'Automatically validate vendor claims against our immutable evidence ledger.\' },
              { icon: Shield, title: \'3. Secure\', desc: \'Finalize contracts with mathematical certainty of performance history.\' }
            ].map((step, i) => (
              <motion.div key={i} whileHover={{ scale: 1.05 }} className=\'bg-surface border border-border p-8 rounded-card text-center hover:shadow-glow transition-all duration-300 group cursor-pointer\'>
                <div className=\'w-16 h-16 bg-raised rounded-full flex items-center justify-center mx-auto mb-6 text-saffron group-hover:bg-saffron group-hover:text-bg transition-colors\'>
                  <step.icon size={32} />
                </div>
                <h3 className=\'text-xl font-bold mb-3 text-text\'>{step.title}</h3>
                <p className=\'text-muted\'>{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <section className=\'mt-20\'>
           <div className=\'grid md:grid-cols-2 gap-8\'>
             {[{title: \'For Buyers\', desc: \'Reduce risk and evaluate vendors with verified facts, not marketing fluff.\'}, {title: \'For Vendors\', desc: \'Stand out by proving your capabilities with cryptographic certainty.\'}].map((role, i) => (
               <Card key={i} className=\'p-8 group hover:shadow-glow hover:-translate-y-1 transition-all cursor-pointer bg-gradient-to-br from-surface to-raised\'>
                 <h3 className=\'text-2xl font-bold font-heading mb-2 group-hover:text-saffron transition-colors\'>{role.title}</h3>
                 <p className=\'text-muted mb-6\'>{role.desc}</p>
                 <div className=\'flex items-center text-saffron font-medium\'>
                   Learn more <ChevronRight size={16} className=\'ml-1 group-hover:translate-x-1 transition-transform\'/>
                 </div>
               </Card>
             ))}
           </div>
        </section>
      </main>
      
      <footer className=\'border-t border-border mt-auto py-8 bg-surface/50\'>
        <div className=\'container mx-auto px-6 text-center text-muted text-sm\'>
          <p>© 2026 PilotProof. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
''',
    'pages/WorkspaceDashboard.tsx': '''import React from \'react\';
import { PageHeader } from \'../components/ui/PageHeader\';
import { StatTile } from \'../components/ui/StatTile\';
import { Card } from \'../components/ui/Card\';
import { Button } from \'../components/ui/Button\';
import { Plus, Download } from \'lucide-react\';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from \'recharts\';

const data = [
  { name: \'Jan\', claims: 4000 },
  { name: \'Feb\', claims: 3000 },
  { name: \'Mar\', claims: 5000 },
  { name: \'Apr\', claims: 2780 },
  { name: \'May\', claims: 6890 },
  { name: \'Jun\', claims: 8390 },
];

export default function WorkspaceDashboard() {
  return (
    <div className=\'p-6 max-w-7xl mx-auto fade-in\'>
      <PageHeader 
        title=\'Workspace Overview\' 
        eyebrow=\'Global Supply Chain\'
        actionSlot={
          <>
            <Button variant=\'outline\' leftIcon={<Download size={16} />}>Export</Button>
            <Button variant=\'primary\' leftIcon={<Plus size={16} />}>New Claim</Button>
          </>
        }
      />

      <div className=\'grid grid-cols-1 md:grid-cols-3 gap-6 mb-8\'>
        <StatTile title=\'Total Verifications\' value={12489} trend={12} />
        <StatTile title=\'Pending Claims\' value={432} trend={-5} />
        <StatTile title=\'Disputed Records\' value={18} trend={2} />
      </div>

      <div className=\'grid grid-cols-1 lg:grid-cols-3 gap-6\'>
        <Card className=\'lg:col-span-2 p-6\'>
          <h3 className=\'text-lg font-semibold mb-6\'>Verification Volume</h3>
          <div className=\'h-[300px] w-full\'>
            <ResponsiveContainer width=\'100%\' height=\'100%\'>
              <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id=\'colorClaims\' x1=\'0\' y1=\'0\' x2=\'0\' y2=\'1\'>
                    <stop offset=\'5%\' stopColor=\'var(--saffron)\' stopOpacity={0.8}/>
                    <stop offset=\'95%\' stopColor=\'var(--saffron)\' stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray=\'3 3\' stroke=\'var(--border)\' vertical={false} />
                <XAxis dataKey=\'name\' stroke=\'var(--muted)\' tick={{fill: \'var(--muted)\'}} axisLine={false} tickLine={false} />
                <YAxis stroke=\'var(--muted)\' tick={{fill: \'var(--muted)\'}} axisLine={false} tickLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: \'var(--surface)\', borderColor: \'var(--border)\', borderRadius: \'8px\' }}
                  itemStyle={{ color: \'var(--text)\' }}
                />
                <Area type=\'monotone\' dataKey=\'claims\' stroke=\'var(--saffron)\' strokeWidth={2} fillOpacity={1} fill=\'url(#colorClaims)\' />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className=\'p-6 bg-gradient-to-b from-surface to-raised border-saffron/30 relative overflow-hidden\'>
           <div className=\'absolute top-0 right-0 w-32 h-32 bg-saffron/10 rounded-full blur-[40px] pointer-events-none\'></div>
           <h3 className=\'text-lg font-semibold mb-2 relative z-10\'>Attention Required</h3>
           <p className=\'text-muted text-sm mb-6 relative z-10\'>You have 5 claims that require manual review before the end of the week.</p>
           
           <div className=\'space-y-3 relative z-10\'>
             {[1,2,3].map(i => (
               <div key={i} className=\'p-3 bg-bg rounded-md border border-border text-sm flex justify-between items-center hover:border-saffron/50 transition-colors cursor-pointer\'>
                 <span className=\'font-medium text-text\'>Claim #{8490 + i}</span>
                 <span className=\'text-rose text-xs font-medium\'>Review needed</span>
               </div>
             ))}
           </div>
           
           <Button className=\'w-full mt-6 relative z-10\' variant=\'outline\'>View All Pending</Button>
        </Card>
      </div>
    </div>
  );
}
''',
    'pages/DesignShowcasePage.tsx': '''import React from \'react\';
import { PageHeader } from \'../components/ui/PageHeader\';
import { Button } from \'../components/ui/Button\';
import { Badge } from \'../components/ui/Badge\';
import { StatusChip } from \'../components/ui/StatusChip\';
import { Card } from \'../components/ui/Card\';
import { Input } from \'../components/ui/Input\';
import { Search, Mail } from \'lucide-react\';

export default function DesignShowcasePage() {
  return (
    <div className=\'p-6 max-w-6xl mx-auto flex gap-10 fade-in\'>
      <div className=\'w-48 shrink-0 hidden md:block\'>
        <div className=\'sticky top-24 space-y-2\'>
          <h3 className=\'font-semibold text-sm uppercase tracking-wider text-muted mb-4\'>Components</h3>
          {[\'Buttons\', \'Badges & Chips\', \'Inputs\', \'Cards\'].map(item => (
            <a key={item} href={`#${item.toLowerCase().replace(/ /g, \'-\')}`} className=\'block text-sm text-muted hover:text-saffron py-1 transition-colors\'>
              {item}
            </a>
          ))}
        </div>
      </div>
      
      <div className=\'flex-1 space-y-16 pb-20\'>
        <PageHeader title=\'Design Showcase\' description=\'A collection of all UI components used in PilotProof.\' />
        
        <section id=\'buttons\' className=\'space-y-6\'>
          <div className=\'border-b border-border pb-2\'>
            <h2 className=\'text-2xl font-heading font-semibold\'>Buttons</h2>
          </div>
          <Card className=\'p-8 flex flex-wrap gap-4 items-center\'>
            <Button>Default</Button>
            <Button variant=\'primary\'>Primary</Button>
            <Button variant=\'outline\'>Outline</Button>
            <Button variant=\'ghost\'>Ghost</Button>
            <Button variant=\'danger\'>Danger</Button>
            <Button isLoading>Loading</Button>
            <Button leftIcon={<Mail size={16} />}>With Icon</Button>
          </Card>
        </section>

        <section id=\'badges-&-chips\' className=\'space-y-6\'>
          <div className=\'border-b border-border pb-2\'>
            <h2 className=\'text-2xl font-heading font-semibold\'>Badges & Status Chips</h2>
          </div>
          <Card className=\'p-8 flex flex-wrap gap-4 items-center\'>
            <Badge>Default</Badge>
            <Badge variant=\'success\'>Success</Badge>
            <Badge variant=\'warning\'>Warning</Badge>
            <Badge variant=\'error\'>Error</Badge>
            <Badge variant=\'info\'>Info</Badge>
            
            <div className=\'w-px h-6 bg-border mx-4\'></div>
            
            <StatusChip status=\'Verified\' />
            <StatusChip status=\'Pending\' />
            <StatusChip status=\'Disputed\' />
            <StatusChip status=\'Needs Verification\' />
            <StatusChip status=\'AI-Drafted\' />
          </Card>
        </section>

        <section id=\'inputs\' className=\'space-y-6\'>
          <div className=\'border-b border-border pb-2\'>
            <h2 className=\'text-2xl font-heading font-semibold\'>Inputs</h2>
          </div>
          <Card className=\'p-8 grid md:grid-cols-2 gap-6\'>
            <Input label=\'Standard Input\' placeholder=\'Type here...\' />
            <Input label=\'With Icon\' leftSlot={<Search size={16} />} placeholder=\'Search...\' />
            <Input label=\'Error State\' error helperText=\'This field is required.\' defaultValue=\'Invalid value\' />
            <Input label=\'Success State\' success helperText=\'Looks good!\' defaultValue=\'Valid value\' />
          </Card>
        </section>
        
        <section id=\'cards\' className=\'space-y-6\'>
          <div className=\'border-b border-border pb-2\'>
            <h2 className=\'text-2xl font-heading font-semibold\'>Cards</h2>
          </div>
          <div className=\'grid md:grid-cols-2 gap-6\'>
            <Card className=\'p-6\'>
              <h3 className=\'font-semibold mb-2\'>Default Card</h3>
              <p className=\'text-muted text-sm\'>Standard surface card with border.</p>
            </Card>
            <Card elevated className=\'p-6\'>
              <h3 className=\'font-semibold mb-2\'>Elevated Card</h3>
              <p className=\'text-muted text-sm\'>Card with shadow and raised background.</p>
            </Card>
            <Card glow className=\'p-6 md:col-span-2\'>
              <h3 className=\'font-semibold mb-2\'>Glow Card</h3>
              <p className=\'text-muted text-sm\'>Card with custom saffron glow hover effect.</p>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
''',
    'App.tsx': '''import React, { Suspense } from \'react\';
import { BrowserRouter, Routes, Route } from \'react-router-dom\';
import { AppShell } from \'./components/layout/AppShell\';
import { LoadingSpinner } from \'./components/ui/LoadingSpinner\';

const LandingPage = React.lazy(() => import(\'./pages/LandingPage\'));
const WorkspaceDashboard = React.lazy(() => import(\'./pages/WorkspaceDashboard\'));
const DesignShowcasePage = React.lazy(() => import(\'./pages/DesignShowcasePage\'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className=\'h-screen w-screen flex items-center justify-center bg-bg\'><LoadingSpinner size=\'lg\' /></div>}>
        <Routes>
          <Route path=\'/\' element={<LandingPage />} />
          <Route element={<AppShell />}>
            <Route path=\'/workspace\' element={<WorkspaceDashboard />} />
            <Route path=\'/components\' element={<DesignShowcasePage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
'''
}

for filepath, content in files.items():
    full_path = os.path.join(base_dir, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Created {full_path}')
