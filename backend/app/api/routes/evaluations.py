from collections import defaultdict
from statistics import pvariance
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit_helper import write_audit_event
from app.core.permissions import require, require_no_conflict
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.challenge import Challenge
from app.models.evaluation import CommitteeDecision, ConflictDeclaration, Evaluation, RubricVersion
from app.models.startup import Application, Startup

router = APIRouter(tags=['Evaluator'])

DEFAULT_CRITERIA = [
    {'key': 'capability_evidence', 'label': 'Capability evidence', 'weight': 35},
    {'key': 'domain_experience', 'label': 'Domain experience', 'weight': 25},
    {'key': 'language_support', 'label': 'Language support', 'weight': 20},
    {'key': 'deployment_readiness', 'label': 'Deployment readiness', 'weight': 20},
]


class ConflictRequest(BaseModel):
    startup_id: str
    challenge_id: str
    has_conflict: bool
    details: str = ''


class CriterionScore(BaseModel):
    score: int = Field(ge=1, le=5)
    reason: str = Field(min_length=5, max_length=2000)


class ScoreRequest(BaseModel):
    application_id: str
    rubric_version_id: str
    conflict_declaration_id: str
    scores: dict[str, CriterionScore]
    overall_rationale: str = Field(min_length=10, max_length=5000)


class CommitteeDecisionRequest(BaseModel):
    challenge_id: str
    startup_id: str
    decision: str = Field(min_length=2, max_length=80)
    dissent: str = ''
    responsibilities: list[dict[str, str]] = Field(min_length=1)
    reason: str = Field(min_length=10)


def _latest_rubric(db: Session, challenge_id: str) -> RubricVersion | None:
    return db.scalar(select(RubricVersion).where(RubricVersion.challenge_id == challenge_id).order_by(RubricVersion.version.desc()))


