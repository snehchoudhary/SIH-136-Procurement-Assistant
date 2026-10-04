import {
  AlertTriangle,
  Building2,
  CircleDashed,
  Hourglass,
  Landmark,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react';
import type { NavItem, Role, StatusType } from '../types';

// ─── Navigation map per role ────────────────────────────────────────────────────

export const roleNavMap: Record<Role, NavItem[]> = {
  Officer: [
    { label: 'Overview', href: '/workspace' },
    { label: 'Evidence', href: '/workspace' },
    { label: 'Timeline', href: '/workspace' },
    { label: 'Recommendation', href: '/workspace' },
  ],
  Startup: [
    { label: 'Overview', href: '/workspace' },
    { label: 'Evidence', href: '/workspace' },
    { label: 'Payments', href: '/workspace' },
    { label: 'Validation', href: '/workspace' },
  ],
  Evaluator: [
    { label: 'Overview', href: '/workspace' },
    { label: 'Evidence', href: '/workspace' },
    { label: 'Standards', href: '/workspace' },
    { label: 'Recommendation', href: '/workspace' },
  ],
  Validator: [
    { label: 'Overview', href: '/workspace' },
    { label: 'Validation', href: '/workspace' },
    { label: 'Evidence', href: '/workspace' },
    { label: 'Payments', href: '/workspace' },
  ],
  Finance: [
    { label: 'Overview', href: '/workspace' },
    { label: 'Payments', href: '/workspace' },
    { label: 'Validation', href: '/workspace' },
    { label: 'Recommendation', href: '/workspace' },
  ],
  'Receiving District': [
    { label: 'Overview', href: '/workspace' },
    { label: 'Evidence', href: '/workspace' },
    { label: 'Timeline', href: '/workspace' },
    { label: 'Recommendation', href: '/workspace' },
  ],
};

export const roleOptions: Role[] = [
  'Officer',
  'Startup',
  'Evaluator',
  'Validator',
  'Finance',
  'Receiving District',
];

// ─── Evidence table rows ────────────────────────────────────────────────────────

export const evidenceTableRows = [
  {
    id: 'EV-1042',
    status: 'Verified' as StatusType,
    source: 'Simulated · Startup India',
    lastUpdated: '2h ago',
    reason: 'Baseline matched procurement brief',
  },
  {
    id: 'EV-1044',
    status: 'Needs Verification' as StatusType,
    source: 'Simulated · GeM',
    lastUpdated: '4h ago',
    reason: 'Invoice linked but route not confirmed',
  },
  {
    id: 'EV-1049',
    status: 'AI-Drafted' as StatusType,
    source: 'AI summary',
    lastUpdated: '1d ago',
    reason: 'Human review required before approval',
  },
  {
    id: 'EV-1057',
    status: 'Disputed' as StatusType,
    source: 'Validator',
    lastUpdated: '3d ago',
    reason: 'Evidence mismatch on asset count',
  },
];

// ─── Sparkline chart data ───────────────────────────────────────────────────────

export const sparklineData = [
  { value: 18 },
  { value: 26 },
  { value: 21 },
  { value: 34 },
  { value: 48 },
  { value: 42 },
  { value: 60 },
  { value: 66 },
  { value: 72 },
];

// ─── Procurement lifecycle steps ────────────────────────────────────────────────

export const procurementLifecycleSteps = [
  'Define the problem and baseline',
  'Discover applicant evidence and constraints',
  'Pilot with measurable outputs',
  'Prove outcomes and reconcile payment status',
  'Scale the decision with traceable evidence',
];

// ─── Evidence timeline events ───────────────────────────────────────────────────

export const evidenceTimelineEvents = [
  {
    title: 'Problem statement approved',
    detail: 'Challenge brief and baseline criteria signed.',
    time: '09:30',
  },
  {
    title: 'Eligibility evidence submitted',
    detail: 'Startup files and project commitments checked.',
    time: '10:15',
  },
  {
    title: 'Pilot launched',
    detail: 'Field trial and service logs captured with timestamps.',
    time: '11:00',
  },
  {
    title: 'Independent validation',
    detail: 'District validator confirmed evidence and sample checks.',
    time: '14:30',
  },
  {
    title: 'Payment recommendation',
    detail: 'Outcome and responsibility record reviewed for next stage.',
    time: '18:10',
  },
];

// ─── Status metadata ────────────────────────────────────────────────────────────

export const statusMeta: Record<
  StatusType,
  { label: string; icon: typeof ShieldCheck; tint: string }
> = {
  Verified: { label: 'Verified', icon: ShieldCheck, tint: 'text-success' },
  Pending: { label: 'Pending', icon: Hourglass, tint: 'text-warning' },
  Disputed: { label: 'Disputed', icon: AlertTriangle, tint: 'text-danger' },
  'Needs Verification': {
    label: 'Needs Verification',
    icon: CircleDashed,
    tint: 'text-warning',
  },
  'AI-Drafted': { label: 'AI-Drafted', icon: Sparkles, tint: 'text-primary' },
  Simulated: { label: 'Simulated', icon: Workflow, tint: 'text-muted' },
};

// ─── Role cards for landing page ────────────────────────────────────────────────

export const roleCards = [
  { title: 'Officer', accent: 'bg-primary/10 text-primary', icon: ShieldCheck },
  { title: 'Startup', accent: 'bg-success/10 text-success', icon: Workflow },
  { title: 'Evaluator', accent: 'bg-primary/10 text-primary', icon: Sparkles },
  { title: 'Validator', accent: 'bg-warning/10 text-warning', icon: AlertTriangle },
  { title: 'Finance', accent: 'bg-danger/10 text-danger', icon: Landmark },
  {
    title: 'Receiving District',
    accent: 'bg-primary/10 text-primary',
    icon: Building2,
  },
] as const;
