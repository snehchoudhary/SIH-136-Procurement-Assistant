import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\backend")

files = {}

files["app/schemas/__init__.py"] = ""

files["app/schemas/auth.py"] = """from pydantic import BaseModel, ConfigDict
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    sub: str | None = None
"""

files["app/core/security.py"] = """from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings
from pydantic import BaseModel

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

class OIDCUserInfo(BaseModel):
    sub: str
    email: str
    name: str
    role: str
    org_id: str | None = None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> OIDCUserInfo | None:
    try:
        if token.endswith('.local-demo'):
            return None
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            return None
        return OIDCUserInfo(
            sub=sub,
            email=payload.get("email"),
            name=payload.get("name"),
            role=payload.get("role"),
            org_id=payload.get("org_id")
        )
    except JWTError:
        return None
"""

files["app/api/deps.py"] = """from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import verify_token, OIDCUserInfo

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> OIDCUserInfo:
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
"""

files["app/core/permissions.py"] = """from fastapi import Depends, HTTPException, status
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.evidence import EvidenceFile
from app.models.evaluation import ConflictDeclaration

POLICY: dict[str, set[str]] = {
    'challenge.publish':       {'officer'},
    'challenge.create_draft':  {'officer'},
    'startup.register':        {'officer'},
    'startup.verify_eligibility': {'officer'},
    'evaluation.score':        {'evaluator'},
    'evaluation.view':         {'officer', 'evaluator', 'validator'},
    'pilot.approve':           {'officer'},
    'pilot.revise_plan':       {'officer'},
    'evidence.submit':         {'startup'},
    'evidence.validate':       {'validator'},
    'evidence.approve_own':    set(),
    'milestone.accept':        {'officer'},
    'milestone.submit_invoice': {'startup'},
    'milestone.approve_invoice': {'finance'},
    'milestone.initiate_payment': {'finance'},
    'milestone.confirm_payment':  {'finance'},
    'transfer.assess':         {'officer', 'validator'},
    'decision.record':         {'officer'},
    'audit.read':              {'officer', 'validator', 'finance'},
    'policy.read':             {'officer', 'evaluator', 'validator', 'finance', 'startup', 'district'},
}

def require(action: str):
    async def _check(current_user: OIDCUserInfo = Depends(get_current_user)):
        allowed = POLICY.get(action, set())
        if current_user.role not in allowed:
            raise HTTPException(403, detail=f"Role '{current_user.role}' cannot perform '{action}'.")
        return current_user
    return Depends(_check)

def require_no_own_evidence_approval(evidence_file_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if ev and ev.submitted_by == current_user.sub:
        raise HTTPException(403, detail="Cannot validate own evidence")
    return current_user

def require_no_conflict(startup_id: str, challenge_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    conflict = db.query(ConflictDeclaration).filter(
        ConflictDeclaration.evaluator_id == current_user.sub,
        ConflictDeclaration.startup_id == startup_id,
        ConflictDeclaration.challenge_id == challenge_id
    ).first()
    if conflict and conflict.has_conflict:
        raise HTTPException(409, detail="Evaluator has a conflict of interest")
    return current_user
"""

files["app/core/audit_helper.py"] = """import hashlib
from app.models.audit import AuditEvent
from sqlalchemy.orm import Session
from datetime import datetime, timezone

def write_audit_event(db: Session, actor_id: str | None, actor_role: str, action: str, resource_type: str, resource_id: str, detail: str):
    last_event = db.query(AuditEvent).order_by(AuditEvent.occurred_at.desc()).first()
    previous_hash = last_event.event_hash if last_event else "genesis"
    
    # We use current time in UTC
    at_str = datetime.now(timezone.utc).isoformat()
    raw = f"{at_str}{actor_role}{action}{resource_id}{detail}{previous_hash}"
    event_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    
    event = AuditEvent(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        previous_hash=previous_hash,
        event_hash=event_hash
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
"""

for path, content in files.items():
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
print("Third batch created.")
