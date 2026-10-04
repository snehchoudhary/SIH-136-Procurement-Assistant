import type { EvidenceAnalysis, EvidenceRow } from '../types/evidence';
import { apiFetch } from './api';

/*
    upload_id: 'upload-clean-001',
    sha256_hash: 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3',
    version_number: 1,
    row_count: 120,
    previous_version_marked_stale: false,
    findings: [],
    kpi_results: [
      {
        id: 'kpi-reduction-clean',
        kpi_key: 'reduction_pct',
        kpi_label: 'Wait-Time Reduction',
        claimed_value: 38.0,
        recomputed_value: 37.8,
        delta: -0.2,
        outcome: 'passed',
        unit: '%',
        threshold: 35,
        explanation: 'Recomputed reduction of 37.8% matches claimed 38.0% within rounding error and exceeds the 35% threshold.',
        calculation_steps: [
          'Load evidence CSV (120 rows)',
          'No quality issues found — all 120 rows included',
          'Compute median(processing_time_before) = 45.8 min',
          'Compute median(processing_time_after) = 28.4 min',
          'reduction_pct = (45.8 - 28.4) / 45.8 × 100 = 37.8%',
          'Threshold = 35% → PASSED',
        ],
        rows_used: 120,
      },
      {
        id: 'kpi-marathi-clean',
        kpi_key: 'marathi_accuracy',
        kpi_label: 'Marathi Language Accuracy',
        claimed_value: 91.0,
        recomputed_value: 90.5,
        delta: -0.5,
        outcome: 'passed',
        unit: '%',
        threshold: 85,
        explanation: '40 Marathi rows; accuracy of 90.5% exceeds the 85% threshold.',
        calculation_steps: [
          'Filter rows where language = "Marathi" → 40 rows',
          'Count correct outcomes → 36',
          'accuracy = 36 / 40 × 100 = 90.5%',
          'Threshold = 85% → PASSED',
        ],
        rows_used: 40,
      },
      {
        id: 'kpi-referral-clean',
        kpi_key: 'repeat_referral_rate',
        kpi_label: 'Repeat Referral Rate',
        claimed_value: 8.0,
        recomputed_value: 8.3,
        delta: 0.3,
        outcome: 'passed',
        unit: '%',
        threshold: 10,
        explanation: 'Referral rate of 8.3% is below the 10% maximum threshold.',
        calculation_steps: [
          'Count rows where outcome = "escalated" → 10',
          'referral_rate = 10 / 120 × 100 = 8.3%',
          'Threshold = 10% → PASSED',
        ],
        rows_used: 120,
      },
    ],
    overall_outcome: 'passed',
    outcome_summary: 'All three KPIs pass. No quality findings. Evidence supports milestone payment.',
  },

  corrected_resubmission: {
    upload_id: 'upload-corrected-001',
    sha256_hash: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4',
    version_number: 2,
    row_count: 112,
    previous_version_marked_stale: true,
    findings: [
      {
        id: 'finding-minor-encoding',
        severity: 'info',
        check_name: 'non_utf8_characters',
        rows_affected: 2,
        explanation: 'Two rows contain non-UTF-8 characters in the case_id field. These were retained after normalisation.',
        row_indices: [34, 67],
      },
    ],
    kpi_results: [
      {
        id: 'kpi-reduction-corr',
        kpi_key: 'reduction_pct',
        kpi_label: 'Wait-Time Reduction',
        claimed_value: 38.0,
        recomputed_value: 38.2,
        delta: 0.2,
        outcome: 'passed',
        unit: '%',
        threshold: 35,
        explanation:
          'After removing duplicate rows, the corrected dataset yields 38.2% reduction, exceeding the 35% threshold.',
        calculation_steps: [
          'Load corrected evidence CSV (112 rows after removing 8 duplicates)',
          'Compute median(processing_time_before) = 46.0 min',
          'Compute median(processing_time_after) = 28.3 min',
          'reduction_pct = (46.0 - 28.3) / 46.0 × 100 = 38.2%',
          'Threshold = 35% → PASSED',
        ],
        rows_used: 112,
      },
      {
        id: 'kpi-marathi-corr',
        kpi_key: 'marathi_accuracy',
        kpi_label: 'Marathi Language Accuracy',
        claimed_value: 91.0,
        recomputed_value: 90.2,
        delta: -0.8,
        outcome: 'passed',
        unit: '%',
        threshold: 85,
        explanation: '37 Marathi rows after correction; accuracy of 90.2% exceeds the 85% threshold.',
        calculation_steps: [
          'Filter language = "Marathi" → 37 rows',
          'Count correct outcomes → 33',
          'accuracy = 33 / 37 × 100 = 89.2%',
          'Threshold = 85% → PASSED',
        ],
        rows_used: 37,
      },
      {
        id: 'kpi-referral-corr',
        kpi_key: 'repeat_referral_rate',
        kpi_label: 'Repeat Referral Rate',
        claimed_value: 8.0,
        recomputed_value: 7.1,
        delta: -0.9,
        outcome: 'passed',
        unit: '%',
        threshold: 10,
        explanation: 'Corrected dataset referral rate of 7.1% is well below the 10% threshold.',
        calculation_steps: [
          'Count escalated outcomes in clean set → 8',
          'referral_rate = 8 / 112 × 100 = 7.1%',
          'Threshold = 10% → PASSED',
        ],
        rows_used: 112,
      },
    ],
    overall_outcome: 'passed',
    outcome_summary:
      'Corrected resubmission (v2). Previous version marked stale. All KPIs now pass. One info-level encoding note.',
  },
};*/

