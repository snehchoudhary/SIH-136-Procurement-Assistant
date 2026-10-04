from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.permissions import require
from app.core.audit_helper import write_audit_event
from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from pydantic import BaseModel, ConfigDict, Field
from app.models.challenge import Challenge, ChallengeVersion
from app.services.challenge_drafting import draft_challenge

router = APIRouter()


class MeasurementDraft(BaseModel):
    challenge_id: str | None = None
    title: str = Field(min_length=3, max_length=250)
    department: str = 'Maharashtra State Innovation Society'
    district: str = 'Maharashtra'
    sector: str = 'Public service'
    problem_statement: str = Field(min_length=10)
    outcomes: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baseline: str = 'Baseline unavailable'
    test_plan: str = ''
    test_duration_days: int | None = Field(default=None, ge=1, le=365)
    acceptance_criteria: list[str] = Field(default_factory=list)
    budget: int | None = None
    deadline: date | None = None
    input_language: str = 'en'
    change_note: str = 'Initial version'


class AIDraftRequest(BaseModel):
    problem_statement: str = Field(min_length=3)
    input_language: str = 'en'


class PublishRequest(BaseModel):
    officer_approved: bool


def _version_payload(version: ChallengeVersion) -> dict:
    return {
        'id': str(version.id), 'challenge_id': version.challenge_id, 'version': version.version,
        'title': '', 'problem_statement': version.problem_statement,
        'description': version.description, 'outcomes': version.outcomes or [],
        'metrics': [part.strip() for part in (version.metric or '').split(';') if part.strip()],
        'baseline': version.baseline, 'test_plan': version.test_plan,
        'test_duration_days': version.test_duration_days,
        'acceptance_criteria': version.acceptance_criteria or [],
        'budget': version.budget, 'deadline': version.deadline.isoformat() if version.deadline else None,
        'input_language': version.input_language, 'change_note': version.change_note,
        'is_published': version.is_published,
    }


def _write_version_fields(version: ChallengeVersion, data: MeasurementDraft) -> None:
    version.description = data.problem_statement
    version.problem_statement = data.problem_statement
    version.outcomes = data.outcomes
    version.metric = '; '.join(data.metrics) if data.metrics else 'To be defined during officer review'
    version.baseline = data.baseline.strip() or 'Baseline unavailable'
    version.test_plan = data.test_plan
    version.test_duration_days = data.test_duration_days
    version.acceptance_criteria = data.acceptance_criteria
    version.budget = data.budget
    version.deadline = data.deadline
    version.input_language = data.input_language if data.input_language in {'en', 'mr'} else 'en'
    version.change_note = data.change_note


@router.post('/ai-draft')
def ai_draft(request: AIDraftRequest, current_user: OIDCUserInfo = Depends(require('challenge.create_draft'))):
    proposal = draft_challenge(request.problem_statement, request.input_language)
    return {'proposal': proposal, 'review_required': True, 'label': 'AI-Drafted, needs review'}


