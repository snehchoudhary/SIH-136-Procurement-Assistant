from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.audit import AuditEvent
from app.core.audit_helper import verify_record_audit_chain

router = APIRouter()

@router.get("")
def list_audit_events(limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('audit.read'))):
    return db.query(AuditEvent).order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit).all()


@router.get('/verify-records')
def verify_application_audit_records(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('audit.read'))):
    result = verify_record_audit_chain(db)
    return {'valid': result.valid, 'checked_events': result.checked_events,
            'first_broken_event_id': result.first_broken_event_id, 'message': result.message}
