import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workflow.models import AuditEvent, PaymentAttempt, PilotRecord

LIFECYCLE_STATES = (
    'Draft', 'Published', 'Applications Open', 'Evaluating', 'Shortlisted',
    'Agreement Drafted', 'Agreement Approved', 'Pilot Running', 'Evidence Submitted',
    'Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated',
    'Payment Confirmed', 'Scale-up Review', 'Decision Recorded',
)
SIDE_STATES = ('Disputed', 'Correction Requested', 'Terminated')

TRANSITIONS: dict[str, tuple[str, ...]] = {
    'Draft': ('Published', 'Terminated'),
    'Published': ('Applications Open', 'Correction Requested', 'Terminated'),
    'Applications Open': ('Evaluating', 'Correction Requested', 'Terminated'),
    'Evaluating': ('Shortlisted', 'Disputed', 'Correction Requested', 'Terminated'),
    'Shortlisted': ('Agreement Drafted', 'Disputed', 'Correction Requested', 'Terminated'),
    'Agreement Drafted': ('Agreement Approved', 'Disputed', 'Correction Requested', 'Terminated'),
    'Agreement Approved': ('Pilot Running', 'Disputed', 'Correction Requested', 'Terminated'),
    'Pilot Running': ('Evidence Submitted', 'Disputed', 'Correction Requested', 'Terminated'),
    'Evidence Submitted': ('Validated', 'Disputed', 'Correction Requested', 'Terminated'),
    'Validated': ('Accepted', 'Disputed', 'Correction Requested', 'Terminated'),
    'Accepted': ('Invoice Approved', 'Disputed', 'Correction Requested', 'Terminated'),
    'Invoice Approved': ('Payment Initiated', 'Disputed', 'Correction Requested', 'Terminated'),
    'Payment Initiated': ('Payment Confirmed', 'Disputed', 'Correction Requested', 'Terminated'),
    'Payment Confirmed': ('Scale-up Review', 'Disputed', 'Correction Requested', 'Terminated'),
    'Scale-up Review': ('Decision Recorded', 'Disputed', 'Correction Requested', 'Terminated'),
    'Decision Recorded': (),
    'Disputed': ('Correction Requested', 'Terminated'),
    'Correction Requested': ('Published', 'Applications Open', 'Evaluating', 'Shortlisted', 'Agreement Drafted', 'Agreement Approved', 'Pilot Running', 'Evidence Submitted', 'Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated', 'Payment Confirmed', 'Scale-up Review', 'Terminated'),
    'Terminated': (),
}

GENESIS_HASH = '0' * 64


class LifecycleError(ValueError):
    """A requested lifecycle operation violates a business rule."""


@dataclass(frozen=True)
class AuditVerification:
    valid: bool
    checked_events: int
    first_broken_sequence: int | None = None
    message: str = ''


