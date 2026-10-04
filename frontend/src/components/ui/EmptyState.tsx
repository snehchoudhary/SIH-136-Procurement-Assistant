import { Folder } from 'lucide-react';

type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center rounded-card border border-dashed border-border bg-raised/30 px-6 text-center text-muted">
      <Folder className="mb-3 h-6 w-6 text-primary" />
      <h3 className="text-lg font-heading font-semibold text-text">{title}</h3>
      <p className="mt-2 max-w-sm text-sm">{description}</p>
    </div>
  );
}
