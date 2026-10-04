import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\backend")
files = {}

files["app/api/routes/auth.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import create_access_token, verify_token, OIDCUserInfo
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={
        "sub": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "org_id": str(user.organisation_id) if user.organisation_id else None
    })
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email, "role": user.role}}

@router.get("/me")
def read_users_me(current_user: OIDCUserInfo = Depends(get_current_user)):
    return current_user
"""

files["app/api/routes/challenges.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from pydantic import BaseModel, ConfigDict
from app.models.challenge import Challenge, ChallengeVersion

router = APIRouter()

class ChallengeCreate(BaseModel):
    id: str
    title: str
    department: str
    district: str
    sector: str
    budget: int
    target_pct: float
    deadline: str
    metric: str
    description: str

@router.post("")
def publish_challenge(ch: ChallengeCreate, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('challenge.publish'))):
    challenge = Challenge(
        id=ch.id, title=ch.title, department=ch.department,
        district=ch.district, sector=ch.sector, status="Open", published_by=current_user.sub
    )
    db.add(challenge)
    db.commit()
    
    cv = ChallengeVersion(
        challenge_id=ch.id, version=1, description=ch.description, budget=ch.budget,
        target_pct=ch.target_pct, deadline=ch.deadline, metric=ch.metric, created_by=current_user.sub
    )
    db.add(cv)
    db.commit()
    
    write_audit_event(db, current_user.sub, current_user.role, "challenge.published", "Challenge", ch.id, f"Challenge {ch.id} published")
    return {"status": "ok", "id": ch.id}

@router.get("")
def list_challenges(db: Session = Depends(get_db)):
    return db.query(Challenge).all()

@router.get("/{id}")
def get_challenge(id: str, db: Session = Depends(get_db)):
    return db.query(Challenge).filter(Challenge.id == id).first()
"""

files["app/api/routes/startups.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.startup import Startup, EligibilityCheck

router = APIRouter()

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
"""

files["app/api/routes/evaluations.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require, require_no_conflict
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.evaluation import Evaluation

router = APIRouter()

@router.post("")
def create_evaluation(application_id: str, rubric_version_id: str, startup_id: str, challenge_id: str, conflict_declaration_id: str, scores: dict, rationale: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluation.score'))):
    require_no_conflict(startup_id, challenge_id, db, current_user)
    total = sum(scores.values())
    ev = Evaluation(application_id=application_id, rubric_version_id=rubric_version_id, evaluator_id=current_user.sub, conflict_declaration_id=conflict_declaration_id, scores=scores, total_score=total, rationale=rationale)
    db.add(ev)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "evaluation.scored", "Evaluation", str(ev.id), f"Evaluation scored for app {application_id}")
    return {"status": "ok", "id": str(ev.id)}

@router.get("")
def list_evaluations(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluation.view'))):
    return db.query(Evaluation).all()
"""

files["app/api/routes/pilots.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.pilot import PilotAgreement, AgreementVersion, Milestone

router = APIRouter()

@router.post("")
def approve_pilot(id: str, challenge_id: str, startup_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('pilot.approve'))):
    pa = PilotAgreement(id=id, challenge_id=challenge_id, startup_id=startup_id, status="Active", approved_by=current_user.sub)
    db.add(pa)
    db.commit()
    
    # Generate 3 milestones
    for i in range(1, 4):
        ms = Milestone(agreement_id=id, code=f"M{i}", title=f"Milestone {i}", amount=100000, status="Awaiting evidence")
        db.add(ms)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "pilot.approved", "PilotAgreement", id, f"Pilot {id} approved")
    return {"status": "ok"}

@router.get("")
def list_pilots(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    return db.query(PilotAgreement).all()

@router.post("/{id}/revise")
def revise_pilot(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('pilot.revise_plan'))):
    write_audit_event(db, current_user.sub, current_user.role, "pilot.revised", "PilotAgreement", id, f"Pilot {id} revised")
    return {"status": "ok"}
