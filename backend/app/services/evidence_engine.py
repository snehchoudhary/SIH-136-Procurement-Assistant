"""Evidence verification computation engine.

This module is the single source of truth for all data-quality checks and KPI
recomputations.  It is intentionally dependency-free (no FastAPI, no SQLAlchemy)
so it can be tested in isolation with plain DataFrames.
"""

import hashlib
import io
import json
import random
from typing import IO

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Locked measurement plan (agreed in the pilot agreement template)
# ---------------------------------------------------------------------------

MEASUREMENT_PLAN: dict = {
    "baseline_minutes": 45.0,
    "target_reduction_pct": 30.0,   # at least 30 % reduction required to pass
    "max_error_rate_pct": 5.0,
    "min_marathi_accuracy_pct": 85.0,
    "min_marathi_samples": 30,
    "max_bandwidth_mbps": 2.0,
    "min_total_observations": 100,
    "min_low_bandwidth_success_pct": 80.0,
    "min_segment_samples": 30,
    "capacity_per_day": 100,
    "min_low_bandwidth_samples": 10,
}

# Bump when the calculation contract changes so a later upload is comparable
# only to results produced by the same engine definition.
CALCULATOR_VERSION = "evidence-engine-v2"

REQUIRED_COLUMNS: list[str] = [
    "language",
    "processing_time_before",
    "processing_time_after",
    "error_flag",
    "low_bandwidth",
    "outcome",
    "period",
]


# ---------------------------------------------------------------------------
# SHA-256 helper
# ---------------------------------------------------------------------------


def compute_sha256(file_obj: IO[bytes]) -> str:
    """Return the SHA-256 hex digest of *file_obj* without loading it fully
    into memory.  The file pointer is rewound to the beginning afterwards.
    """
    hasher = hashlib.sha256()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(65536), b""):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------


