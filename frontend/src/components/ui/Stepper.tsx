import { cn } from '../../lib/utils';

type StepperProps = {
  steps: string[];
  active: number;
};

export function Stepper({ steps, active }: StepperProps) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <div key={step} className="flex items-center gap-3">
          <div
            className={cn(
              'flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold',
              index <= active ? 'bg-primary text-on-primary' : 'bg-raised text-muted',
            )}
          >
            {index + 1}
          </div>
          <div
            className={cn(
              'flex-1 rounded-lg border px-3 py-2 text-sm',
              index === active
                ? 'border-primary/40 bg-primary/5 text-text'
                : 'border-border bg-raised/50 text-muted',
            )}
          >
            {step}
          </div>
        </div>
      ))}
    </div>
  );
}
