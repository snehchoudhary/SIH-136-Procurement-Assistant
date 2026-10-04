"""FastAPI router for the evidence verification v2 engine.

Prefix: (none – full paths specified per endpoint)
"""

import io
from pathlib import Path
from typing import Optional
import json

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit_helper import write_audit_event
from app.core.permissions import require
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.evidence_verification import (
    EvidenceUpload,
    EvidenceVersion2,
    KPIResult2,
    QualityFinding,
    ValidatorDecision,
    EvidenceReviewThread,
)
from app.models.pilot import Milestone, AgreementVersion, PilotAgreement
from app.models.startup import Startup
from app.services.evidence_engine import (
    compute_sha256,
    generate_demo_datasets,
    get_claimed_values_for_demo,
    recalculate_kpis,
    run_quality_checks,
    MEASUREMENT_PLAN,
    CALCULATOR_VERSION,
)
from app.services.evidence_invalidation import measurement_plan_for_version, measurement_plan_fingerprint, comparable_measurement_plan

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Resolve upload directory relative to this file's location
_BACKEND_ROOT = Path(__file__).resolve().parents[3]  # …/backend
_UPLOAD_DIR = _BACKEND_ROOT / "uploads" / "evidence"
_MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
_MAX_EVIDENCE_ROWS = 100_000


def _ensure_upload_dir() -> Path:
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return _UPLOAD_DIR


def _load_upload_for_user(db: Session, upload_id: str, current_user: OIDCUserInfo) -> EvidenceUpload:
    ev = db.get(EvidenceUpload, upload_id)
    if ev is None:
        raise HTTPException(404, detail="Upload not found.")
    if current_user.role == 'startup':
        agreement = db.get(PilotAgreement, ev.pilot_agreement_id)
        startup = db.get(Startup, agreement.startup_id) if agreement else None
        if not current_user.org_id or not startup or str(startup.organisation_id) != current_user.org_id:
            raise HTTPException(403, detail="Startup users may only access evidence for their own organization.")
    return ev


def _build_analysis_response(
    upload_id: str | None,
    sha256_hash: str,
    version_number: int,
    row_count: int,
    previous_version_marked_stale: bool,
    findings: list[dict],
    kpi_results: list[dict],
    finding_ids: list[str] | None = None,
    kpi_ids: list[str] | None = None,
    rows: list[dict] | None = None,
    milestone_status: str = "Pending",
    is_demo: bool = False,
) -> dict:
    """Assemble the canonical analysis response dict."""
    # Derive overall outcome
    outcomes = [k["outcome"] for k in kpi_results]
    n_failed = outcomes.count("failed")
    n_missing = outcomes.count("missing_evidence")
    if n_missing > 0:
        overall = "missing_evidence"
    elif n_failed > 0:
        overall = "failed"
    else:
        overall = "passed"

    parts: list[str] = []
    if n_failed:
        parts.append(f"{n_failed} KPI{'s' if n_failed > 1 else ''} failed")
    if n_missing:
        parts.append(f"{n_missing} missing evidence")
    if not parts:
        parts.append("all KPIs passed")
    if n_missing and not n_failed:
        parts.insert(0, "missing evidence")
    outcome_summary = ", ".join(parts)

    resp_findings = []
    for idx, f in enumerate(findings):
        fd = {
            "id": finding_ids[idx] if finding_ids else f.get("id", ""),
            "severity": f["severity"],
            "check_name": f["check_name"],
            "rows_affected": f["rows_affected"],
            "explanation": f["explanation"],
            "row_indices": f["row_indices"],
        }
        resp_findings.append(fd)

    resp_kpis = []
    for idx, k in enumerate(kpi_results):
        kd = {
            "id": kpi_ids[idx] if kpi_ids else k.get("id", ""),
            "kpi_key": k["kpi_key"],
            "kpi_label": k["kpi_label"],
            "claimed_value": k["claimed_value"],
            "recomputed_value": k["recomputed_value"],
            "delta": k["delta"],
            "outcome": k["outcome"],
            "unit": k["unit"],
            "threshold": k["threshold"],
            "explanation": k["explanation"],
            "calculation_steps": k["calculation_steps"],
            "rows_used": k["rows_used"],
            "python_code": k["python_code"],
        }
        resp_kpis.append(kd)

    return {
        "upload_id": upload_id,
        "sha256_hash": sha256_hash,
        "version_number": version_number,
        "row_count": row_count,
        "previous_version_marked_stale": previous_version_marked_stale,
        "findings": resp_findings,
        "kpi_results": resp_kpis,
        "overall_outcome": overall,
        "outcome_summary": outcome_summary,
        "rows": rows,
        "milestone_status": milestone_status,
        "is_demo": is_demo,
    }