@router.get('/rubrics/{challenge_id}', tags=['Evaluator', 'Officer'])
def get_rubric(challenge_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluation.view'))):
    rubric = _latest_rubric(db, challenge_id)
    if not db.get(Challenge, challenge_id):
        raise HTTPException(status_code=404, detail='Challenge not found.')
    return {'id': str(rubric.id) if rubric else None, 'challenge_id': challenge_id,
            'version': rubric.version if rubric else None,
            'criteria': rubric.criteria if rubric and rubric.criteria else DEFAULT_CRITERIA,
            'weights': rubric.weights if rubric else {item['key']: item['weight'] for item in DEFAULT_CRITERIA}}


@router.post('/conflicts', tags=['Evaluator'])
def declare_conflict(request: ConflictRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluator', 'evaluation.score'))):
    try:
        startup_uuid = UUID(request.startup_id)
        evaluator_uuid = UUID(current_user.sub)
    except ValueError as error:
        raise HTTPException(status_code=422, detail='Invalid startup or evaluator identifier.') from error
    if request.has_conflict and not request.details.strip():
        raise HTTPException(status_code=422, detail='Explain the declared conflict before proceeding.')
    startup = db.get(Startup, startup_uuid)
    if not startup or not db.get(Challenge, request.challenge_id):
        raise HTTPException(status_code=404, detail='Startup or challenge not found.')
    declaration = db.scalar(select(ConflictDeclaration).where(
        ConflictDeclaration.evaluator_id == evaluator_uuid,
        ConflictDeclaration.startup_id == startup_uuid,
        ConflictDeclaration.challenge_id == request.challenge_id,
    ).order_by(ConflictDeclaration.declared_at.desc()))
    if declaration is None:
        declaration = ConflictDeclaration(id=uuid4(), evaluator_id=evaluator_uuid, startup_id=startup_uuid,
                                          challenge_id=request.challenge_id, has_conflict=request.has_conflict,
                                          note=request.details.strip())
        db.add(declaration)
    else:
        declaration.has_conflict = request.has_conflict
        declaration.note = request.details.strip()
    db.commit()
    db.refresh(declaration)
    write_audit_event(db, current_user.sub, current_user.role, 'evaluation.conflict_declared' if request.has_conflict else 'evaluation.no_conflict_declared',
                      'ConflictDeclaration', str(declaration.id), request.details.strip() or 'Evaluator declared no conflict.')
    return {'id': str(declaration.id), 'has_conflict': declaration.has_conflict,
            'blocked_from_scoring': declaration.has_conflict, 'details': declaration.note}


@router.get('/queue', tags=['Evaluator'])
def evaluation_queue(challenge_id: str, blind_mode: bool = True, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluator', 'evaluation.score'))):
    applications = db.scalars(select(Application).where(Application.challenge_id == challenge_id).order_by(Application.submitted_at)).all()
    results = []
    for application in applications:
        startup = db.get(Startup, application.startup_id)
        if not startup:
            continue
        declaration = db.scalar(select(ConflictDeclaration).where(
            ConflictDeclaration.evaluator_id == UUID(current_user.sub),
            ConflictDeclaration.startup_id == application.startup_id,
            ConflictDeclaration.challenge_id == challenge_id,
        ).order_by(ConflictDeclaration.declared_at.desc()))
        submitted = db.scalar(select(Evaluation.id).where(
            Evaluation.application_id == application.id,
            Evaluation.evaluator_id == UUID(current_user.sub),
            Evaluation.submitted.is_(True),
        )) is not None
        conflicted = bool(declaration and declaration.has_conflict)
        results.append({
            'application_id': str(application.id),
            'startup_id': str(startup.id),
            'startup_name': None if blind_mode and not submitted else startup.name,
            'blind_label': f'Applicant {str(application.id)[:8].upper()}' if blind_mode and not submitted else startup.name,
            'sector': startup.sector,
            'district': startup.city,
            'conflict_declaration': 'declared' if conflicted else 'none' if declaration else 'required',
            'conflict_details': declaration.note if declaration else '',
            'scoring_blocked': conflicted,
            'scoring_submitted': submitted,
        })
    rubric = _latest_rubric(db, challenge_id)
    return {'challenge_id': challenge_id, 'blind_mode': blind_mode,
            'rubric': {'id': str(rubric.id) if rubric else None, 'version': rubric.version if rubric else None,
                   'criteria': rubric.criteria if rubric and rubric.criteria else DEFAULT_CRITERIA},
            'items': results}


@router.post('/score', tags=['Evaluator'])
def create_evaluation(request: ScoreRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluator', 'evaluation.score'))):
    application = db.get(Application, UUID(request.application_id))
    rubric = db.get(RubricVersion, UUID(request.rubric_version_id))
    declaration = db.get(ConflictDeclaration, UUID(request.conflict_declaration_id))
    if not application or not rubric or not declaration:
        raise HTTPException(status_code=404, detail='Application, rubric, or conflict declaration not found.')
    if rubric.challenge_id != application.challenge_id:
        raise HTTPException(status_code=409, detail='Rubric version does not belong to this application challenge.')
    if declaration.evaluator_id != UUID(current_user.sub) or declaration.startup_id != application.startup_id or declaration.challenge_id != application.challenge_id:
        raise HTTPException(status_code=403, detail='Conflict declaration does not match this evaluator and application.')
    if declaration.has_conflict:
        raise HTTPException(status_code=403, detail='Declared conflict blocks scoring for this startup.')
    criteria = rubric.criteria or DEFAULT_CRITERIA
    required_keys = {criterion['key'] for criterion in criteria}
    if set(request.scores) != required_keys:
        raise HTTPException(status_code=422, detail='Provide one 1–5 score and written reason for every rubric criterion.')
    weights = rubric.weights or {criterion['key']: criterion['weight'] for criterion in criteria}
    total = sum(request.scores[key].score * float(weights.get(key, 0)) for key in required_keys) / 100
    serialized_scores = {key: value.model_dump() for key, value in request.scores.items()}
    evaluation = Evaluation(
        id=uuid4(), application_id=application.id, rubric_version_id=rubric.id,
        evaluator_id=UUID(current_user.sub), conflict_declaration_id=declaration.id,
        scores=serialized_scores, total_score=total, rationale=request.overall_rationale,
        submitted=True,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    write_audit_event(db, current_user.sub, current_user.role, 'evaluation.scored', 'Evaluation', str(evaluation.id),
                      f'Scored application {application.id} against rubric v{rubric.version}; each criterion includes a written reason.')
    return {'status': 'submitted', 'id': str(evaluation.id), 'weighted_total': total, 'rubric_version': rubric.version}


@router.get('/committee/matrix', tags=['Officer'])
def committee_matrix(challenge_id: str, variance_threshold: float = Query(1.0, ge=0, le=4), db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'decision.record'))):
    applications = db.scalars(select(Application).where(Application.challenge_id == challenge_id)).all()
    rubric = _latest_rubric(db, challenge_id)
    matrix = []
    criterion_values: dict[str, list[float]] = defaultdict(list)
    for application in applications:
        startup = db.get(Startup, application.startup_id)
        evaluations = db.scalars(select(Evaluation).where(Evaluation.application_id == application.id, Evaluation.submitted.is_(True))).all()
        for evaluation in evaluations:
            evaluator = db.get(__import__('app.models.user', fromlist=['User']).User, evaluation.evaluator_id)
            scores = {}
            for criterion in (rubric.criteria if rubric and rubric.criteria else DEFAULT_CRITERIA):
                key = criterion['key']
                entry = (evaluation.scores or {}).get(key, {})
                if isinstance(entry, dict):
                    scores[key] = {'score': entry.get('score'), 'reason': entry.get('reason', '')}
                    if isinstance(entry.get('score'), (int, float)):
                        criterion_values[key].append(float(entry['score']))
            matrix.append({
                'startup_id': str(application.startup_id), 'startup_name': startup.name if startup else 'Unknown applicant',
                'evaluator': evaluator.full_name if evaluator else str(evaluation.evaluator_id),
                'evaluation_id': str(evaluation.id), 'scores': scores,
            })
    disagreements = []
    for criterion in (rubric.criteria if rubric and rubric.criteria else DEFAULT_CRITERIA):
        values = criterion_values[criterion['key']]
        variance = pvariance(values) if len(values) > 1 else 0
        if variance > variance_threshold:
            disagreements.append({'criterion': criterion['key'], 'label': criterion['label'], 'variance': variance, 'threshold': variance_threshold, 'flag': True})
    return {'challenge_id': challenge_id, 'rubric_version': rubric.version if rubric else None,
            'criteria': rubric.criteria if rubric and rubric.criteria else DEFAULT_CRITERIA,
            'matrix': matrix, 'disagreements': disagreements, 'variance_threshold': variance_threshold}


@router.post('/committee/decisions', tags=['Officer'])
def record_committee_decision(request: CommitteeDecisionRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'decision.record'))):
    if any(not item.get('name', '').strip() or not item.get('responsibility', '').strip() or not item.get('reason', '').strip() for item in request.responsibilities):
        raise HTTPException(status_code=422, detail='Each named responsibility must include a person, responsibility, and reason.')
    decision = CommitteeDecision(
        id=uuid4(), challenge_id=request.challenge_id, startup_id=UUID(request.startup_id),
        recorded_by=UUID(current_user.sub), decision=request.decision,
        dissent=request.dissent.strip(), responsibilities=request.responsibilities, reason=request.reason,
    )
    application = db.scalar(select(Application).where(Application.startup_id == UUID(request.startup_id), Application.challenge_id == request.challenge_id))
    if application and request.decision.strip().lower() in {'shortlisted', 'select', 'selected', 'approve'}:
        application.status = 'Shortlisted'
    elif application and request.decision.strip().lower() in {'not selected', 'declined', 'reject'}:
        application.status = 'Not selected'
    db.add(decision)
    db.commit()
    db.refresh(decision)
    write_audit_event(db, current_user.sub, current_user.role, 'committee.decision_recorded', 'CommitteeDecision', str(decision.id),
                      f'{request.decision}: {request.reason}; dissent: {request.dissent or "none recorded"}.')
    return {'id': str(decision.id), 'decision': decision.decision, 'recorded': True}


@router.get('')
def list_evaluations(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluation.view'))):
    return db.query(Evaluation).all()


@router.post('')
def create_evaluation_compatibility_alias(request: ScoreRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('evaluator', 'evaluation.score'))):
    return create_evaluation(request, db, current_user)