def _canonical_hash_payload(event_values: dict[str, object]) -> str:
    return json.dumps(event_values, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def calculate_event_hash(*, pilot_id: str, sequence: int, actor: str, role: str,
                         reason: str, before_state: str, after_state: str,
                         event_type: str, previous_hash: str, created_at: datetime) -> str:
    normalized_created_at = (
        created_at.replace(tzinfo=timezone.utc)
        if created_at.tzinfo is None
        else created_at.astimezone(timezone.utc)
    )
    payload = {
        'pilot_id': pilot_id,
        'sequence': sequence,
        'actor': actor,
        'role': role,
        'reason': reason,
        'before_state': before_state,
        'after_state': after_state,
        'event_type': event_type,
        'previous_hash': previous_hash,
        'created_at': normalized_created_at.isoformat(),
    }
    return hashlib.sha256(_canonical_hash_payload(payload).encode('utf-8')).hexdigest()


def _append_audit(db: Session, pilot: PilotRecord, *, actor: str, role: str,
                  reason: str, before: str, after: str, event_type: str) -> AuditEvent:
    previous = db.scalar(
        select(AuditEvent).where(AuditEvent.pilot_id == pilot.id).order_by(AuditEvent.sequence.desc())
    )
    sequence = previous.sequence + 1 if previous else 1
    previous_hash = previous.event_hash if previous else GENESIS_HASH
    created_at = datetime.now(timezone.utc)
    digest = calculate_event_hash(
        pilot_id=pilot.id, sequence=sequence, actor=actor, role=role,
        reason=reason, before_state=before, after_state=after,
        event_type=event_type, previous_hash=previous_hash, created_at=created_at,
    )
    event = AuditEvent(
        pilot_id=pilot.id, sequence=sequence, actor=actor, role=role,
        reason=reason, before_state=before, after_state=after,
        event_type=event_type, previous_hash=previous_hash,
        event_hash=digest, created_at=created_at,
    )
    db.add(event)
    return event


def create_pilot(db: Session, pilot_id: str, actor: str = 'demo', role: str = 'Officer') -> PilotRecord:
    existing = db.get(PilotRecord, pilot_id)
    if existing:
        return existing
    pilot = PilotRecord(id=pilot_id)
    db.add(pilot)
    db.flush()
    _append_audit(db, pilot, actor=actor, role=role, reason='Pilot record created.',
                  before='None', after='Draft', event_type='created')
    db.commit()
    db.refresh(pilot)
    return pilot


def transition_pilot(db: Session, pilot_id: str, target: str, *, actor: str,
                     role: str, reason: str = '') -> PilotRecord:
    pilot = db.get(PilotRecord, pilot_id)
    if pilot is None:
        pilot = create_pilot(db, pilot_id, actor=actor, role=role)
    if target not in TRANSITIONS:
        raise LifecycleError(f'Unknown lifecycle state: {target}.')
    if target in ('Disputed', 'Correction Requested') and not reason.strip():
        raise LifecycleError(f'A reason is required when entering {target}.')
    if target == 'Pilot Running' and not pilot.agreement_approved:
        raise LifecycleError('An approved agreement is required before the pilot can start.')
    is_side_transition = target in ('Disputed', 'Correction Requested') and pilot.state not in ('Decision Recorded', 'Terminated')
    if not is_side_transition and target not in TRANSITIONS[pilot.state]:
        raise LifecycleError(f'Transition from {pilot.state} to {target} is not allowed.')

    before = pilot.state
    if target == 'Agreement Approved':
        pilot.agreement_approved = True
    pilot.state = target
    _append_audit(db, pilot, actor=actor, role=role, reason=reason,
                  before=before, after=target, event_type='transition')
    db.commit()
    db.refresh(pilot)
    return pilot


def update_kpi(db: Session, pilot_id: str, *, actor: str, role: str, reason: str) -> PilotRecord:
    pilot = db.get(PilotRecord, pilot_id)
    if pilot is None:
        raise LifecycleError(f'Pilot {pilot_id} does not exist.')
    if not reason.strip():
        raise LifecycleError('A reason is required when changing KPI criteria.')
    before = f'KPI v{pilot.kpi_version}; results {pilot.result_status}'
    pilot.kpi_version += 1
    pilot.result_status = 'Stale, re-review needed'
    after = f'KPI v{pilot.kpi_version}; results {pilot.result_status}'
    _append_audit(db, pilot, actor=actor, role=role, reason=reason,
                  before=before, after=after, event_type='kpi_changed')
    db.commit()
    db.refresh(pilot)
    return pilot


def initiate_payment(db: Session, pilot_id: str, idempotency_key: str, *, actor: str, role: str) -> PaymentAttempt:
    if not idempotency_key.strip():
        raise LifecycleError('An idempotency_key is required.')
    existing = db.scalar(select(PaymentAttempt).where(
        PaymentAttempt.pilot_id == pilot_id,
        PaymentAttempt.idempotency_key == idempotency_key,
    ))
    if existing:
        return existing
    pilot = db.get(PilotRecord, pilot_id)
    if pilot is None:
        raise LifecycleError(f'Pilot {pilot_id} does not exist.')
    if pilot.state != 'Invoice Approved':
        raise LifecycleError('Payment can only be initiated after invoice approval.')
    before = pilot.state
    pilot.state = 'Payment Initiated'
    _append_audit(db, pilot, actor=actor, role=role,
                  reason=f'Payment initiated with idempotency key {idempotency_key}.',
                  before=before, after=pilot.state, event_type='transition')
    import uuid
    attempt = PaymentAttempt(pilot_id=pilot_id, idempotency_key=idempotency_key,
                             status='Initiated', reference=f'SIM-{uuid.uuid4().hex[:12].upper()}', simulated=True)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def verify_audit_chain(db: Session, pilot_id: str | None = None) -> AuditVerification:
    query = select(AuditEvent).order_by(AuditEvent.pilot_id, AuditEvent.sequence)
    if pilot_id:
        query = query.where(AuditEvent.pilot_id == pilot_id).order_by(AuditEvent.sequence)
    events = list(db.scalars(query))
    last_hash_by_pilot: dict[str, str] = {}
    expected_sequence_by_pilot: dict[str, int] = {}

    for event in events:
        expected_sequence = expected_sequence_by_pilot.get(event.pilot_id, 1)
        expected_previous = last_hash_by_pilot.get(event.pilot_id, GENESIS_HASH)
        computed = calculate_event_hash(
            pilot_id=event.pilot_id, sequence=event.sequence, actor=event.actor,
            role=event.role, reason=event.reason, before_state=event.before_state,
            after_state=event.after_state, event_type=event.event_type,
            previous_hash=event.previous_hash, created_at=event.created_at,
        )
        if event.sequence != expected_sequence or event.previous_hash != expected_previous or event.event_hash != computed:
            return AuditVerification(
                valid=False,
                checked_events=sum(expected_sequence_by_pilot.values()) - len(expected_sequence_by_pilot),
                first_broken_sequence=event.sequence,
                message=f'Integrity check failed at event {event.sequence} for pilot {event.pilot_id}.',
            )
        last_hash_by_pilot[event.pilot_id] = event.event_hash
        expected_sequence_by_pilot[event.pilot_id] = expected_sequence + 1

    return AuditVerification(valid=True, checked_events=len(events), message='Audit chain verified.')
