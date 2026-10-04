"""Portable project passport, PDF decision package, and public integrity check."""
import hashlib
import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.evidence_verification import EvidenceUpload, EvidenceVersion2, KPIResult2, ValidatorDecision
from app.models.payment import Invoice, PaymentRecord
from app.models.pilot import AgreementVersion, Milestone, PilotAgreement
from app.models.policy import PolicySource
from app.models.challenge import Challenge, ChallengeVersion
from app.models.transfer import TransferAssessment
from app.workflow.engine import verify_audit_chain

router = APIRouter()


def _passport(db: Session, agreement_id: str) -> dict:
    agreement = db.get(PilotAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, detail='Pilot passport not found.')
    challenge = db.get(Challenge, agreement.challenge_id)
    challenge_version = db.scalar(select(ChallengeVersion).where(ChallengeVersion.challenge_id == agreement.challenge_id)
        .order_by(ChallengeVersion.version.desc()))
    plan = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id)
        .order_by(AgreementVersion.version.desc()))
    upload = db.scalar(select(EvidenceUpload).join(EvidenceVersion2, EvidenceVersion2.upload_id == EvidenceUpload.id)
        .where(EvidenceUpload.pilot_agreement_id == agreement_id, EvidenceVersion2.is_current.is_(True))
        .order_by(EvidenceVersion2.version_number.desc()))
    kpis = list(db.scalars(select(KPIResult2).where(KPIResult2.upload_id == upload.id))) if upload else []
    decision = db.scalar(select(ValidatorDecision).where(ValidatorDecision.upload_id == upload.id)
        .order_by(ValidatorDecision.created_at.desc())) if upload else None
    milestones = db.scalars(select(Milestone).where(Milestone.agreement_id == agreement_id)
        .order_by(Milestone.code)).all()
    milestone_rows = []
    for milestone in milestones:
        invoice = db.scalar(select(Invoice).where(Invoice.milestone_id == milestone.id)
            .order_by(Invoice.submitted_at.desc()))
        payment = db.scalar(select(PaymentRecord).where(PaymentRecord.invoice_id == invoice.id)
            .order_by(PaymentRecord.created_at.desc())) if invoice else None
        milestone_rows.append({'id': str(milestone.id), 'code': milestone.code, 'title': milestone.title,
            'amount': milestone.amount, 'state': milestone.lifecycle_state, 'status': milestone.status,
            'invoice': ({'id': str(invoice.id), 'amount': invoice.amount, 'status': invoice.approval_status,
                'reference': invoice.reference, 'sha256': invoice.content_sha256} if invoice else None),
            'payment': ({'id': str(payment.id), 'status': payment.status, 'reference': payment.reference,
                'simulated': payment.simulated} if payment else None)})
    upload_hash_valid = None
    if upload:
        try: upload_hash_valid = hashlib.sha256(Path(upload.file_path).read_bytes()).hexdigest() == upload.sha256_hash
        except OSError: upload_hash_valid = False
    chain = verify_audit_chain(db, agreement_id)
    assessment = db.scalar(select(TransferAssessment).where(TransferAssessment.agreement_id == agreement_id)
        .order_by(TransferAssessment.assessed_at.desc()))
    policies = db.scalars(select(PolicySource).order_by(PolicySource.effective_date.desc()).limit(5)).all()
    return {
        'id': agreement_id, 'record_type': 'Pilot Evidence Passport',
        'disclaimer': 'Structured project record. Not a government certification.',
        'problem_and_kpis': {'challenge_id': challenge.id if challenge else agreement.challenge_id,
            'title': challenge.title if challenge else agreement.challenge_id,
            'problem': challenge_version.problem_statement if challenge_version else None,
            'measurement_plan': ({'version': plan.version, 'baseline_minutes': plan.baseline_minutes,
                'target_pct': plan.target_pct, 'error_limit_pct': plan.error_limit_pct,
                'marathi_accuracy_pct': plan.marathi_accuracy_pct, 'min_observations': plan.min_observations,
                'min_marathi_observations': plan.min_marathi_observations, 'bandwidth_mbps': plan.bandwidth_mbps,
                'capacity_per_day': plan.capacity_per_day, 'clauses': plan.clauses} if plan else None),
            'results': [{'kpi': k.kpi_label, 'claimed': k.claimed_value, 'recomputed': k.recomputed_value,
                'delta': k.delta, 'outcome': k.outcome, 'explanation': k.explanation} for k in kpis]},
        'eligibility': {'startup_id': str(agreement.startup_id), 'agreement_status': agreement.status,
            'terms_accepted': agreement.terms_accepted},
        'evaluation': {'challenge_id': agreement.challenge_id, 'decision': 'Recorded in project evaluation workspace'},
        'agreement_version': ({'version': plan.version, 'template': plan.template_key,
            'template_version': plan.template_version, 'approved': plan.approved,
            'change_note': plan.change_note} if plan else None),
        'evidence_and_results': ({'filename': upload.original_filename, 'sha256': upload.sha256_hash,
            'rows': upload.row_count, 'version': db.scalar(select(EvidenceVersion2.version_number).where(EvidenceVersion2.upload_id == upload.id)),
            'integrity_check': 'Verified' if upload_hash_valid else 'Failed or unavailable',
            'submitted_at': upload.created_at.isoformat() if upload.created_at else None} if upload else None),
        'validation': ({'action': decision.action, 'reason': decision.reason,
            'recorded_at': decision.created_at.isoformat() if decision.created_at else None} if decision else None),
        'milestones_and_payments': milestone_rows,
        'scale_up_recommendation': ({'technical_suitability': assessment.technical_suitability,
            'procurement_route_status': assessment.procurement_route_status,
            'findings': assessment.findings} if assessment else None),
        'procurement_route': ({'status': assessment.procurement_route_status,
            'note': assessment.procurement_note} if assessment else {'status': 'Not assessed', 'note': ''}),
        'policy_sources': [{'title': p.title, 'jurisdiction': p.jurisdiction, 'version': p.version,
            'effective_date': p.effective_date.isoformat(), 'url': p.url, 'policy_type': p.policy_type,
            'notes': p.notes} for p in policies],
        'audit_chain': {'valid': chain.valid, 'checked_events': chain.checked_events,
            'first_broken_sequence': chain.first_broken_sequence, 'message': chain.message},
        'public_verify_path': f'/verify/{agreement_id}',
    }