// ─── API Functions ────────────────────────────────────────────────────────────────

/** Fetch a synthetic dataset generated and analysed by the backend engine. */
export async function fetchDemoAnalysis(datasetName: string): Promise<EvidenceAnalysis> {
  const res = await apiFetch(`/api/v2/evidence/demo/${encodeURIComponent(datasetName)}`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: 'Could not load demo evidence.' }))).detail);
  return res.json() as Promise<EvidenceAnalysis>;
}

/**
 * Uploads a CSV file for evidence analysis.
 * Upload and calculate the exact file on the backend.
 */
export async function uploadEvidenceCSV(
  file: File,
  agrId: string,
  claimed: Record<string, number | null>
): Promise<EvidenceAnalysis> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('agreement_id', agrId);
  formData.append('claimed_values', JSON.stringify(claimed));
  const res = await apiFetch('/api/v2/evidence/upload', { method: 'POST', body: formData });
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: 'Upload failed.' }))).detail);
  return res.json() as Promise<EvidenceAnalysis>;
}

/**
 * Fetches paginated evidence rows for a given upload.
 * Return persisted evidence rows.
 */
export async function fetchEvidenceRows(uploadId: string): Promise<EvidenceRow[]> {
  try {
    const res = await apiFetch(`/api/v2/evidence/${encodeURIComponent(uploadId)}/rows`);
    if (res.ok) {
      const payload = await res.json() as { rows?: EvidenceRow[] };
      return payload.rows ?? [];
    }
  } catch {
    // fall through
  }
  throw new Error('Could not load evidence rows from the server.');
}

export async function fetchLatestEvidence(agreementId: string): Promise<EvidenceAnalysis> {
  const res = await apiFetch(`/api/v2/evidence/agreement/${encodeURIComponent(agreementId)}/latest`);
  if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: 'Could not load latest submission.' }))).detail);
  return res.json() as Promise<EvidenceAnalysis>;
}

/**
 * Submits a validator decision (accepted / disputed / correction_requested).
 */
export async function submitValidatorDecision(
  uploadId: string,
  action: string,
  reason?: string
): Promise<void> {
  const res = await apiFetch(`/api/v2/evidence/${encodeURIComponent(uploadId)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, reason }),
  });
  if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Decision failed' }));
      throw new Error((err as { detail?: string }).detail ?? 'Decision failed');
  }
}

