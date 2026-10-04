import { Check, Copy } from 'lucide-react';
import { useState } from 'react';

type HashBadgeProps = {
  value: string;
};

export function HashBadge({ value }: HashBadgeProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-raised/60 px-2.5 py-1 font-mono text-[11px] text-text"
    >
      <span className="truncate max-w-[12rem]">{value}</span>
      {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5 text-muted" />}
    </button>
  );
}