@router.post('/draft', tags=['Officer'])
def create_challenge_draft(data: MeasurementDraft, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.create_draft'))):
    challenge_id = data.challenge_id or f'CH-{uuid4().hex[:10].upper()}'
    if db.query(Challenge).filter(Challenge.id == challenge_id).first():
        raise HTTPException(status_code=409, detail='Challenge ID already exists.')
    challenge = Challenge(
        id=challenge_id, title=data.title, department=data.department, district=data.district,
        sector=data.sector, status='Draft', published_by=UUID(current_user.sub), measurement_locked=False,
    )
    version = ChallengeVersion(challenge_id=challenge_id, version=1, description=data.problem_statement,
                               budget=data.budget, target_pct=None, deadline=data.deadline,
                               metric='To be defined during officer review', created_by=UUID(current_user.sub))
    _write_version_fields(version, data)
    db.add_all([challenge, version])
    db.commit()
    db.refresh(version)
    write_audit_event(db, current_user.sub, current_user.role, 'challenge.draft_created', 'Challenge', challenge_id, 'Initial challenge and measurement-plan draft created.')
    return {'id': challenge_id, 'status': 'Draft', 'version': _version_payload(version)}


@router.put('/{challenge_id}/draft', tags=['Officer'])
def update_challenge_draft(challenge_id: str, data: MeasurementDraft, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.create_draft'))):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail='Challenge not found.')
    if challenge.status != 'Draft' or challenge.measurement_locked:
        raise HTTPException(status_code=409, detail='Published measurement plans are locked. Create a new version instead.')
    version = db.query(ChallengeVersion).filter_by(challenge_id=challenge_id).order_by(ChallengeVersion.version.desc()).first()
    if not version or version.is_published:
        raise HTTPException(status_code=409, detail='No editable draft version exists.')
    challenge.title, challenge.department = data.title, data.department
    challenge.district, challenge.sector = data.district, data.sector
    _write_version_fields(version, data)
    db.commit()
    db.refresh(version)
    write_audit_event(db, current_user.sub, current_user.role, 'challenge.draft_updated', 'Challenge', challenge_id, f'Measurement-plan draft v{version.version} updated.')
    return {'id': challenge_id, 'status': challenge.status, 'version': _version_payload(version)}


@router.post('/{challenge_id}/versions', tags=['Officer'])
def create_challenge_version(challenge_id: str, data: MeasurementDraft, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.create_draft'))):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail='Challenge not found.')
    latest = db.query(ChallengeVersion).filter_by(challenge_id=challenge_id).order_by(ChallengeVersion.version.desc()).first()
    if latest and not latest.is_published:
        raise HTTPException(status_code=409, detail='Finish or discard the current unpublished version before creating another.')
    next_version = (latest.version if latest else 0) + 1
    version = ChallengeVersion(challenge_id=challenge_id, version=next_version, description=data.problem_statement,
                               budget=data.budget, target_pct=None, deadline=data.deadline,
                               metric='To be defined during officer review', created_by=UUID(current_user.sub))
    _write_version_fields(version, data)
    db.add(version)
    db.commit()
    db.refresh(version)
    write_audit_event(db, current_user.sub, current_user.role, 'challenge.version_created', 'ChallengeVersion', str(version.id), f'Challenge {challenge_id} version {version.version} created.')
    return {'id': challenge_id, 'status': 'Version draft', 'version': _version_payload(version)}


@router.put('/{challenge_id}/versions/{version_number}', tags=['Officer'])
def update_challenge_version(challenge_id: str, version_number: int, data: MeasurementDraft, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.create_draft'))):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    version = db.query(ChallengeVersion).filter_by(challenge_id=challenge_id, version=version_number).first()
    if not challenge or not version:
        raise HTTPException(status_code=404, detail='Challenge version not found.')
    if version.is_published:
        raise HTTPException(status_code=409, detail='Published measurement plans are immutable. Create a new version.')
    challenge.title, challenge.department = data.title, data.department
    challenge.district, challenge.sector = data.district, data.sector
    _write_version_fields(version, data)
    db.commit()
    db.refresh(version)
    write_audit_event(db, current_user.sub, current_user.role, 'challenge.version_updated', 'ChallengeVersion', str(version.id), f'Unpublished challenge version {version.version} updated.')
    return {'id': challenge_id, 'status': 'Version draft', 'version': _version_payload(version)}


@router.get('/{challenge_id}/versions')
def list_challenge_versions(challenge_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('challenge.read'))):
    versions = db.query(ChallengeVersion).filter_by(challenge_id=challenge_id).order_by(ChallengeVersion.version.asc()).all()
    payload = [_version_payload(version) for version in versions]
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    for item in payload:
        item['title'] = challenge.title if challenge else ''
    return payload


@router.post('/{challenge_id}/publish', tags=['Officer'])
def publish_challenge_draft(challenge_id: str, request: PublishRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.publish'))):
    if not request.officer_approved:
        raise HTTPException(status_code=400, detail='Explicit officer approval is required to publish.')
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail='Challenge not found.')
    version = db.query(ChallengeVersion).filter_by(challenge_id=challenge_id).order_by(ChallengeVersion.version.desc()).first()
    if not version:
        raise HTTPException(status_code=409, detail='A measurement version is required before publication.')
    if version.baseline.strip().lower() in {'', 'baseline unavailable'}:
        version.baseline = 'Baseline unavailable'
    if not version.outcomes or not version.acceptance_criteria:
        raise HTTPException(status_code=400, detail='Add at least one outcome and acceptance criterion before publishing.')
    version.is_published = True
    challenge.status = 'Open'
    challenge.measurement_locked = True
    challenge.published_by = UUID(current_user.sub)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'challenge.published', 'Challenge', challenge.id, f'Officer explicitly approved and published measurement plan v{version.version}.')
    return {'id': challenge.id, 'status': challenge.status, 'measurement_locked': True, 'published_version': version.version}

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

@router.post("", tags=['Officer'])
def publish_challenge(ch: ChallengeCreate, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'challenge.publish'))):
    raise HTTPException(
        status_code=409,
        detail='Direct publication is disabled. Create and review a guided measurement-plan draft, then explicitly approve it.',
    )

@router.get("")
def list_challenges(db: Session = Depends(get_db)):
    return db.query(Challenge).all()

@router.get("/{id}")
def get_challenge(id: str, db: Session = Depends(get_db)):
    return db.query(Challenge).filter(Challenge.id == id).first()


