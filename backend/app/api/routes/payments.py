"""Milestone invoice and simulated payment workflow."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit_helper import write_audit_event
from app.core.permissions import require
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.evidence_verification import EvidenceUpload, EvidenceVersion2, KPIResult2, ValidatorDecision
from app.models.pilot import Milestone
from app.models.pilot import PilotAgreement
from app.models.startup import Startup
from app.models.payment import Invoice, PaymentRecord

router = APIRouter(tags=['Finance'])
_INVOICE_DIR = Path(__file__).resolve().parents[2] / 'uploads' / 'invoices'
_ORDERED_STATES = ('Evidence Submitted', 'Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated', 'Payment Confirmed')


def _milestone(db: Session, milestone_id: str) -> Milestone:
    try:
        item = db.get(Milestone, UUID(milestone_id))
    except ValueError as exc:
        raise HTTPException(404, detail='Milestone not found.') from exc
    if item is None:
        raise HTTPException(404, detail='Milestone not found.')
    return item


def _require_milestone_startup_access(db: Session, item: Milestone, current_user: OIDCUserInfo) -> None:
    agreement = db.get(PilotAgreement, item.agreement_id)
    startup = db.get(Startup, agreement.startup_id) if agreement else None
    if current_user.role != 'startup' or not current_user.org_id or not startup or str(startup.organisation_id) != current_user.org_id:
        raise HTTPException(status_code=403, detail='Startup users may only submit invoices for their own organization milestones.')


def _latest_accepted_upload(db: Session, agreement_id: str):
    upload = db.scalar(select(EvidenceUpload).where(EvidenceUpload.pilot_agreement_id == agreement_id)
                       .order_by(EvidenceUpload.created_at.desc()))
    if upload is None:
        raise HTTPException(409, detail='No submitted evidence is available for this milestone.')
    version = db.scalar(select(EvidenceVersion2).where(EvidenceVersion2.upload_id == upload.id))
    decision = db.scalar(select(ValidatorDecision).where(ValidatorDecision.upload_id == upload.id)
                         .order_by(ValidatorDecision.created_at.desc()))
    results = list(db.scalars(select(KPIResult2).where(KPIResult2.upload_id == upload.id)))
    if not version or not version.is_current or not decision or decision.action != 'accepted':
        raise HTTPException(409, detail='The latest evidence must be current and accepted by an independent validator.')
    if not results or any(item.outcome != 'passed' or item.is_stale for item in results):
        raise HTTPException(409, detail='All current KPI results must pass before milestone acceptance.')
    from app.models.pilot import AgreementVersion
    from app.services.evidence_invalidation import measurement_plan_for_version, measurement_plan_fingerprint
    active_plan = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id,
        AgreementVersion.approved.is_(True)).order_by(AgreementVersion.version.desc()))
    expected = measurement_plan_fingerprint(measurement_plan_for_version(active_plan))
    if version.metric_definition_hash and version.measurement_plan_snapshot:
        stored_plan = dict(version.measurement_plan_snapshot)
        stored_calculator = stored_plan.pop('calculator_version', None)
        from app.services.evidence_engine import CALCULATOR_VERSION
        if stored_calculator != CALCULATOR_VERSION or measurement_plan_fingerprint(stored_plan) != expected:
            raise HTTPException(409, detail='Evidence uses an outdated measurement plan and must be recalculated before payment.')
    return upload


def _require_latest_accepted_upload(db: Session, agreement_id: str) -> EvidenceUpload:
    """Fail closed if evidence was replaced or its locked inputs changed."""
    accepted_upload = _latest_accepted_upload(db, agreement_id)
    latest_upload = db.scalar(select(EvidenceUpload).where(EvidenceUpload.pilot_agreement_id == agreement_id)
                              .order_by(EvidenceUpload.created_at.desc()))
    if latest_upload is None or latest_upload.id != accepted_upload.id:
        raise HTTPException(409, detail='The accepted evidence is no longer the latest submission; milestone payment is blocked.')
    return accepted_upload


@router.post('/{id}/accept-evidence')
def accept_milestone_evidence(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.accept'))):
    item = _milestone(db, id)
    _latest_accepted_upload(db, item.agreement_id)
    if item.lifecycle_state != 'Validated':
        raise HTTPException(409, detail=f"Evidence acceptance requires Validated state; milestone is {item.lifecycle_state}.")
    item.lifecycle_state = 'Accepted'
    item.status = 'Accepted'
    item.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'milestone.evidence_accepted', 'Milestone', id,
                      'Milestone evidence accepted after independent validation.')
    return {'milestone_id': id, 'state': item.lifecycle_state}


@router.post('/{id}/invoice', tags=['Startup Applicant'])
async def submit_invoice(id: str, amount: int = Form(...), reference: str = Form('', max_length=100), file: UploadFile = File(...),
                         db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.submit_invoice'))):
    item = _milestone(db, id)
    _require_milestone_startup_access(db, item, current_user)
    if item.lifecycle_state != 'Accepted':
        raise HTTPException(409, detail='A milestone invoice can be submitted only after its evidence is accepted.')
    _require_latest_accepted_upload(db, item.agreement_id)
    if amount <= 0:
        raise HTTPException(422, detail='Invoice amount must be greater than zero.')
    if amount > item.amount:
        raise HTTPException(422, detail='Invoice amount cannot exceed the sanctioned milestone amount.')
    if not file.filename or not file.filename.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(400, detail='Upload an invoice as PDF or image.')
    raw = await file.read(10 * 1024 * 1024 + 1)
    if not raw or len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413 if raw else 400, detail='Invoice file must be between 1 byte and 10 MB.')
    _INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    invoice_id = uuid4()
    safe_filename = Path((file.filename or 'invoice').replace('\\', '/')).name.replace('\x00', '')[:180]
    target = _INVOICE_DIR / f'{invoice_id}_{safe_filename}'
    target.write_bytes(raw)
    record = Invoice(id=invoice_id, milestone_id=UUID(id), submitted_by=UUID(current_user.sub), amount=amount,
                     reference=reference.strip() or None, storage_path=str(target),
                     content_sha256=hashlib.sha256(raw).hexdigest(), approval_status='Submitted')
    db.add(record)
    db.commit()
    db.refresh(record)
    write_audit_event(db, current_user.sub, current_user.role, 'invoice.submitted', 'Invoice', str(record.id),
                      f'Invoice uploaded for milestone {id}; SHA-256 {record.content_sha256}.')
    return {'invoice_id': str(record.id), 'milestone_id': id, 'state': item.lifecycle_state,
            'approval_status': record.approval_status, 'sha256': record.content_sha256}


@router.post('/{id}/approve-invoice')
def approve_invoice(id: str, invoice_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.approve_invoice'))):
    item = _milestone(db, id)
    try:
        invoice = db.get(Invoice, UUID(invoice_id))
    except ValueError as exc:
        raise HTTPException(404, detail='Invoice not found.') from exc
    if invoice is None or invoice.milestone_id != UUID(id):
        raise HTTPException(404, detail='Invoice not found for this milestone.')
    if item.lifecycle_state != 'Accepted' or invoice.approval_status != 'Submitted':
        raise HTTPException(409, detail='Invoice approval requires an Accepted milestone and a submitted invoice.')
    _require_latest_accepted_upload(db, item.agreement_id)
    invoice.approval_status = 'Approved'
    invoice.approved_by = UUID(current_user.sub)
    invoice.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    item.lifecycle_state = 'Invoice Approved'
    item.updated_at = invoice.approved_at
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'invoice.approved', 'Invoice', invoice_id,
                      f'Invoice approved for milestone {id}.')
    return {'invoice_id': invoice_id, 'milestone_id': id, 'state': item.lifecycle_state,
            'approval_status': invoice.approval_status}


@router.post('/{id}/initiate-payment')
def initiate_payment(id: str, invoice_id: str, idempotency_key: str, db: Session = Depends(get_db),
                     current_user: OIDCUserInfo = Depends(require('milestone.initiate_payment'))):
    if not idempotency_key.strip() or len(idempotency_key) > 200:
        raise HTTPException(422, detail='A valid idempotency key is required.')
    item = _milestone(db, id)
    try:
        invoice = db.get(Invoice, UUID(invoice_id))
    except ValueError as exc:
        raise HTTPException(404, detail='Invoice not found.') from exc
    if invoice is None or invoice.milestone_id != UUID(id):
        raise HTTPException(404, detail='Invoice not found for this milestone.')
    existing = db.scalar(select(PaymentRecord).where(PaymentRecord.idempotency_key == idempotency_key))
    if existing:
        if existing.invoice_id != UUID(invoice_id):
            raise HTTPException(409, detail='This idempotency key is already assigned to a different invoice.')
        return {'payment_id': str(existing.id), 'state': item.lifecycle_state, 'status': existing.status,
                'reference': existing.reference, 'simulated': True, 'banner': 'Simulated settlement. No real funds move.'}
    if item.lifecycle_state != 'Invoice Approved' or invoice.approval_status != 'Approved':
        raise HTTPException(409, detail='Payment can start only after the invoice is approved.')
    _require_latest_accepted_upload(db, item.agreement_id)
    payment = PaymentRecord(invoice_id=UUID(invoice_id), idempotency_key=idempotency_key,
                            approved_by=UUID(current_user.sub), status='Initiated',
                            reference=f'SIM-{uuid4().hex[:12].upper()}', simulated=True,
                            details={'adapter': 'mock-bank', 'note': 'No real funds move.'})
    db.add(payment)
    item.lifecycle_state = 'Payment Initiated'
    item.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(payment)
    write_audit_event(db, current_user.sub, current_user.role, 'payment.initiated', 'PaymentRecord', str(payment.id),
                      f'Simulated payment initiated: {payment.reference}. No real funds move.')
    return {'payment_id': str(payment.id), 'state': item.lifecycle_state, 'status': payment.status,
            'reference': payment.reference, 'simulated': True, 'banner': 'Simulated settlement. No real funds move.'}


@router.post('/{id}/confirm-payment')
def confirm_payment(id: str, payment_id: str, db: Session = Depends(get_db),
                    current_user: OIDCUserInfo = Depends(require('milestone.confirm_payment'))):
    item = _milestone(db, id)
    try:
        payment = db.get(PaymentRecord, UUID(payment_id))
    except ValueError as exc:
        raise HTTPException(404, detail='Payment request not found.') from exc
    if payment is None:
        raise HTTPException(404, detail='Payment request not found.')
    invoice = db.get(Invoice, payment.invoice_id)
    if invoice is None or invoice.milestone_id != UUID(id):
        raise HTTPException(404, detail='Payment request not found for this milestone.')
    if item.lifecycle_state != 'Payment Initiated' or payment.status != 'Initiated' or not payment.simulated:
        raise HTTPException(409, detail='Only an initiated simulated payment can be confirmed.')
    _require_latest_accepted_upload(db, item.agreement_id)
    payment.status = 'Confirmed'
    item.lifecycle_state = 'Payment Confirmed'
    item.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'payment.confirmed', 'PaymentRecord', payment_id,
                      f'Simulated settlement confirmed under reference {payment.reference}. No real funds moved.')
    return {'payment_id': payment_id, 'state': item.lifecycle_state, 'status': payment.status,
            'reference': payment.reference, 'simulated': True, 'banner': 'Simulated settlement. No real funds move.'}


@router.get('')
def list_milestones(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('finance.read'))):
    rows = db.scalars(select(Milestone).order_by(Milestone.updated_at.desc())).all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = []
    for item in rows:
        invoice = db.scalar(select(Invoice).where(Invoice.milestone_id == item.id).order_by(Invoice.submitted_at.desc()))
        payment = db.scalar(select(PaymentRecord).where(PaymentRecord.invoice_id == invoice.id).order_by(PaymentRecord.created_at.desc())) if invoice else None
        blocked = {
            'Evidence Submitted': 'Waiting for an independent validator to review current evidence.',
            'Validated': 'Waiting for an officer to accept the validated milestone.',
            'Accepted': 'Waiting for the startup to upload an invoice.',
            'Invoice Approved': 'Ready for Finance to initiate a simulated payment.',
            'Payment Initiated': 'Waiting for Finance to confirm the simulated settlement.',
            'Payment Confirmed': 'No blocker. Settlement is recorded as simulated.',
        }.get(item.lifecycle_state, 'Evidence and milestone action are pending.')
        entered = item.updated_at or item.planned_start
        days = max(0, (now.date() - (entered if hasattr(entered, 'year') else now.date())).days) if entered else 0
        result.append({'id': str(item.id), 'agreement_id': item.agreement_id, 'code': item.code,
                       'title': item.title, 'amount': item.amount, 'state': item.lifecycle_state,
                       'status': item.status, 'days_in_state': days, 'why_blocked': blocked,
                       'invoice': ({'id': str(invoice.id), 'amount': invoice.amount,
                                    'approval_status': invoice.approval_status, 'reference': invoice.reference,
                                    'sha256': invoice.content_sha256} if invoice else None),
                       'payment': ({'id': str(payment.id), 'status': payment.status,
                                   'reference': payment.reference, 'simulated': payment.simulated} if payment else None)})
    return {'items': result, 'settlement_notice': 'Simulated settlement. No real funds move.',
            'funds_notice': 'The platform tracks sanctioned funding and acceptance; it does not hold public money.',
            'states': list(_ORDERED_STATES)}