def run_quality_checks(
    df: pd.DataFrame,
    prev_df: pd.DataFrame | None = None,
    previous_metric_definition_hash: str | None = None,
    metric_definition_hash: str | None = None,
    measurement_plan: dict | None = None,
) -> list[dict]:
    """Run all data-quality checks and return a list of finding dicts.

    Each dict has keys: severity, check_name, rows_affected, explanation,
    row_indices (list of int 0-based positions into *df*).
    """
    findings: list[dict] = []
    plan = {**MEASUREMENT_PLAN, **(measurement_plan or {})}

    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        findings.append({
            "severity": "critical",
            "check_name": "missing_required_columns",
            "rows_affected": len(df),
            "explanation": f"Required evidence columns are missing: {', '.join(missing_columns)}.",
            "row_indices": df.index.tolist(),
        })

    # 1. missing_periods ---------------------------------------------------
    # Check whether 'period' column has gaps (e.g. weeks 1, 2, 4 but not 3).
    if "period" in df.columns:
        numeric_periods = pd.to_numeric(df["period"], errors="coerce")
        periods = numeric_periods.dropna().unique()
        whole_periods = [int(p) for p in periods if float(p).is_integer()]
        if len(whole_periods) > 0:
            min_p = min(whole_periods) if whole_periods else 0
            max_p = max(whole_periods) if whole_periods else -1
            expected = set(range(min_p, max_p + 1)) if whole_periods else set()
            present = set(whole_periods)
            missing_periods = sorted(expected - present)
            missing_period_rows = df[(numeric_periods.isna() | (numeric_periods % 1 != 0))].index.tolist()
            if missing_periods or missing_period_rows:
                findings.append(
                    {
                        "severity": "major",
                        "check_name": "missing_periods",
                        "rows_affected": len(missing_period_rows),
                        "explanation": (
                            f"Period column has gaps: periods {missing_periods} are absent "
                            f"from the data (range {min_p}–{max_p}).  "
                            f"{len(missing_period_rows)} rows have a null or invalid period value."
                        ),
                        "row_indices": missing_period_rows,
                    }
                )
        elif len(df):
            findings.append({"severity": "major", "check_name": "missing_periods", "rows_affected": len(df),
                "explanation": "No valid integer periods were provided.", "row_indices": df.index.tolist()})

    # 2. duplicate_rows ----------------------------------------------------
    if "case_id" in df.columns and "period" in df.columns:
        dup_mask = df.duplicated(subset=["case_id", "period"], keep=False)
        dup_indices = df[dup_mask].index.tolist()
        if dup_indices:
            findings.append(
                {
                    "severity": "critical",
                    "check_name": "duplicate_rows",
                    "rows_affected": len(dup_indices),
                    "explanation": (
                        f"{len(dup_indices)} rows have duplicate (case_id, period) combinations. "
                        "Each case should appear at most once per period."
                    ),
                    "row_indices": dup_indices,
                }
            )

    # 3. unsupported_denominators ------------------------------------------
    invalid_mask = pd.Series(False, index=df.index)
    baseline = pd.to_numeric(df["processing_time_before"], errors="coerce") if "processing_time_before" in df.columns else pd.Series(float('nan'), index=df.index)
    after = pd.to_numeric(df["processing_time_after"], errors="coerce") if "processing_time_after" in df.columns else pd.Series(float('nan'), index=df.index)
    invalid_mask |= baseline.isna() | (baseline <= 0) | after.isna() | (after <= 0)
    invalid_indices = df[invalid_mask].index.tolist()
    if invalid_indices:
        findings.append(
            {
                "severity": "critical",
                "check_name": "unsupported_denominators",
                "rows_affected": len(invalid_indices),
                "explanation": (
                    f"{len(invalid_indices)} rows have missing, non-numeric, or non-positive "
                    "processing-time values, which cannot support the locked calculation."
                ),
                "row_indices": invalid_indices,
            }
        )

    # 4. changed_metric_definition -----------------------------------------
    if prev_df is not None:
        prev_cols = set(prev_df.columns)
        curr_cols = set(df.columns)
        added = curr_cols - prev_cols
        removed = prev_cols - curr_cols
        if added or removed:
            findings.append(
                {
                    "severity": "critical",
                    "check_name": "changed_metric_definition",
                    "rows_affected": 0,
                    "explanation": (
                        "Column schema differs from the previous submission. "
                        f"Added: {sorted(added) or 'none'}.  "
                        f"Removed: {sorted(removed) or 'none'}.  "
                        "This breaks comparability across versions."
                    ),
                    "row_indices": [],
                }
            )
        if (previous_metric_definition_hash and metric_definition_hash
                and previous_metric_definition_hash != metric_definition_hash):
            findings.append({
                "severity": "critical", "check_name": "changed_metric_definition",
                "rows_affected": 0,
                "explanation": "The locked measurement-plan definition differs from the previous evidence version. Results are not directly comparable.",
                "row_indices": [],
            })

    # 5. excluded_failed_cases ---------------------------------------------
    if "outcome" in df.columns:
        total = len(df)
        failed_mask = df["outcome"] == "failed"
        n_failed = int(failed_mask.sum())
        n_success = int((df["outcome"] == "success").sum())
        if n_failed > 0:
            failed_pct = (n_failed / total) * 100 if total else 0.0
            severity = "critical" if failed_pct > 10 else "major"
            findings.append(
                {
                    "severity": severity,
                    "check_name": "excluded_failed_cases",
                    "rows_affected": n_failed,
                    "explanation": (
                        f"Dataset contains {n_failed} failed-outcome rows out of {total} total "
                        f"({failed_pct:.1f} %).  Success rows: {n_success}.  "
                        "KPIs computed only on 'success' rows may be cherry-picked."
                    ),
                    "row_indices": df[failed_mask].index.tolist(),
                }
            )

    min_total = max(1, int(plan.get("min_total_observations", 100)))
    if len(df) < min_total:
        findings.append({
            "severity": "major",
            "check_name": "sample_size_adequacy",
            "rows_affected": len(df),
            "explanation": f"The evidence set has {len(df)} attempted rows; the locked minimum is {min_total}.",
            "row_indices": df.index.tolist(),
        })

    # 6. sample_size_adequacy ----------------------------------------------
    if "language" in df.columns:
        default_segment_min = max(1, int(plan.get("min_segment_samples", 30)))
        marathi_min = max(1, int(plan.get("min_marathi_samples", 30)))
        for lang, group in df.groupby("language"):
            segment_min = marathi_min if str(lang).strip().casefold() == 'marathi' else default_segment_min
            if len(group) < segment_min:
                findings.append(
                    {
                        "severity": "major",
                        "check_name": "sample_size_adequacy",
                        "rows_affected": len(group),
                        "explanation": (
                            f"Language segment '{lang}' has only {len(group)} rows, "
                            f"below the minimum of {segment_min} required for statistical validity."
                        ),
                        "row_indices": group.index.tolist(),
                    }
                )

    # 7. outliers ----------------------------------------------------------
    if "processing_time_after" in df.columns:
        numeric_after = pd.to_numeric(df["processing_time_after"], errors="coerce")
        col = numeric_after.dropna()
        invalid_denominators = numeric_after.isna() | (numeric_after <= 0)
        if invalid_denominators.any():
            findings.append({"severity": "critical", "check_name": "unsupported_denominators",
                "rows_affected": int(invalid_denominators.sum()),
                "explanation": "Processing-time denominator values are missing, non-numeric, or non-positive.",
                "row_indices": df[invalid_denominators].index.tolist()})
        if len(col) >= 3 and (col.max() > (col.mean() + 3 * col.std()) or (len(col) < 30 and col.max() > col.quantile(0.75) * 1.25)):
            mean_val = col.mean()
            std_val = col.std()
            threshold_val = mean_val + 3 * std_val
            outlier_mask = numeric_after > threshold_val
            if len(col) < 30:
                outlier_mask |= numeric_after > col.quantile(0.75) * 1.25
            outlier_indices = df[outlier_mask].index.tolist()
            if outlier_indices:
                findings.append(
                    {
                        "severity": "minor",
                        "check_name": "outliers",
                        "rows_affected": len(outlier_indices),
                        "explanation": (
                            f"{len(outlier_indices)} rows in processing_time_after exceed "
                            f"mean + 3σ (threshold {threshold_val:.2f} min, "
                            f"mean={mean_val:.2f}, σ={std_val:.2f}).  "
                            "These may skew aggregate statistics."
                        ),
                        "row_indices": outlier_indices,
                    }
                )

    return findings


