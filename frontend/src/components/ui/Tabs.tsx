import { useState } from 'react';
import { cn } from '../../lib/utils';

type TabItem = { label: string; content: React.ReactNode };

type TabsProps = {
  items: TabItem[];
};

export function Tabs({ items }: TabsProps) {
  const [active, setActive] = useState(0);

  return (
    <div className="space-y-4">
      <div className="flex gap-2 rounded-xl border border-border bg-raised/60 p-1">
        {items.map((item, index) => (
          <button
            key={item.label}
            onClick={() => setActive(index)}
            className={cn(
              'flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              index === active ? 'bg-primary text-on-primary' : 'text-muted hover:text-text',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="rounded-card border border-border bg-surface/70 p-4 text-sm text-text">
        {items[active].content}
      </div>
    </div>
  );
}
