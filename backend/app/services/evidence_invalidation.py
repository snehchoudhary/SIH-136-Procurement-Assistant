"""Shared measurement-plan fingerprinting and current-result invalidation."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence_verification import EvidenceVersion2, KPIResult2
from app.models.pilot import AgreementVersion
from app.services.evidence_engine import CALCULATOR_VERSION, MEASUREMENT_PLAN


def measurement_plan_for_version(version: AgreementVersion | None) -> dict:
    plan = dict(MEASUREMENT_PLAN)
    plan['max_error_rate_pct'] = plan['max_error_rate_pct']
    if version is not None:
        plan.update({
            "baseline_minutes": version.baseline_minutes,
            "target_reduction_pct": version.target_pct,
            "max_error_rate_pct": version.error_limit_pct,
            "min_marathi_accuracy_pct": version.marathi_accuracy_pct,
            "min_marathi_samples": version.min_marathi_observations,
            "min_total_observations": version.min_observations,
            "max_bandwidth_mbps": version.bandwidth_mbps,
            "capacity_per_day": version.capacity_per_day,
        })
    # These inputs are stored on the agreement model; retain the locked engine
    # defaults for plan dimensions not represented in that schema.
    return plan


def comparable_measurement_plan(plan: dict) -> dict:
    """Select only values represented in the approved agreement schema."""
    aliases = {
        'baseline_minutes': 'baseline_minutes', 'target_reduction_pct': 'target_reduction_pct',
        'max_error_rate_pct': 'max_error_rate_pct', 'min_marathi_accuracy_pct': 'min_marathi_accuracy_pct',
        'min_marathi_samples': 'min_marathi_samples', 'max_bandwidth_mbps': 'max_bandwidth_mbps',
        'min_total_observations': 'min_total_observations', 'min_low_bandwidth_success_pct': 'min_low_bandwidth_success_pct',
        'min_segment_samples': 'min_segment_samples', 'capacity_per_day': 'capacity_per_day',
    }
    return {key: plan[key] for key in aliases if key in plan}


def measurement_plan_fingerprint(plan: dict) -> str:
    # Keep the engine's reproducibility contract inside the versioned snapshot.
    payload = {"calculator_version": CALCULATOR_VERSION, "measurement_plan": comparable_measurement_plan(plan)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def invalidate_current_evidence(db: Session, agreement_id: str, *, reason: str) -> int:
    """Mark current evidence/results stale after a locked input changes.

    Returns the number of evidence versions invalidated. The audit log is
    append-only; callers record this action separately after committing.
    """
    latest_approved = db.scalar(
        select(AgreementVersion)
        .where(AgreementVersion.agreement_id == agreement_id, AgreementVersion.approved.is_(True))
        .order_by(AgreementVersion.version.desc())
    )
    new_plan = measurement_plan_for_version(latest_approved)
    new_fingerprint = measurement_plan_fingerprint(new_plan)
    current_versions = list(db.scalars(
        select(EvidenceVersion2).where(
            EvidenceVersion2.agreement_id == agreement_id,
            EvidenceVersion2.is_current.is_(True),
        )
    ))
    invalidated = 0
    for version in current_versions:
        if version.created_at is None:
            db.flush()
        snapshot = dict(version.measurement_plan_snapshot or {})
        snapshot.pop('calculator_version', None)
        if snapshot and comparable_measurement_plan(snapshot) != comparable_measurement_plan(new_plan):
            version.is_current = False
            for result in db.scalars(select(KPIResult2).where(KPIResult2.upload_id == version.upload_id)):
                result.is_stale = True
            invalidated += 1
    return invalidated
