from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.policy import PolicySource

router = APIRouter()

@router.get("")
def list_policies(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('policy.read'))):
    return db.query(PolicySource).all()
