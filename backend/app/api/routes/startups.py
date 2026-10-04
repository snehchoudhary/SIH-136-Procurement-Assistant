from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.startup import Startup, EligibilityCheck

router = APIRouter(tags=['Officer'])

@router.get("")
def list_startups(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluation.view'))):
    return db.query(Startup).all()

@router.post("/{id}/verify-eligibility")
def verify_eligibility(id: str, challenge_id: str, passed: bool, note: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('startup.verify_eligibility'))):
    ec = EligibilityCheck(startup_id=id, challenge_id=challenge_id, checked_by=current_user.sub, passed=passed, note=note)
    db.add(ec)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "startup.eligibility_verified", "Startup", id, f"Eligibility verified for {id}")
    return {"status": "ok"}
