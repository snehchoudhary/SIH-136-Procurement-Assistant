// ─── Evidence Verification Types ────────────────────────────────────────────────

export type Severity = 'critical' | 'major' | 'minor' | 'info';
export type KPIOutcome = 'passed' | 'failed' | 'missing_evidence';
export type EvidenceOutcome = KPIOutcome | 'pending';
export type ValidatorAction = 'accepted' | 'disputed' | 'correction_requested';

export interface QualityFinding {
  id: string;
  severity: Severity;
  check_name: string;
  rows_affected: number;
  explanation: string;
  row_indices: number[];
}

export interface KPIResult {
  id: string;
  kpi_key: string;
  kpi_label: string;
  claimed_value: number | null;
  recomputed_value: number | null;
  delta: number | null;
  outcome: KPIOutcome;
  unit: string;
  threshold: number | null;
  explanation: string;
  calculation_steps: string[];
  rows_used: number;
  python_code?: string;
  is_stale?: boolean;
}

export interface EvidenceAnalysis {
  upload_id: string;
  sha256_hash: string;
  version_number: number;
  row_count: number;
  previous_version_marked_stale: boolean;
  findings: QualityFinding[];
  kpi_results: KPIResult[];
  overall_outcome: EvidenceOutcome;
  outcome_summary: string;
  rows?: EvidenceRow[];
  is_demo?: boolean;
  milestone_status?: string;
}

export interface EvidenceRow {
  [key: string]: unknown;
  _flagged: boolean;
  _finding_ids: string[];
  _row_index: number;
}

export interface ReproduceStep {
  kpi_key: string;
  kpi_label: string;
  calculation_steps: string[];
  python_code: string;
  rows_used: number;
  recomputed_value: number | null;
}
