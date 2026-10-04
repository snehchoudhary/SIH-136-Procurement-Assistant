from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.permissions import LIFECYCLE_TRANSITION_ACTIONS, enforce_action, require
from app.core.security import OIDCUserInfo
from app.models.pilot import PilotAgreement
from app.models.evidence_verification import EvidenceVersion2, KPIResult2
from app.workflow.engine import (
    LIFECYCLE_STATES,
    LifecycleError,
    create_pilot,
    initiate_payment,
    transition_pilot,
    update_kpi,
    verify_audit_chain,
)
from app.workflow.models import AuditEvent, PaymentAttempt, PilotRecord
from app.services.evidence_invalidation import invalidate_current_evidence
from app.core.audit_helper import write_audit_event

router = APIRouter(prefix='/api', tags=['Officer'])


class TransitionRequest(BaseModel):
    target: str
    reason: str = ''


class KPIChangeRequest(BaseModel):
    reason: str = Field(min_length=1)


class PaymentRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)


@router.get('/lifecycle/states')
def lifecycle_states() -> dict[str, list[str]]:
    return {'main': list(LIFECYCLE_STATES), 'side': ['Disputed', 'Correction Requested', 'Terminated']}


@router.post('/pilots/{pilot_id}')
def post_pilot(pilot_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('pilot.approve'))) -> dict[str, str | int]:
    pilot = create_pilot(db, pilot_id, actor=current_user.sub, role=current_user.role)
    return {'id': pilot.id, 'state': pilot.state, 'kpi_version': pilot.kpi_version}


@router.get('/pilots/{pilot_id}')
def get_pilot(pilot_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('pilot.read'))) -> dict[str, str | int | bool]:
    pilot = db.get(PilotRecord, pilot_id)
    if pilot is None:
        raise HTTPException(status_code=404, detail='Pilot not found.')
    return {
        'id': pilot.id,
        'state': pilot.state,
        'agreement_approved': pilot.agreement_approved,
        'kpi_version': pilot.kpi_version,
        'result_status': pilot.result_status,
        'procurement_route': pilot.procurement_route,
    }


@router.post('/pilots/{pilot_id}/transition')
def post_transition(pilot_id: str, request: TransitionRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)) -> dict[str, str]:
    action = LIFECYCLE_TRANSITION_ACTIONS.get(request.target)
    if action is None:
        raise HTTPException(status_code=422, detail='Unknown lifecycle target.')
    enforce_action(current_user, action)
    if request.target in {'Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated', 'Payment Confirmed'}:
        raise HTTPException(status_code=409, detail=f"{request.target} must be recorded through its dedicated evidence or finance endpoint.")
    if request.target == 'Pilot Running':
        agreement = db.get(PilotAgreement, pilot_id)
        if not agreement or agreement.status != 'Approved' or not agreement.terms_accepted:
            raise HTTPException(status_code=409, detail='An approved agreement and startup term acceptance are required before the pilot can start.')
    try:
        pilot = transition_pilot(
            db, pilot_id, request.target, actor=current_user.sub, role=current_user.role,
            reason=request.reason,
        )
    except LifecycleError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {'id': pilot.id, 'state': pilot.state}


@router.post('/pilots/{pilot_id}/kpi')
def post_kpi_change(pilot_id: str, request: KPIChangeRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)) -> dict[str, str | int]:
    enforce_action(current_user, 'pilot.revise_kpi')
    try:
        pilot = update_kpi(db, pilot_id, actor=current_user.sub, role=current_user.role, reason=request.reason)
    except LifecycleError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    agreement = db.get(PilotAgreement, pilot_id)
    invalidated = invalidate_current_evidence(db, pilot_id, reason='workflow_kpi_changed') if agreement else 0
    if invalidated:
        db.commit()
        write_audit_event(db, current_user.sub, current_user.role, 'evidence.results_invalidated', 'PilotAgreement', pilot_id,
                          f'Workflow KPI inputs changed; {invalidated} evidence version(s) marked stale.')
    return {'id': pilot.id, 'kpi_version': pilot.kpi_version, 'result_status': pilot.result_status,
            'invalidated_evidence_versions': invalidated}


@router.post('/pilots/{pilot_id}/payments', tags=['Finance'])
def post_payment(pilot_id: str, request: PaymentRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.initiate_payment'))) -> dict[str, str | int]:
    raise HTTPException(status_code=409, detail='Payment requests must be linked to an approved milestone invoice. Use the milestone finance endpoint.')


@router.get('/audit/verify', tags=['Validator', 'Finance'])
def get_audit_verification(pilot_id: str | None = None, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('audit.read'))) -> dict[str, bool | int | str | None]:
    result = verify_audit_chain(db, pilot_id)
    return {
        'valid': result.valid,
        'checked_events': result.checked_events,
        'first_broken_sequence': result.first_broken_sequence,
        'message': result.message,
        'note': 'Hashes detect changes. They do not prove a measurement was truthful.',
    }


@router.get('/audit/events', tags=['Validator', 'Finance'])
def get_audit_events(pilot_id: str | None = None, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('audit.read'))) -> list[dict[str, str | int]]:
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.sequence.desc())
    if pilot_id:
        query = query.where(AuditEvent.pilot_id == pilot_id)
    events = db.scalars(query).all()
    return [
        {
            'id': event.id,
            'pilot_id': event.pilot_id,
            'sequence': event.sequence,
            'actor': event.actor,
            'role': event.role,
            'reason': event.reason,
            'before_state': event.before_state,
            'after_state': event.after_state,
            'event_type': event.event_type,
            'previous_hash': event.previous_hash,
            'event_hash': event.event_hash,
            'created_at': event.created_at.isoformat(),
        }
        for event in events
    ]


@router.get('/pilots/{pilot_id}/payments')
def list_payments(pilot_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.initiate_payment'))) -> list[dict[str, str | int]]:
    attempts = db.scalars(select(PaymentAttempt).where(PaymentAttempt.pilot_id == pilot_id)).all()
    return [{'id': item.id, 'idempotency_key': item.idempotency_key, 'status': item.status,
             'reference': item.reference, 'simulated': item.simulated} for item in attempts]