# ---------------------------------------------------------------------------
# KPI recomputation
# ---------------------------------------------------------------------------

_KPI_PYTHON_CODE: dict[str, str] = {
    "reduction_pct": (
        "# Include every attempted case, including failures\n"
        "baseline_median = df['processing_time_before'].median()\n"
        "after_median = df['processing_time_after'].median()\n"
        "recomputed = ((baseline_median - after_median) / baseline_median) * 100"
    ),
    "error_rate_pct": (
        "recomputed = (df['error_flag'].sum() / len(df)) * 100"
    ),
    "marathi_accuracy_pct": (
        "marathi_df = df[df['language'] == 'Marathi']\n"
        "n_success = marathi_df[marathi_df['outcome'] == 'success'].shape[0]\n"
        "recomputed = (n_success / len(marathi_df)) * 100"
    ),
    "low_bandwidth_pct": (
        "lb_df = df[df['low_bandwidth'] == True]\n"
        "n_success = lb_df[lb_df['outcome'] == 'success'].shape[0]\n"
        "recomputed = (n_success / len(lb_df)) * 100"
    ),
}


def recalculate_kpis(df: pd.DataFrame, claimed: dict, measurement_plan: dict | None = None) -> list[dict]:
    """Recompute all four KPIs from *df* and compare against *claimed* values.

    *claimed* keys: reduction_pct, error_rate_pct, marathi_accuracy_pct,
    low_bandwidth_pct.  Any value may be None if the startup did not make a claim.

    Returns a list of KPI result dicts suitable for storage in KPIResult2.
    """
    results: list[dict] = []
    plan = {**MEASUREMENT_PLAN, **(measurement_plan or {})}

    def valid_sample(columns: tuple[str, ...], minimum: int = 1) -> tuple[bool, str]:
        missing = [column for column in columns if column not in df.columns]
        if missing:
            return False, f"Required evidence columns are missing: {', '.join(missing)}."
        if len(df) < minimum:
            return False, f"Only {len(df)} attempted rows; the locked minimum is {minimum}."
        return True, ""

    # ── 1. Median processing-time reduction ──────────────────────────────
    target_pct = plan["target_reduction_pct"]
    min_total = max(1, int(plan.get("min_total_observations", 100)))
    calculation_minimum = 1 if measurement_plan is None else min_total
    ok_reduction, reason_reduction = valid_sample(("processing_time_before", "processing_time_after"), calculation_minimum)
    baseline_values = pd.to_numeric(df.get("processing_time_before", pd.Series(dtype=float)), errors="coerce")
    after_values = pd.to_numeric(df.get("processing_time_after", pd.Series(dtype=float)), errors="coerce")
    ok_reduction = ok_reduction and bool(baseline_values.notna().all() and after_values.notna().all()) and bool((baseline_values > 0).all())
    if not ok_reduction and not reason_reduction:
        reason_reduction = "Processing-time values must be numeric and baseline values must be positive."
    baseline_median = float(baseline_values.median()) if len(baseline_values) and baseline_values.notna().all() else 0.0
    after_median = float(after_values.median()) if len(after_values) and after_values.notna().all() else 0.0
    if baseline_median > 0 and ok_reduction:
        recomputed_reduction = ((baseline_median - after_median) / baseline_median) * 100.0
    else:
        recomputed_reduction = None
    n_rows_reduction = len(df)
    claimed_reduction = claimed.get("reduction_pct")
    delta_reduction = (
        round(recomputed_reduction - claimed_reduction, 4)
        if claimed_reduction is not None and recomputed_reduction is not None
        else None
    )
    outcome_reduction = ("passed" if recomputed_reduction >= target_pct else "failed") if recomputed_reduction is not None else "missing_evidence"
    reduction_display = recomputed_reduction if recomputed_reduction is not None else 0.0
    explanation_reduction = (
        f"Recomputed median reduction is {recomputed_reduction:.2f} % "
        f"(baseline median={baseline_median:.2f} min, after median={after_median:.2f} min, "
        f"using all {n_rows_reduction} attempted rows, including failed cases). Required ≥ {target_pct} %."
        if recomputed_reduction is not None else f"Reduction is missing evidence: {reason_reduction}"
    )
    if claimed_reduction is not None:
        explanation_reduction += (
            f"Startup claimed {claimed_reduction:.1f} %; delta={delta_reduction:+.2f} pp."
        )
    steps_reduction = [
        f"Step 1: Keep every attempted case (success and failed) → {n_rows_reduction} rows.",
        f"Step 2: Compute baseline_median = df['processing_time_before'].median() → {baseline_median:.4f} min.",
        f"Step 3: Compute after_median = df['processing_time_after'].median() → {after_median:.4f} min.",
        f"Step 4: reduction = ((baseline_median - after_median) / baseline_median) × 100 "
        f"= (({baseline_median:.4f} - {after_median:.4f}) / {baseline_median:.4f}) × 100 "
        f"= {reduction_display:.4f} %." if recomputed_reduction is not None else "Step 4: Calculation cannot be completed from this evidence.",
        f"Step 5: Compare {reduction_display:.4f} % vs threshold {target_pct} % → {outcome_reduction.upper()}.",
    ]
    results.append(
        {
            "kpi_key": "reduction_pct",
            "kpi_label": "Median Processing Time Reduction",
            "claimed_value": claimed_reduction,
            "recomputed_value": round(recomputed_reduction, 4) if recomputed_reduction is not None else None,
            "delta": delta_reduction,
            "outcome": outcome_reduction,
            "unit": "%",
            "threshold": target_pct,
            "explanation": explanation_reduction,
            "calculation_steps": steps_reduction,
            "rows_used": n_rows_reduction,
            "python_code": _KPI_PYTHON_CODE["reduction_pct"],
        }
    )

    # ── 2. Error rate ─────────────────────────────────────────────────────
    max_error = plan["max_error_rate_pct"]
    ok_error, reason_error = valid_sample(("error_flag",), calculation_minimum)
    error_values = pd.to_numeric(df.get("error_flag", pd.Series(dtype=float)), errors="coerce")
    ok_error = ok_error and bool(error_values.notna().all() and error_values.isin([0, 1]).all())
    if "error_flag" in df.columns:
        n_errors = int(error_values.fillna(0).sum())
        recomputed_error = (n_errors / len(df)) * 100.0 if len(df) and ok_error else None
    else:
        n_errors = 0
        recomputed_error = None
    if not ok_error and not reason_error:
        reason_error = "Error flags must be numeric 0/1 values."
    claimed_error = claimed.get("error_rate_pct")
    delta_error = (
        round(recomputed_error - claimed_error, 4) if claimed_error is not None and recomputed_error is not None else None
    )
    outcome_error = ("passed" if recomputed_error <= max_error else "failed") if recomputed_error is not None else "missing_evidence"
    error_display = recomputed_error if recomputed_error is not None else 0.0
    explanation_error = (
        f"Error rate is {recomputed_error:.2f} % ({n_errors} errors / {len(df)} rows). Required ≤ {max_error} %."
        if recomputed_error is not None else f"Error-rate KPI is missing evidence: {reason_error}"
    )
    if claimed_error is not None:
        explanation_error += f"Startup claimed {claimed_error:.1f} %; delta={delta_error:+.2f} pp."
    steps_error = [
        f"Step 1: Sum error_flag column → {n_errors} flagged rows.",
        f"Step 2: Divide by total rows {len(df)} → {n_errors}/{len(df)} = {error_display:.4f} %.",
        f"Step 3: Compare {error_display:.4f} % vs threshold ≤ {max_error} % → {outcome_error.upper()}.",
    ]
    results.append(
        {
            "kpi_key": "error_rate_pct",
            "kpi_label": "Error Rate",
            "claimed_value": claimed_error,
            "recomputed_value": round(recomputed_error, 4) if recomputed_error is not None else None,
            "delta": delta_error,
            "outcome": outcome_error,
            "unit": "%",
            "threshold": max_error,
            "explanation": explanation_error,
            "calculation_steps": steps_error,
            "rows_used": len(df),
            "python_code": _KPI_PYTHON_CODE["error_rate_pct"],
        }
    )

    # ── 3. Marathi accuracy ───────────────────────────────────────────────
    min_acc = plan["min_marathi_accuracy_pct"]
    min_samples = plan["min_marathi_samples"]
    claimed_marathi = claimed.get("marathi_accuracy_pct")
    if "language" in df.columns and "outcome" in df.columns:
        marathi_df = df[df["language"].astype(str).str.strip().str.casefold() == "marathi"]
        n_marathi = len(marathi_df)
        if n_marathi < min_samples:
            outcome_marathi = "missing_evidence"
            recomputed_marathi: float | None = None
            delta_marathi = None
            explanation_marathi = (
                f"Only {n_marathi} Marathi rows found; minimum required for a valid "
                f"accuracy measurement is {min_samples}. Cannot compute KPI."
            )
            steps_marathi = [
                f"Step 1: Filter language == 'Marathi' → {n_marathi} rows.",
                f"Step 2: {n_marathi} < {min_samples} minimum threshold → outcome=MISSING_EVIDENCE.",
            ]
            rows_used_marathi = n_marathi
        else:
            n_marathi_success = int(marathi_df[marathi_df["outcome"].astype(str).str.casefold() == "success"].shape[0])
            recomputed_marathi = (n_marathi_success / n_marathi) * 100.0
            delta_marathi = (
                round(recomputed_marathi - claimed_marathi, 4)
                if claimed_marathi is not None
                else None
            )
            outcome_marathi = "passed" if recomputed_marathi >= min_acc else "failed"
            explanation_marathi = (
                f"Marathi accuracy is {recomputed_marathi:.2f} % "
                f"({n_marathi_success} successes / {n_marathi} Marathi rows). "
                f"Required ≥ {min_acc} %.  "
            )
            if claimed_marathi is not None:
                explanation_marathi += (
                    f"Startup claimed {claimed_marathi:.1f} %; delta={delta_marathi:+.2f} pp."
                )
            steps_marathi = [
                f"Step 1: Filter language == 'Marathi' → {n_marathi} rows.",
                f"Step 2: Count outcome == 'success' within Marathi rows → {n_marathi_success}.",
                f"Step 3: accuracy = ({n_marathi_success} / {n_marathi}) × 100 = {recomputed_marathi:.4f} %.",
                f"Step 4: Compare {recomputed_marathi:.4f} % vs threshold ≥ {min_acc} % → {outcome_marathi.upper()}.",
            ]
            rows_used_marathi = n_marathi
    else:
        outcome_marathi = "missing_evidence"
        recomputed_marathi = None
        delta_marathi = None
        explanation_marathi = "Required columns 'language' and/or 'outcome' not present."
        steps_marathi = ["Step 1: Columns 'language'/'outcome' missing → outcome=MISSING_EVIDENCE."]
        rows_used_marathi = 0

    results.append(
        {
            "kpi_key": "marathi_accuracy_pct",
            "kpi_label": "Marathi Accuracy",
            "claimed_value": claimed_marathi,
            "recomputed_value": round(recomputed_marathi, 4) if recomputed_marathi is not None else None,
            "delta": delta_marathi,
            "outcome": outcome_marathi,
            "unit": "%",
            "threshold": min_acc,
            "explanation": explanation_marathi,
            "calculation_steps": steps_marathi,
            "rows_used": rows_used_marathi,
            "python_code": _KPI_PYTHON_CODE["marathi_accuracy_pct"],
        }
    )

    # ── 4. Low-bandwidth performance ──────────────────────────────────────
    lb_threshold = plan["min_low_bandwidth_success_pct"]
    claimed_lb = claimed.get("low_bandwidth_pct")
    if "low_bandwidth" in df.columns and "outcome" in df.columns:
        low_values = df["low_bandwidth"].map(lambda value: value if isinstance(value, bool) else str(value).strip().casefold() in {"true", "1", "yes", "y"})
        lb_df = df[low_values]
        n_lb = len(lb_df)
        lb_minimum = max(1, int(plan.get("min_low_bandwidth_samples", 1)))
        if n_lb < lb_minimum:
            outcome_lb = "missing_evidence"
            recomputed_lb: float | None = None
            delta_lb = None
            explanation_lb = f"Only {n_lb} low-bandwidth rows found; the locked minimum is {lb_minimum}. Cannot compute KPI."
            steps_lb = [
                f"Step 1: Filter low_bandwidth == True → {n_lb} rows.",
                f"Step 2: {n_lb} low-bandwidth observations are below minimum {lb_minimum} → outcome=MISSING_EVIDENCE.",
            ]
            rows_used_lb = n_lb
        else:
            n_lb_success = int(lb_df[lb_df["outcome"].astype(str).str.casefold() == "success"].shape[0])
            recomputed_lb = (n_lb_success / n_lb) * 100.0
            delta_lb = (
                round(recomputed_lb - claimed_lb, 4) if claimed_lb is not None else None
            )
            outcome_lb = "passed" if recomputed_lb >= lb_threshold else "failed"
            explanation_lb = (
                f"Low-bandwidth success rate is {recomputed_lb:.2f} % "
                f"({n_lb_success} successes / {n_lb} low-bandwidth rows). "
                f"Required ≥ {lb_threshold} %.  "
            )
            if claimed_lb is not None:
                explanation_lb += (
                    f"Startup claimed {claimed_lb:.1f} %; delta={delta_lb:+.2f} pp."
                )
            steps_lb = [
                f"Step 1: Filter low_bandwidth == True → {n_lb} rows.",
                f"Step 2: Count outcome == 'success' within low-bandwidth rows → {n_lb_success}.",
                f"Step 3: rate = ({n_lb_success} / {n_lb}) × 100 = {recomputed_lb:.4f} %.",
                f"Step 4: Compare {recomputed_lb:.4f} % vs threshold ≥ {lb_threshold} % → {outcome_lb.upper()}.",
            ]
            rows_used_lb = n_lb
    else:
        outcome_lb = "missing_evidence"
        recomputed_lb = None
        delta_lb = None
        explanation_lb = "Required columns 'low_bandwidth'/'outcome' not present."
        steps_lb = ["Step 1: Columns 'low_bandwidth'/'outcome' missing → outcome=MISSING_EVIDENCE."]
        rows_used_lb = 0

    results.append(
        {
            "kpi_key": "low_bandwidth_pct",
            "kpi_label": "Low-Bandwidth Performance",
            "claimed_value": claimed_lb,
            "recomputed_value": round(recomputed_lb, 4) if recomputed_lb is not None else None,
            "delta": delta_lb,
            "outcome": outcome_lb,
            "unit": "%",
            "threshold": lb_threshold,
            "explanation": explanation_lb,
            "calculation_steps": steps_lb,
            "rows_used": rows_used_lb,
            "python_code": _KPI_PYTHON_CODE["low_bandwidth_pct"],
        }
    )

    return results


