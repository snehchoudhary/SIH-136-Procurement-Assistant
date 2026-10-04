// ─── Domain Types ──────────────────────────────────────────────────────────────

export type Theme = 'dark' | 'light';

export type Role =
  | 'Officer'
  | 'Startup'
  | 'Evaluator'
  | 'Validator'
  | 'Finance'
  | 'Receiving District';

export type StatusType =
  | 'Verified'
  | 'Pending'
  | 'Disputed'
  | 'Needs Verification'
  | 'AI-Drafted'
  | 'Simulated';

// ─── Navigation ────────────────────────────────────────────────────────────────

export type NavItem = {
  label: string;
  href: string;
};