"""

files["app/api/routes/evidence.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require, require_no_own_evidence_approval
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.evidence import EvidenceFile

router = APIRouter()

@router.post("/pilots/{id}/evidence")
def submit_evidence(id: str, filename: str, agreement_version: int, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evidence.submit'))):
    ev = EvidenceFile(agreement_id=id, agreement_version=agreement_version, submitted_by=current_user.sub, filename=filename, status="Submitted")
    db.add(ev)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "evidence.submitted", "EvidenceFile", str(ev.id), f"Evidence {filename} submitted")
    return {"status": "ok"}

@router.post("/evidence/{id}/validate")
def validate_evidence(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evidence.validate'))):
    require_no_own_evidence_approval(id, db, current_user)
    write_audit_event(db, current_user.sub, current_user.role, "evidence.validated", "EvidenceFile", id, f"Evidence {id} validated")
    return {"status": "ok"}

@router.get("/pilots/{id}/evidence")
def get_pilot_evidence(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    return db.query(EvidenceFile).filter(EvidenceFile.agreement_id == id).all()
"""

files["app/api/routes/payments.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.payment import Invoice, PaymentRecord
import uuid

router = APIRouter()

@router.post("/{id}/invoice")
def submit_invoice(id: str, amount: int, reference: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.submit_invoice'))):
    inv = Invoice(milestone_id=id, submitted_by=current_user.sub, amount=amount, reference=reference)
    db.add(inv)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "invoice.submitted", "Invoice", str(inv.id), f"Invoice submitted for milestone {id}")
    return {"status": "ok"}

@router.post("/{id}/approve-invoice")
def approve_invoice(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.approve_invoice'))):
    write_audit_event(db, current_user.sub, current_user.role, "invoice.approved", "Milestone", id, f"Invoice approved for milestone {id}")
    return {"status": "ok"}

@router.post("/{id}/initiate-payment")
def initiate_payment(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.initiate_payment'))):
    write_audit_event(db, current_user.sub, current_user.role, "payment.initiated", "Milestone", id, f"Payment initiated for milestone {id}")
    return {"status": "ok"}

@router.post("/{id}/confirm-payment")
def confirm_payment(id: str, invoice_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('milestone.confirm_payment'))):
    pr = PaymentRecord(invoice_id=invoice_id, idempotency_key=str(uuid.uuid4()), approved_by=current_user.sub, status="Confirmed")
    db.add(pr)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, "payment.confirmed", "PaymentRecord", str(pr.id), f"Payment confirmed for invoice {invoice_id}")
    return {"status": "ok"}

@router.get("")
def list_milestones(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    # Assuming list milestones is here
    return []
"""

files["app/api/routes/policies.py"] = """from fastapi import APIRouter, Depends
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
"""

files["app/api/routes/audit.py"] = """from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.models.audit import AuditEvent

router = APIRouter()

@router.get("")
def list_audit_events(limit: int = 100, offset: int = 0, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('audit.read'))):
    return db.query(AuditEvent).order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit).all()
"""

files["app/main.py"] = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, auth, challenges, startups, evaluations, pilots, evidence, payments, policies, audit

tags_metadata = [
    {"name": "auth", "description": "Authentication — all roles"},
    {"name": "challenges", "description": "Challenges — Officer publishes, all read"},
    {"name": "startups", "description": "Startups — Officer verifies eligibility"},
    {"name": "evaluations", "description": "Evaluations — Evaluator only (conflict-guarded)"},
    {"name": "pilots", "description": "Pilots — Officer approves and revises"},
    {"name": "evidence", "description": "Evidence — Startup submits, Validator reviews"},
    {"name": "payments", "description": "Payments — Finance approves (startup invoices)"},
    {"name": "policies", "description": "Policies — All roles read-only"},
    {"name": "audit", "description": "Audit log — Officer, Validator, Finance"},
    {"name": "health", "description": "Health check"},
]

app = FastAPI(openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["challenges"])
app.include_router(startups.router, prefix="/api/startups", tags=["startups"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])
app.include_router(pilots.router, prefix="/api/pilots", tags=["pilots"])
app.include_router(evidence.router, prefix="/api", tags=["evidence"])
app.include_router(payments.router, prefix="/api/milestones", tags=["payments"])
app.include_router(policies.router, prefix="/api/policies", tags=["policies"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
"""

for path, content in files.items():
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
print("Fourth batch created.")