@router.get('/api/passports/{agreement_id}')
def get_passport(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    return _passport(db, agreement_id)


@router.get('/api/passports/{agreement_id}/export.json')
def export_passport_json(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    record = _passport(db, agreement_id)
    return Response(content=json.dumps(record, ensure_ascii=False, indent=2), media_type='application/json',
        headers={'Content-Disposition': f'attachment; filename="pilot-passport-{agreement_id}.json"'})


def _pdf_escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _decision_package_pdf(record: dict) -> bytes:
    problem = record['problem_and_kpis']
    lines = ['PILOT EVIDENCE PASSPORT', 'Decision package · Synthetic demonstration record', '',
        f"Project: {problem['title']}", f"Agreement: {record['id']}",
        f"Agreement version: {(record['agreement_version'] or {}).get('version', 'Not recorded')}",
        f"Evidence integrity: {(record['evidence_and_results'] or {}).get('integrity_check', 'No evidence uploaded')}",
        f"Audit chain: {'Verified' if record['audit_chain']['valid'] else 'Failed'} ({record['audit_chain']['checked_events']} events checked)", '',
        'CLAIM VS RECOMPUTED RESULTS']
    for item in problem['results']:
        lines.append(f"{item['kpi']}: claimed {item['claimed']} · recalculated {item['recomputed']} · {item['outcome']}")
        lines.append(f"  {item['explanation']}")
    lines += ['', 'MILESTONES & PAYMENT TRACKING']
    for milestone in record['milestones_and_payments']:
        pay = milestone['payment']
        lines.append(f"{milestone['code']} · {milestone['title']} · {milestone['state']}")
        if pay: lines.append(f"  {pay['status']} · {pay['reference']} · Simulated: {pay['simulated']}")
    transfer = record['scale_up_recommendation']
    lines += ['', 'SCALE-UP / PROCUREMENT']
    lines.append(f"Technical suitability: {transfer['technical_suitability'] if transfer else 'Not assessed'}")
    lines.append(f"Procurement route: {record['procurement_route']['status']}")
    if transfer:
        for finding in transfer['findings']:
            lines.append(f"{finding['dimension']}: {finding['decision']} · {finding['reason']}")
    lines += ['', record['disclaimer'], 'Limitations: synthetic/demo records where labelled; evidence integrity verifies file changes, not truth.',
        'Payment status reflects simulated settlement only. No real funds move.']
    content = bytearray(b'BT\n/F1 9 Tf\n48 790 Td\n12 TL\n')
    for line in lines[:58]: content.extend(f'({_pdf_escape(str(line)[:150])}) Tj\nT*\n'.encode('latin-1', errors='replace'))
    content.extend(b'ET')
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(content)).encode()+b' >>\nstream\n'+bytes(content)+b'\nendstream']
    pdf = bytearray(b'%PDF-1.4\n%PilotProof\n'); offsets = [0]
    for i, obj in enumerate(objects, 1): offsets.append(len(pdf)); pdf.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref = len(pdf); pdf.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]: pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode())
    return bytes(pdf)


@router.get('/api/passports/{agreement_id}/decision-package.pdf')
def export_decision_package(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    record = _passport(db, agreement_id)
    return Response(content=_decision_package_pdf(record), media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="decision-package-{agreement_id}.pdf"'})


@router.get('/api/verify/{agreement_id}')
def public_verify(agreement_id: str, db: Session = Depends(get_db)):
    record = _passport(db, agreement_id)
    evidence = record['evidence_and_results'] or {}
    # The public response deliberately omits startup user identifiers, invoice files, and reviewer identities.
    return {'id': agreement_id, 'integrity': evidence.get('integrity_check', 'No evidence uploaded'),
        'evidence_sha256': evidence.get('sha256'), 'audit_chain': record['audit_chain'],
        'summary': {'project': record['problem_and_kpis']['title'], 'agreement_version': (record['agreement_version'] or {}).get('version'),
            'evidence_version': evidence.get('version'), 'results': record['problem_and_kpis']['results'],
            'technical_suitability': (record['scale_up_recommendation'] or {}).get('technical_suitability'),
            'procurement_route': record['procurement_route']['status']},
        'disclaimer': record['disclaimer']}