# ---------------------------------------------------------------------------
# POST /api/v2/evidence/upload
# ---------------------------------------------------------------------------


@router.post("/api/v2/evidence/upload", tags=["Evidence V2"])
async def upload_evidence(
    file: UploadFile = File(...),
    agreement_id: Optional[str] = Form(None),
    pilot_agreement_id: Optional[str] = Form(None),
    claimed_values: Optional[str] = Form(None),
    claimed_reduction_pct: Optional[float] = Form(None),
    claimed_error_rate_pct: Optional[float] = Form(None),
    claimed_marathi_accuracy_pct: Optional[float] = Form(None),
    claimed_low_bandwidth_pct: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.submit")),
):
    """Upload a CSV evidence file, run quality checks and KPI recomputation."""
    from uuid import uuid4

    pilot_agreement_id = agreement_id or pilot_agreement_id
    if not pilot_agreement_id:
        raise HTTPException(400, detail="agreement_id is required.")
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(400, detail="Upload a CSV evidence file.")
    agreement = db.get(PilotAgreement, pilot_agreement_id)
    if agreement is None:
        raise HTTPException(404, detail="Pilot agreement not found.")
    if current_user.role == 'startup':
        startup = db.get(Startup, agreement.startup_id)
        if not current_user.org_id or not startup or str(startup.organisation_id) != current_user.org_id:
            raise HTTPException(403, detail="Startup users may only upload evidence for their own organization.")

    # ── Read file ──────────────────────────────────────────────────────────
    raw_bytes = await file.read(_MAX_EVIDENCE_BYTES + 1)
    if len(raw_bytes) > _MAX_EVIDENCE_BYTES:
        raise HTTPException(413, detail="Evidence CSV files must be 10 MiB or smaller.")
    file_obj = io.BytesIO(raw_bytes)
    sha256_hash = compute_sha256(file_obj)
    file_size = len(raw_bytes)

    # Parse CSV
    try:
        file_obj.seek(0)
        df = pd.read_csv(file_obj)
    except Exception as exc:
        raise HTTPException(400, detail=f"Could not parse CSV: {exc}") from exc

    row_count = len(df)
    if row_count == 0:
        raise HTTPException(400, detail="CSV contains no data rows.")
    if row_count > _MAX_EVIDENCE_ROWS:
        raise HTTPException(413, detail="Evidence CSV files may contain no more than 100,000 data rows.")

    # ── Save to disk ───────────────────────────────────────────────────────
    upload_id = str(uuid4())
    safe_name = Path((file.filename or "upload.csv").replace('\\', '/')).name.replace('\x00', '')[:180]
    dest_path = _ensure_upload_dir() / f"{upload_id}_{safe_name}"
    dest_path.write_bytes(raw_bytes)

    # ── Create EvidenceUpload record (status = processing) ─────────────────
    ev_upload = EvidenceUpload(
        id=upload_id,
        pilot_agreement_id=pilot_agreement_id,
        submitted_by=current_user.sub,
        original_filename=file.filename or safe_name,
        sha256_hash=sha256_hash,
        file_path=str(dest_path),
        row_count=row_count,
        file_size_bytes=file_size,
        upload_status="processing",
    )
    db.add(ev_upload)
    for milestone in db.query(Milestone).filter(Milestone.agreement_id == pilot_agreement_id).all():
        milestone.lifecycle_state = "Evidence Submitted"
        if milestone.status not in {"Accepted", "Paid"}:
            milestone.status = "Pending"
    db.flush()

    # ── Load previous version CSV for schema-change detection ─────────────
    prev_df: pd.DataFrame | None = None
    prev_version = (
        db.query(EvidenceVersion2)
        .filter(
            EvidenceVersion2.agreement_id == pilot_agreement_id,
            EvidenceVersion2.is_current == True,  # noqa: E712
        )
        .order_by(EvidenceVersion2.version_number.desc())
        .first()
    )
    previous_version_marked_stale = False
    if prev_version is not None:
        prev_upload = db.get(EvidenceUpload, prev_version.upload_id)
        if prev_upload and Path(prev_upload.file_path).exists():
            try:
                prev_df = pd.read_csv(prev_upload.file_path)
            except Exception:
                prev_df = None
        # Mark previous version stale
        prev_version.is_current = False
        db.query(KPIResult2).filter(KPIResult2.upload_id == prev_version.upload_id).update({KPIResult2.is_stale: True})
        db.flush()
        previous_version_marked_stale = True

    next_version_number = (prev_version.version_number + 1) if prev_version else 1

    # ── Quality checks ────────────────────────────────────────────────────
    agreement_version = (db.query(AgreementVersion).filter(AgreementVersion.agreement_id == pilot_agreement_id, AgreementVersion.approved == True).order_by(AgreementVersion.version.desc()).first())  # noqa: E712
    plan = measurement_plan_for_version(agreement_version)
    metric_definition_hash = measurement_plan_fingerprint(plan)
    findings = run_quality_checks(df, prev_df,
        prev_version.metric_definition_hash if prev_version else None,
        metric_definition_hash, plan)
    finding_records: list[QualityFinding] = []
    for f in findings:
        rec = QualityFinding(
            upload_id=upload_id,
            severity=f["severity"],
            check_name=f["check_name"],
            rows_affected=f["rows_affected"],
            explanation=f["explanation"],
            row_indices=f["row_indices"],
        )
        db.add(rec)
        finding_records.append(rec)
    db.flush()

    # ── KPI recomputation ─────────────────────────────────────────────────
    try:
        claims = json.loads(claimed_values) if claimed_values else {}
        if not isinstance(claims, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(400, detail="claimed_values must be a JSON object.")
    claimed = {
        "reduction_pct": claims.get("reduction_pct", claimed_reduction_pct),
        "error_rate_pct": claims.get("error_rate_pct", claimed_error_rate_pct),
        "marathi_accuracy_pct": claims.get("marathi_accuracy_pct", claimed_marathi_accuracy_pct),
        "low_bandwidth_pct": claims.get("low_bandwidth_pct", claimed_low_bandwidth_pct),
    }
    kpi_results = recalculate_kpis(df, claimed, plan)
    kpi_records: list[KPIResult2] = []
    for k in kpi_results:
        rec = KPIResult2(
            upload_id=upload_id,
            kpi_key=k["kpi_key"],
            kpi_label=k["kpi_label"],
            claimed_value=k["claimed_value"],
            recomputed_value=k["recomputed_value"],
            delta=k["delta"],
            outcome=k["outcome"],
            unit=k["unit"],
            threshold=k["threshold"],
            explanation=k["explanation"],
            calculation_steps=k["calculation_steps"],
            rows_used=k["rows_used"],
            python_code=k["python_code"],
        )
        db.add(rec)
        kpi_records.append(rec)
    db.flush()

    # ── EvidenceVersion2 snapshot ─────────────────────────────────────────
    version_rec = EvidenceVersion2(
        upload_id=upload_id,
        agreement_id=pilot_agreement_id,
        version_number=next_version_number,
        sha256_hash=sha256_hash,
        is_current=True,
        metric_definition_hash=metric_definition_hash,
        measurement_plan_snapshot={**comparable_measurement_plan(plan), "calculator_version": CALCULATOR_VERSION},
    )
    db.add(version_rec)

    # ── Mark upload ready ─────────────────────────────────────────────────
    ev_upload.upload_status = "ready"
    db.commit()
    db.refresh(ev_upload)

    # ── Audit ─────────────────────────────────────────────────────────────
    write_audit_event(
        db,
        current_user.sub,
        current_user.role,
        "evidence.uploaded",
        "EvidenceUpload",
        upload_id,
        f"Evidence '{safe_name}' uploaded for agreement {pilot_agreement_id}; "
        f"v{next_version_number}, sha256={sha256_hash[:12]}…",
    )

    flagged_rows = {idx: [] for idx in range(len(df))}
    for index, finding in enumerate(findings):
        for idx in finding["row_indices"]:
            flagged_rows[idx].append(finding_records[index].id)
    response = _build_analysis_response(
        upload_id=upload_id,
        sha256_hash=sha256_hash,
        version_number=next_version_number,
        row_count=row_count,
        previous_version_marked_stale=previous_version_marked_stale,
        findings=findings,
        kpi_results=kpi_results,
        finding_ids=[r.id for r in finding_records],
        kpi_ids=[r.id for r in kpi_records],
        rows=[{**row.to_dict(), "_row_index": int(idx), "_flagged": bool(flagged_rows[idx]), "_finding_ids": flagged_rows[idx]}
              for idx, row in df.where(pd.notna(df), None).iterrows()],
        milestone_status="Pending",
    )
    return response


# ---------------------------------------------------------------------------
# GET /api/v2/evidence/{upload_id}
# ---------------------------------------------------------------------------


@router.get("/api/v2/evidence/{upload_id}", tags=["Evidence V2"])
def get_evidence(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.view")),
):
    """Return upload metadata, findings, and KPI results for an upload."""
    ev = _load_upload_for_user(db, upload_id, current_user)

    findings = (
        db.query(QualityFinding)
        .filter(QualityFinding.upload_id == upload_id)
        .all()
    )
    kpis = (
        db.query(KPIResult2)
        .filter(KPIResult2.upload_id == upload_id)
        .all()
    )
    version = (
        db.query(EvidenceVersion2)
        .filter(EvidenceVersion2.upload_id == upload_id)
        .first()
    )
    last_decision = (db.query(ValidatorDecision).filter(ValidatorDecision.upload_id == upload_id)
        .order_by(ValidatorDecision.created_at.desc()).first())
    decisions = (
        db.query(ValidatorDecision)
        .filter(ValidatorDecision.upload_id == upload_id)
        .all()
    )

    return {
        "upload_id": ev.id,
        "pilot_agreement_id": ev.pilot_agreement_id,
        "submitted_by": ev.submitted_by,
        "original_filename": ev.original_filename,
        "sha256_hash": ev.sha256_hash,
        "row_count": ev.row_count,
        "version_number": version.version_number if version else None,
        "previous_version_marked_stale": bool(version and version.version_number > 1),
        "file_size_bytes": ev.file_size_bytes,
        "upload_status": ev.upload_status,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
        "version": {
            "version_number": version.version_number if version else None,
            "is_current": version.is_current if version else None,
        },
        "findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "check_name": f.check_name,
                "rows_affected": f.rows_affected,
                "explanation": f.explanation,
                "row_indices": f.row_indices,
            }
            for f in findings
        ],
        "kpi_results": [
            {
                "id": k.id,
                "kpi_key": k.kpi_key,
                "kpi_label": k.kpi_label,
                "claimed_value": k.claimed_value,
                "recomputed_value": k.recomputed_value,
                "delta": k.delta,
                "outcome": k.outcome,
                "unit": k.unit,
                "threshold": k.threshold,
                "explanation": k.explanation,
                "calculation_steps": k.calculation_steps,
                "rows_used": k.rows_used,
                "python_code": k.python_code,
                "is_stale": k.is_stale,
            }
            for k in kpis
        ],
        "rows": None,
        "is_demo": False,
        "milestone_status": "Validated" if last_decision and last_decision.action == "accepted" else "Pending",
        "overall_outcome": (
            "missing_evidence" if any(k.outcome == "missing_evidence" for k in kpis)
            else "failed" if any(k.outcome == "failed" for k in kpis)
            else "passed"
        ),
        "outcome_summary": "Evidence results are provisional until validator acceptance.",
        "decisions": [
            {
                "id": d.id,
                "validator_id": d.validator_id,
                "action": d.action,
                "reason": d.reason,
                "thread_id": d.thread_id,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/v2/evidence/{upload_id}/rows
# ---------------------------------------------------------------------------


@router.get("/api/v2/evidence/{upload_id}/rows", tags=["Evidence V2"])
def get_evidence_rows(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.view")),
):
    """Return the raw CSV rows as JSON, with per-row flagging metadata."""
    ev = _load_upload_for_user(db, upload_id, current_user)

    file_path = Path(ev.file_path)
    if not file_path.exists():
        raise HTTPException(404, detail="Stored CSV file not found on disk.")

    df = pd.read_csv(file_path)

    findings = (
        db.query(QualityFinding)
        .filter(QualityFinding.upload_id == upload_id)
        .all()
    )

    # Build index → list of finding ids map
    index_to_finding_ids: dict[int, list[str]] = {}
    for f in findings:
        for idx in (f.row_indices or []):
            index_to_finding_ids.setdefault(idx, []).append(f.id)

    rows = []
    for i, row in df.iterrows():
        row_dict = row.to_dict()
        row_dict["_row_index"] = int(i)
        finding_ids = index_to_finding_ids.get(int(i), [])
        row_dict["_flagged"] = len(finding_ids) > 0
        row_dict["_finding_ids"] = finding_ids
        rows.append(row_dict)

    return {"upload_id": upload_id, "row_count": len(rows), "rows": rows}


@router.get("/api/v2/evidence/agreement/{agreement_id}/latest", tags=["Evidence V2"])
def get_latest_agreement_evidence(
    agreement_id: str,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.view")),
):
    version = (db.query(EvidenceVersion2)
        .filter(EvidenceVersion2.agreement_id == agreement_id)
        .order_by(EvidenceVersion2.version_number.desc()).first())
    if version is None:
        raise HTTPException(404, detail="No evidence has been submitted for this agreement.")
    analysis = get_evidence(version.upload_id, db, current_user)
    grid = get_evidence_rows(version.upload_id, db, current_user)
    analysis["rows"] = grid["rows"]
    for finding in analysis["findings"]:
        for row in analysis["rows"]:
            if row["_row_index"] in (finding.get("row_indices") or []):
                row["_flagged"] = True
                if finding["id"] not in row["_finding_ids"]:
                    row["_finding_ids"].append(finding["id"])
    analysis["overall_outcome"] = (
        "missing_evidence" if any(k["outcome"] == "missing_evidence" for k in analysis["kpi_results"])
        else "failed" if any(k["outcome"] == "failed" for k in analysis["kpi_results"])
        else "passed"
    )
    analysis["outcome_summary"] = f"{analysis['overall_outcome'].replace('_', ' ').title()} · milestone remains pending until validator acceptance."
    analysis["milestone_status"] = "Pending"
    analysis["is_demo"] = False
    analysis["version_number"] = version.version_number
    analysis["previous_version_marked_stale"] = version.version_number > 1
    return analysis


# ---------------------------------------------------------------------------
# POST /api/v2/evidence/{upload_id}/decision
# ---------------------------------------------------------------------------


class ValidatorDecisionRequest(BaseModel):
    action: str
    reason: Optional[str] = None


@router.post("/api/v2/evidence/{upload_id}/decision", tags=["Evidence V2"])
def make_decision(
    upload_id: str,
    request: ValidatorDecisionRequest,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.validate")),
):
    """Validator accepts, disputes, or requests correction of an evidence upload."""
    valid_actions = {"accepted", "disputed", "correction_requested"}
    action = request.action
    reason = (request.reason or "").strip()
    if action not in valid_actions:
        raise HTTPException(400, detail=f"action must be one of {sorted(valid_actions)}.")
    if action in {"disputed", "correction_requested"} and len(reason) < 20:
        raise HTTPException(400, detail="A reason of at least 20 characters is required.")

    ev = db.get(EvidenceUpload, upload_id)
    if ev is None:
        raise HTTPException(404, detail="Upload not found.")

    # Validators cannot validate their own submissions
    if str(ev.submitted_by) == str(current_user.sub):
        raise HTTPException(403, detail="Validator cannot validate their own evidence upload.")

    version = db.query(EvidenceVersion2).filter(EvidenceVersion2.upload_id == upload_id).first()
    if action == "accepted":
        kpis = db.query(KPIResult2).filter(KPIResult2.upload_id == upload_id).all()
        findings = db.query(QualityFinding).filter(QualityFinding.upload_id == upload_id, QualityFinding.severity == "critical").count()
        if not version or not version.is_current or any(k.is_stale for k in kpis):
            raise HTTPException(409, detail="This evidence version is stale and cannot be accepted.")
        if not kpis or any(k.outcome != "passed" for k in kpis) or findings:
            raise HTTPException(409, detail="Evidence cannot be accepted until every KPI passes and critical findings are resolved.")

    decision = ValidatorDecision(
        upload_id=upload_id,
        validator_id=current_user.sub,
        action=action,
        reason=reason,
        thread_id=None,
    )
    db.add(decision)
    db.flush()

    # If correction requested → update milestone lifecycle_state
    if action == "correction_requested":
        db.query(Milestone).filter(Milestone.agreement_id == ev.pilot_agreement_id).update(
            {Milestone.lifecycle_state: "Correction Requested", Milestone.status: "Pending"},
            synchronize_session="fetch",
        )
        thread = EvidenceReviewThread(
            upload_id=upload_id,
            agreement_id=ev.pilot_agreement_id,
            created_by=current_user.sub,
            subject="Evidence correction requested",
            initial_message=reason,
        )
        db.add(thread)
        db.flush()
        decision.thread_id = thread.id
    elif action == "disputed":
        db.query(Milestone).filter(Milestone.agreement_id == ev.pilot_agreement_id).update(
            {Milestone.lifecycle_state: "Disputed", Milestone.status: "Pending"}, synchronize_session="fetch")
    elif action == "accepted":
        db.query(Milestone).filter(Milestone.agreement_id == ev.pilot_agreement_id).update(
            {Milestone.lifecycle_state: "Validated"}, synchronize_session="fetch")
        db.flush()

    db.commit()
    db.refresh(decision)

    write_audit_event(
        db,
        current_user.sub,
        current_user.role,
        "evidence.decision",
        "ValidatorDecision",
        decision.id,
        f"Validator {current_user.sub} marked upload {upload_id} as '{action}'.",
    )

    return {
        "id": decision.id,
        "upload_id": decision.upload_id,
        "validator_id": decision.validator_id,
        "action": decision.action,
        "reason": decision.reason,
        "thread_id": decision.thread_id,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }


# ---------------------------------------------------------------------------
# GET /api/v2/evidence/demo/{dataset_name}
# ---------------------------------------------------------------------------


@router.get("/api/v2/evidence/demo/{dataset_name}", tags=["Evidence V2"])
def get_demo_analysis(dataset_name: str):
    """Run the engine on a synthetic dataset without persisting anything to DB.

    dataset_name: 'clean_pass' | 'hero_problematic' | 'corrected_resubmission'
    """
    valid = {"clean_pass", "hero_problematic", "corrected_resubmission"}
    if dataset_name not in valid:
        raise HTTPException(
            404,
            detail=f"Unknown dataset '{dataset_name}'. Valid options: {sorted(valid)}.",
        )

    datasets = generate_demo_datasets()
    csv_str = datasets[dataset_name]
    df = pd.read_csv(io.StringIO(csv_str))
    claimed = get_claimed_values_for_demo(dataset_name)

    sha256_hash = compute_sha256(io.BytesIO(csv_str.encode("utf-8")))
    findings = run_quality_checks(df, None)
    kpi_results = recalculate_kpis(df, claimed)
    response = _build_analysis_response(
        upload_id=f"demo:{dataset_name}",
        sha256_hash=sha256_hash,
        version_number=1,
        row_count=len(df),
        previous_version_marked_stale=False,
        findings=findings,
        kpi_results=kpi_results,
    )
    flagged = {idx: [] for idx in range(len(df))}
    for i, finding in enumerate(findings):
        for idx in finding["row_indices"]:
            flagged[idx].append(f"demo-finding-{i}")
    response["findings"] = [dict(f, id=f"demo-finding-{i}") for i, f in enumerate(findings)]
    response["rows"] = [
        {**row.to_dict(), "_row_index": int(idx), "_flagged": bool(flagged[idx]), "_finding_ids": flagged[idx]}
        for idx, row in df.where(pd.notna(df), None).iterrows()
    ]
    response["is_demo"] = True
    response["outcome_summary"] = (
        "Synthetic dataset · " + response["outcome_summary"] +
        " Missing evidence, failed performance, and passed KPIs are reported separately."
    )
    response["milestone_status"] = "Pending"
    return response


# ---------------------------------------------------------------------------
# GET /api/v2/evidence/{upload_id}/reproduce
# ---------------------------------------------------------------------------


@router.get("/api/v2/evidence/{upload_id}/reproduce", tags=["Evidence V2"])
def reproduce_kpis(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(require("evidence.view")),
):
    """Return the exact calculation steps and Python code for every KPI in an upload."""
    ev = _load_upload_for_user(db, upload_id, current_user)

    kpis = (
        db.query(KPIResult2)
        .filter(KPIResult2.upload_id == upload_id)
        .all()
    )

    results = []
    for k in kpis:
        results.append(
            {
                "kpi_key": k.kpi_key,
                "kpi_label": k.kpi_label,
                "calculation_steps": k.calculation_steps,
                "python_code": k.python_code,
                "rows_used": k.rows_used,
                "recomputed_value": k.recomputed_value,
                "outcome": k.outcome,
            }
        )

    return {
        "upload_id": upload_id,
        "sha256_hash": ev.sha256_hash,
        "source_filename": ev.original_filename,
        "kpi_reproductions": results,
    }