# ---------------------------------------------------------------------------
# Synthetic demo datasets
# ---------------------------------------------------------------------------


def _make_row(
    case_id: str,
    language: str,
    pt_before: float,
    pt_after: float,
    error_flag: int,
    low_bandwidth: bool,
    outcome: str,
    period: int,
) -> dict:
    return {
        "case_id": case_id,
        "language": language,
        "processing_time_before": round(pt_before, 2),
        "processing_time_after": round(pt_after, 2),
        "error_flag": error_flag,
        "low_bandwidth": low_bandwidth,
        "outcome": outcome,
        "period": period,
    }


def generate_demo_datasets() -> dict[str, str]:
    """Generate three synthetic CSV datasets as strings.

    Returns
    -------
    dict with keys 'clean_pass', 'hero_problematic', 'corrected_resubmission',
    each mapping to a CSV string.
    """

    # ── Dataset 1: clean_pass ─────────────────────────────────────────────
    # 150 rows, 6 periods, ~44 % reduction, Marathi = 45 rows, error = 2 %
    rows_clean: list[dict] = []
    rng_clean = random.Random(42)
    languages = ["Marathi"] * 45 + ["Hindi"] * 55 + ["English"] * 50
    rng_clean.shuffle(languages)
    for i, lang in enumerate(languages):
        period = (i % 6) + 1
        pt_before = rng_clean.gauss(45.0, 4.0)
        pt_before = max(pt_before, 5.0)
        # Target ~44 % reduction ⟹ after ~ 25.2 min
        pt_after = rng_clean.gauss(25.2, 3.0)
        pt_after = max(pt_after, 1.0)
        error_flag = 1 if i < 3 else 0
        low_bandwidth = rng_clean.random() < 0.30
        rows_clean.append(
            _make_row(
                f"CASE-{i+1:04d}", lang, pt_before, pt_after,
                error_flag, low_bandwidth, "success", period,
            )
        )
    df_clean = pd.DataFrame(rows_clean)

    # ── Dataset 2: hero_problematic ───────────────────────────────────────
    # Deliberately flawed to trigger multiple quality findings.
    # Startup claims: 40 % reduction, 2 % error, 92 % Marathi, 95 % LB.
    # Reality: failed cases have slower times, only 10 Marathi rows, missing
    # periods and duplicate case+period combinations.
    rows_hero: list[dict] = []
    rng_hero = random.Random(43)
    lang_hero = ["Marathi"] * 10 + ["Hindi"] * 70 + ["English"] * 70
    rng_hero.shuffle(lang_hero)
    for i, lang in enumerate(lang_hero):
        # Deliberately omit period 4.
        period = (i % 5) + 1
        if period >= 4:
            period += 1
        pt_before = rng_hero.gauss(45.0, 4.0)
        pt_before = max(pt_before, 5.0)
        # A selectively reported success subset can imply ~40%; including
        # failed attempted cases moves the median toward baseline.
        pt_after = rng_hero.gauss(31.0 if i >= 25 else 66.0, 3.0)
        pt_after = max(pt_after, 1.0)
        # 25 rows are failed
        if i < 25:
            outcome = "failed"
            error_flag = 1
        else:
            error_flag = 1 if rng_hero.random() < 0.02 else 0
            outcome = "success"
        low_bandwidth = rng_hero.random() < 0.30
        rows_hero.append(
            _make_row(
                f"CASE-{i+1:04d}", lang, pt_before, pt_after,
                error_flag, low_bandwidth, outcome, period,
            )
        )
    # Inject 3 duplicate (case_id, period) pairs
    for dup_i in range(3):
        original = rows_hero[dup_i * 10].copy()
        rows_hero.append(original)  # exact duplicate row
    df_hero = pd.DataFrame(rows_hero)

    # ── Dataset 3: corrected_resubmission ────────────────────────────────
    # Fixed version: 35 Marathi, failed cases included, ~38 % reduction,
    # no duplicates, no missing periods, error = 3 %, Marathi acc = 87 %.
    rows_corr: list[dict] = []
    rng_corr = random.Random(44)
    lang_corr = ["Marathi"] * 35 + ["Hindi"] * 60 + ["English"] * 55
    rng_corr.shuffle(lang_corr)
    marathi_success_budget = 31
    marathi_seen = 0
    for i, lang in enumerate(lang_corr):
        period = (i % 6) + 1
        pt_before = rng_corr.gauss(45.0, 4.0)
        pt_before = max(pt_before, 5.0)
        # ~38 % reduction ⟹ after ≈ 27.9 min
        pt_after = rng_corr.gauss(27.9, 3.0)
        pt_after = max(pt_after, 1.0)
        error_flag = 1 if i < 5 else 0
        low_bandwidth = (i % 4) == 0
        # Marathi accuracy = 31/35 (88.6%) with adequate sample size.
        if lang == "Marathi":
            outcome = "success" if marathi_seen < marathi_success_budget else "failed"
            marathi_seen += 1
        else:
            outcome = "success"
        rows_corr.append(
            _make_row(
                f"CASE-{i+1:04d}", lang, pt_before, pt_after,
                error_flag, low_bandwidth, outcome, period,
            )
        )
    for idx, row in enumerate(rows_corr):
        row["error_flag"] = 1 if idx < 4 else 0
        row["low_bandwidth"] = (idx % 4) == 0
        row["period"] = (idx % 6) + 1
    for idx, row in enumerate(rows_corr):
        row["error_flag"] = 1 if idx < 4 else 0
        row["low_bandwidth"] = (idx % 4) == 0
        row["period"] = (idx % 6) + 1
    df_corr = pd.DataFrame(rows_corr)

    return {
        "clean_pass": df_clean.to_csv(index=False),
        "hero_problematic": df_hero.to_csv(index=False),
        "corrected_resubmission": df_corr.to_csv(index=False),
    }


def get_claimed_values_for_demo(dataset_name: str) -> dict:
    """Return the startup's claimed KPI values for a given demo dataset.

    For 'hero_problematic', the startup inflates its claims.
    All other datasets have no pre-populated claimed values.
    """
    if dataset_name == "hero_problematic":
        return {
            "reduction_pct": 40.0,
            "error_rate_pct": 2.0,
            "marathi_accuracy_pct": 92.0,
            "low_bandwidth_pct": 95.0,
        }
    return {
        "reduction_pct": None,
        "error_rate_pct": None,
        "marathi_accuracy_pct": None,
        "low_bandwidth_pct": None,
    }
