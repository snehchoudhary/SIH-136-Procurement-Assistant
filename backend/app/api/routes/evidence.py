from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require, require_no_own_evidence_approval
from app.core.security import OIDCUserInfo
from app.models.evidence import EvidenceFile
from app.models.pilot import PilotAgreement
from app.models.startup import Startup

router = APIRouter()

@router.post("/pilots/{id}/evidence", tags=['Startup Applicant'])
def submit_evidence(id: str, filename: str, agreement_version: int, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evidence.submit'))):
    raise HTTPException(status_code=410, detail='Metadata-only evidence submission is disabled. Upload the source CSV through /api/v2/evidence/upload.')

@router.post("/evidence/{id}/validate", tags=['Validator'])
def validate_evidence(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evidence.validate'))):
    require_no_own_evidence_approval(id, db, current_user)
    raise HTTPException(status_code=410, detail='Legacy metadata-only validation is disabled. Review a versioned upload through /api/v2/evidence/{upload_id}/decision.')

@router.get("/pilots/{id}/evidence")
def get_pilot_evidence(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evidence.view'))):
    if current_user.role == 'startup':
        agreement = db.get(PilotAgreement, id)
        startup = db.get(Startup, agreement.startup_id) if agreement else None
        if not current_user.org_id or not startup or str(startup.organisation_id) != current_user.org_id:
            raise HTTPException(status_code=403, detail='Startup users may only access evidence for their own organization.')
    return db.query(EvidenceFile).filter(EvidenceFile.agreement_id == id).all()
