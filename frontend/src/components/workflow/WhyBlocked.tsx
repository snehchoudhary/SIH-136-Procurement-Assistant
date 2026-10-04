import { ArrowRight, FileCheck2, ReceiptText, ShieldCheck, UserRoundCheck, WalletCards } from 'lucide-react';
import { Card } from '../ui/Card';

export type BlockingDependency = 'evidence' | 'validator' | 'approver' | 'invoice' | 'payment';

const dependencyDetails: Record<BlockingDependency, { title: string; explanation: string; nextActor: string; icon: typeof FileCheck2 }> = {
  evidence: {
    title: 'Evidence is incomplete',
    explanation: 'One or more required pilot files or measurements have not been submitted or linked to the milestone.',
    nextActor: 'Startup: submit or correct the evidence item',
    icon: FileCheck2,
  },
  validator: {
    title: 'Independent validation is pending',
    explanation: 'Submitted evidence is waiting for an independent reviewer to check the source and measurement context.',
    nextActor: 'Validator: review the submitted evidence and record a reason',
    icon: ShieldCheck,
  },
  approver: {
    title: 'An approval is outstanding',
    explanation: 'The next lifecycle step cannot proceed until the assigned approver records a decision and reason.',
    nextActor: 'Officer: review the record and approve or request a correction',
    icon: UserRoundCheck,
  },
  invoice: {
    title: 'Invoice review is holding the milestone',
    explanation: 'Outcome review is complete, but the invoice has not been checked against the agreement and milestone.',
    nextActor: 'Finance: verify invoice details and record the review outcome',
    icon: ReceiptText,
  },
  payment: {
    title: 'Payment status has not been confirmed',
    explanation: 'Payment tracking remains open. This workspace records simulated settlement status only.',
    nextActor: 'Finance: update the tracked payment status',
    icon: WalletCards,
  },
};

type WhyBlockedProps = {
  dependency: BlockingDependency;
  milestone: string;
};

export function WhyBlocked({ dependency, milestone }: WhyBlockedProps) {
  const detail = dependencyDetails[dependency];
  const Icon = detail.icon;

  return (
    <Card className="border-warning/30 p-5">
      <div className="flex items-start gap-3">
        <span className="rounded-xl bg-warning/10 p-2 text-warning"><Icon className="h-5 w-5" /></span>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.18em] text-warning">Why this milestone is blocked</p>
          <h3 className="mt-1 font-heading text-lg font-semibold text-text">{milestone}: {detail.title}</h3>
          <p className="mt-2 text-sm text-muted">{detail.explanation}</p>
          <p className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-text"><ArrowRight className="h-4 w-4 text-primary" />{detail.nextActor}</p>
        </div>
      </div>
    </Card>
  );
}
