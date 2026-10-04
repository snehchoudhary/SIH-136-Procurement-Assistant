import hashlib
import json
from uuid import UUID
from app.models.audit import AuditEvent
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from dataclasses import dataclass

def write_audit_event(db: Session, actor_id: str | None, actor_role: str, action: str, resource_type: str, resource_id: str, detail: str):
    last_event = db.scalar(select(AuditEvent).order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc()).limit(1))
    previous_hash = last_event.event_hash if last_event else "genesis"
    occurred_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        normalized_actor = UUID(actor_id) if actor_id else None
    except ValueError:
        normalized_actor = None
    payload = {
        'actor_id': str(normalized_actor) if normalized_actor else None,
        'actor_role': actor_role,
        'action': action,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'detail': detail,
        'previous_hash': previous_hash,
        'occurred_at': occurred_at.isoformat(),
    }
    event_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    ).hexdigest()
    event = AuditEvent(
        actor_id=normalized_actor,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        previous_hash=previous_hash,
        event_hash=event_hash,
        occurred_at=occurred_at,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@dataclass(frozen=True)
class RecordAuditVerification:
    valid: bool
    checked_events: int
    first_broken_event_id: str | None
    message: str


def verify_record_audit_chain(db: Session) -> RecordAuditVerification:
    """Verify the append-only application audit_event hash chain."""
    events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.id)))
    previous_hash = 'genesis'
    for index, event in enumerate(events):
        actor = str(event.actor_id) if event.actor_id else None
        payload = {
            'actor_id': actor,
            'actor_role': event.actor_role,
            'action': event.action,
            'resource_type': event.resource_type,
            'resource_id': event.resource_id,
            'detail': event.detail,
            'previous_hash': event.previous_hash,
            'occurred_at': event.occurred_at.isoformat(),
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
        if event.previous_hash != previous_hash or event.event_hash != digest:
            return RecordAuditVerification(False, index, str(event.id), f'Integrity check failed at audit event {event.id}.')
        previous_hash = event.event_hash
    return RecordAuditVerification(True, len(events), None, 'Application audit chain verified.')
