from datetime import date, timedelta
from copy import deepcopy
import math
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit_helper import write_audit_event
from app.core.permissions import require
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.challenge import Challenge
from app.models.evaluation import CommitteeDecision
from app.models.organisation import Organisation
from app.models.pilot import AgreementTemplate, AgreementVersion, Milestone, PilotAgreement, StartupOfficerQuestion
from app.models.startup import Application, Startup
from app.models.user import User
from app.workflow.engine import LifecycleError, create_pilot, transition_pilot
from app.workflow.models import PilotRecord
from app.services.evidence_engine import MEASUREMENT_PLAN
from app.services.evidence_invalidation import invalidate_current_evidence
from app.models.payment import Invoice, PaymentRecord

router = APIRouter(tags=['Officer'])

CLAUSE_KEYS = ('milestones', 'evidence_requirements', 'data_access', 'ip', 'security', 'acceptance', 'termination', 'payment_conditions')
DEFAULT_CLAUSES = {
    'milestones': 'Three milestones, each with dated deliverables and review points.',
    'evidence_requirements': 'Submit source records, method notes, timestamps, and relevant limitations for each KPI.',
    'data_access': 'Specify the minimum data needed, authorized users, access period, and return/deletion steps.',
    'ip': 'Each party retains its pre-existing intellectual property; list any pilot-specific licence explicitly.',
    'security': 'Document implemented controls, incident contacts, and access responsibilities. This is not a compliance certification.',
    'acceptance': 'Acceptance requires review against the locked KPI definitions and recorded evidence requirements.',
    'termination': 'State notice period, termination grounds, transition tasks, and handling of incomplete milestones.',
    'payment_conditions': 'Payment tracking follows milestone acceptance and invoice review; any settlement shown here is simulated.',
}


class AgreementDraftRequest(BaseModel):
    agreement_id: str | None = None
    startup_id: str
    challenge_id: str
    template_key: str = 'standard-pilot'
    clauses: dict[str, str] = Field(default_factory=lambda: DEFAULT_CLAUSES.copy())
    change_note: str = 'Initial agreement draft'
    approver_user_ids: list[str] = Field(min_length=1)
    milestones: list[dict] = Field(default_factory=list)
    measurement_plan: dict[str, float | int] = Field(default_factory=dict)


class AgreementRevisionRequest(BaseModel):
    clauses: dict[str, str]
    change_note: str = Field(min_length=3)
    milestones: list[dict] = Field(default_factory=list)
    measurement_plan: dict[str, float | int] | None = None


class TermsAcceptance(BaseModel):
    accepted: bool


class QuestionRequest(BaseModel):
    body: str = Field(min_length=2, max_length=4000)


class PilotStartRequest(BaseModel):
    reason: str = Field(min_length=5)


class AgreementTemplateRequest(BaseModel):
    template_key: str = Field(default='standard-pilot', min_length=2, max_length=80, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$')
    clauses: dict[str, str]
    label: str | None = Field(default=None, min_length=2, max_length=120)


def _version_dict(version: AgreementVersion) -> dict:
    return {
        'id': str(version.id), 'agreement_id': version.agreement_id, 'version': version.version,
        'template_key': version.template_key, 'template_version': version.template_version,
        'clauses': version.clauses or {},
        'measurement_plan': {
            'baseline_minutes': version.baseline_minutes,
            'target_reduction_pct': version.target_pct,
            'max_error_rate_pct': version.error_limit_pct,
            'min_marathi_accuracy_pct': version.marathi_accuracy_pct,
            'min_total_observations': version.min_observations,
            'min_marathi_samples': version.min_marathi_observations,
            'max_bandwidth_mbps': version.bandwidth_mbps,
            'capacity_per_day': version.capacity_per_day,
        },
        'change_note': version.change_note, 'approved': version.approved,
        'start_date': version.start_date.isoformat(), 'end_date': version.end_date.isoformat(),
    }


def _verify_startup_access(db: Session, agreement: PilotAgreement, user: OIDCUserInfo) -> None:
    if user.role != 'startup':
        raise HTTPException(status_code=403, detail='Startup account required.')
    try:
        organization_id = UUID(user.org_id) if user.org_id else None
    except ValueError as error:
        raise HTTPException(status_code=403, detail='Startup organization is not linked.') from error
    startup = db.get(Startup, agreement.startup_id)
    if not startup or organization_id is None or startup.organisation_id != organization_id:
        raise HTTPException(status_code=403, detail='This agreement does not belong to your organization.')


def _verify_agreement_read_access(db: Session, agreement: PilotAgreement, user: OIDCUserInfo) -> None:
    if user.role == 'startup':
        _verify_startup_access(db, agreement, user)
    elif user.role not in {'officer', 'evaluator', 'validator', 'finance', 'district'}:
        raise HTTPException(status_code=403, detail='Role cannot view this agreement.')


def _create_lifecycle_record(db: Session, agreement_id: str, actor: str) -> None:
    record = create_pilot(db, agreement_id, actor=actor, role='officer')
    if record.state == 'Draft':
        for state in ('Published', 'Applications Open', 'Evaluating', 'Shortlisted', 'Agreement Drafted'):
            transition_pilot(db, agreement_id, state, actor=actor, role='officer', reason='Shortlisted synthetic application and agreement draft created.')


def _milestone_list(db: Session, agreement_id: str) -> list[dict]:
    items = db.scalars(select(Milestone).where(Milestone.agreement_id == agreement_id).order_by(Milestone.planned_start, Milestone.code)).all()
    return [{'id': str(item.id), 'code': item.code, 'title': item.title, 'amount': item.amount,
             'status': item.status, 'lifecycle_state': item.lifecycle_state,
             'evidence_requirements': item.evidence_requirements or [],
             'acceptance_criteria': item.acceptance_criteria or [], 'linked_kpis': item.linked_kpis or [],
             'planned_start': item.planned_start.isoformat() if item.planned_start else None,
             'planned_end': item.planned_end.isoformat() if item.planned_end else None,
             'note': item.note} for item in items]


def _create_milestones(db: Session, agreement_id: str, milestones: list[dict], start_date: date) -> None:
    plan = milestones or [
        {'code': 'M1', 'title': 'Mobilization and baseline', 'amount': 100000,
         'evidence_requirements': ['Approved baseline method', 'Site readiness record'],
         'acceptance_criteria': ['Baseline collection is documented and reviewable'], 'linked_kpis': ['baseline'], 'days': [0, 30]},
        {'code': 'M2', 'title': 'Field pilot and evidence submission', 'amount': 150000,
         'evidence_requirements': ['Timestamped service records', 'Sample and limitation notes'],
         'acceptance_criteria': ['Evidence covers the locked KPI definitions'], 'linked_kpis': ['service_response_time'], 'days': [31, 65]},
        {'code': 'M3', 'title': 'Independent validation and handover', 'amount': 100000,
         'evidence_requirements': ['Validator review', 'Operational handover checklist'],
         'acceptance_criteria': ['Results reviewed by an independent validator'], 'linked_kpis': ['validated_outcome'], 'days': [66, 90]},
    ]
    if len(plan) != 3:
        raise HTTPException(status_code=422, detail='Each agreement must define exactly three milestones.')
    for index, item in enumerate(plan):
        days = item.get('days', [index * 30, (index + 1) * 30])
        db.add(Milestone(
            id=uuid4(), agreement_id=agreement_id, code=item.get('code', f'M{index + 1}'),
            title=item.get('title', f'Milestone {index + 1}'), amount=int(item.get('amount', 0)),
            status='Awaiting evidence', note=None,
            evidence_requirements=item.get('evidence_requirements', []),
            acceptance_criteria=item.get('acceptance_criteria', []),
            linked_kpis=item.get('linked_kpis', []),
            planned_start=start_date + timedelta(days=int(days[0])),
            planned_end=start_date + timedelta(days=int(days[1])),
            lifecycle_state='Agreement Drafted',
        ))


def _make_version(db: Session, agreement_id: str, template_key: str, clauses: dict[str, str], *,
                  user_id: UUID, change_note: str, version_number: int, template_version: int = 1,
                  measurement_plan: dict | None = None) -> AgreementVersion:
    missing = [key for key in CLAUSE_KEYS if not clauses.get(key, '').strip()]
    if missing:
        raise HTTPException(status_code=422, detail=f'Missing required agreement clauses: {", ".join(missing)}.')
    today = date.today()
    start_date = today + timedelta(days=7)
    plan = {**MEASUREMENT_PLAN, **(measurement_plan or {})}
    allowed_keys = {'baseline_minutes', 'target_reduction_pct', 'max_error_rate_pct', 'min_marathi_accuracy_pct',
                    'min_marathi_samples', 'min_total_observations', 'max_bandwidth_mbps', 'capacity_per_day',
                    'min_low_bandwidth_samples', 'min_low_bandwidth_success_pct', 'min_segment_samples'}
    if set(plan) - allowed_keys or any(not isinstance(v, (int, float)) or not math.isfinite(float(v)) or v < 0 for v in plan.values()):
        raise HTTPException(status_code=422, detail='Measurement plan contains unsupported or negative values.')
    if any(not 0 <= float(plan[key]) <= 100 for key in ('target_reduction_pct', 'max_error_rate_pct', 'min_marathi_accuracy_pct')):
        raise HTTPException(status_code=422, detail='Percentage thresholds must be between 0 and 100.')
    if plan['baseline_minutes'] <= 0 or plan['max_bandwidth_mbps'] <= 0 or plan['min_total_observations'] < 1 or plan['min_marathi_samples'] < 1 or plan['capacity_per_day'] < 1 or plan['min_low_bandwidth_samples'] < 1:
        raise HTTPException(status_code=422, detail='Measurement plan baseline, sample sizes, bandwidth, and capacity must be positive.')
    version = AgreementVersion(
        id=uuid4(), agreement_id=agreement_id, version=version_number,
        baseline_minutes=plan['baseline_minutes'], target_pct=plan['target_reduction_pct'],
        error_limit_pct=plan['max_error_rate_pct'], marathi_accuracy_pct=plan['min_marathi_accuracy_pct'],
        min_observations=plan['min_total_observations'], min_marathi_observations=plan['min_marathi_samples'],
        bandwidth_mbps=plan['max_bandwidth_mbps'], capacity_per_day=plan['capacity_per_day'],
        start_date=start_date, end_date=start_date + timedelta(days=90),
        revised_by=user_id, revision_reason=change_note, template_key=template_key,
        template_version=template_version,
        clauses=clauses, change_note=change_note, approved=False,
    )
    db.add(version)
    db.flush()
    return version


@router.get('/templates')
def list_agreement_templates(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    templates = db.scalars(select(AgreementTemplate).where(AgreementTemplate.published.is_(True)).order_by(AgreementTemplate.template_key, AgreementTemplate.version.desc())).all()
    if templates:
        return [{'id': str(item.id), 'template_key': item.template_key, 'version': item.version, 'label': item.label, 'clauses': item.clauses} for item in templates]
    return [{'id': None, 'template_key': 'standard-pilot', 'version': 1, 'label': 'Standard pilot agreement (starter template)', 'clauses': DEFAULT_CLAUSES}]


@router.post('/templates', tags=['Officer'])
def publish_agreement_template(payload: AgreementTemplateRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.approve'))):
    key = payload.template_key
    clauses = payload.clauses
    if any(not clauses.get(clause, '').strip() for clause in CLAUSE_KEYS):
        raise HTTPException(status_code=422, detail='Template must include every required clause.')
    latest = db.scalar(select(AgreementTemplate).where(AgreementTemplate.template_key == key).order_by(AgreementTemplate.version.desc()))
    item = AgreementTemplate(id=uuid4(), template_key=key, version=(latest.version + 1 if latest else 1),
                             label=payload.label or key, clauses=clauses, published=True,
                             created_by=UUID(current_user.sub))
    db.add(item); db.commit(); db.refresh(item)
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.template_published', 'AgreementTemplate', str(item.id), f'Published template {key} v{item.version}.')
    return {'id': str(item.id), 'template_key': key, 'version': item.version}


@router.post('/drafts', tags=['Officer'])
def create_agreement_draft(payload: AgreementDraftRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.approve'))):
    try:
        startup_uuid, creator_uuid = UUID(payload.startup_id), UUID(current_user.sub)
        approver_ids = [UUID(item) for item in payload.approver_user_ids]
    except ValueError as error:
        raise HTTPException(status_code=422, detail='Invalid startup, approver, or actor identifier.') from error
    if len(set(approver_ids)) != len(approver_ids):
        raise HTTPException(status_code=422, detail='Approval chain must not contain duplicate approvers.')
    startup, challenge = db.get(Startup, startup_uuid), db.get(Challenge, payload.challenge_id)
    if not startup or not challenge:
        raise HTTPException(status_code=404, detail='Startup or challenge not found.')
    application = db.scalar(select(Application).where(Application.startup_id == startup_uuid, Application.challenge_id == payload.challenge_id))
    if application is None or application.status.lower() not in {'shortlisted', 'selected'}:
        raise HTTPException(status_code=409, detail='Only a shortlisted startup can proceed to agreement drafting.')
    approvers = []
    for approver_id in approver_ids:
        user = db.get(User, approver_id)
        if not user or user.role not in {'officer', 'validator', 'finance'}:
            raise HTTPException(status_code=422, detail=f'Approver {approver_id} must be a named officer, validator, or finance user.')
        approvers.append({'user_id': str(approver_id), 'name': user.full_name, 'role': user.role, 'approved': False, 'approved_at': None})
    template = db.scalar(select(AgreementTemplate).where(AgreementTemplate.template_key == payload.template_key, AgreementTemplate.published.is_(True)).order_by(AgreementTemplate.version.desc()))
    clauses = payload.clauses or (template.clauses if template else DEFAULT_CLAUSES.copy())
    agreement_id = payload.agreement_id or f'PA-{uuid4().hex[:12].upper()}'
    if db.get(PilotAgreement, agreement_id):
        raise HTTPException(status_code=409, detail='Agreement ID already exists.')
    agreement = PilotAgreement(id=agreement_id, challenge_id=challenge.id, startup_id=startup_uuid,
                               status='Draft', approved_by=None, terms_accepted=False,
                               approval_chain=approvers, created_by=creator_uuid)
    db.add(agreement); db.flush()
    version = _make_version(db, agreement_id, payload.template_key, clauses, user_id=creator_uuid,
                             change_note=payload.change_note, version_number=1,
                             template_version=template.version if template else 1,
                             measurement_plan=payload.measurement_plan)
    _create_milestones(db, agreement_id, payload.milestones, version.start_date)
    _create_lifecycle_record(db, agreement_id, current_user.sub)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.draft_created', 'PilotAgreement', agreement_id,
                      f'Agreement v1 drafted from shortlist; {len(approvers)} named approver(s).')
    return {'id': agreement_id, 'status': agreement.status, 'version': _version_dict(version),
            'approval_chain': approvers, 'terms_accepted': agreement.terms_accepted,
            'milestones': _milestone_list(db, agreement_id)}


@router.get('')
def list_pilots(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    query = select(PilotAgreement)
    if current_user.role == 'startup':
        if not current_user.org_id:
            return []
        query = query.join(Startup, Startup.id == PilotAgreement.startup_id).where(Startup.organisation_id == UUID(current_user.org_id))
    elif current_user.role not in {'officer', 'evaluator', 'validator', 'finance', 'district'}:
        raise HTTPException(status_code=403, detail='Role cannot view pilot agreements.')
    payload = []
    for item in db.scalars(query.order_by(PilotAgreement.created_at.desc())):
        startup_name = None
        if current_user.role != 'startup':
            startup = db.get(Startup, item.startup_id)
            startup_name = startup.name if startup else None
        payload.append({'id': item.id, 'challenge_id': item.challenge_id, 'startup_id': str(item.startup_id),
                        'startup_name': startup_name, 'status': item.status,
                        'terms_accepted': item.terms_accepted, 'approval_chain': item.approval_chain})
    return payload


@router.get('/{agreement_id}/versions')
def list_agreement_versions(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    _verify_agreement_read_access(db, agreement, current_user)
    versions = db.scalars(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id).order_by(AgreementVersion.version)).all()
    return [_version_dict(item) for item in versions]


@router.post('/{agreement_id}/versions', tags=['Officer'])
def revise_agreement(agreement_id: str, payload: AgreementRevisionRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.revise_plan'))):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    latest = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id).order_by(AgreementVersion.version.desc()))
    if not latest or not latest.approved:
        raise HTTPException(status_code=409, detail='Only an approved agreement can be revised into a new version.')
    invoice_history = db.scalar(select(Invoice.id).join(Milestone, Invoice.milestone_id == Milestone.id)
                                .where(Milestone.agreement_id == agreement_id).limit(1))
    if invoice_history:
        raise HTTPException(status_code=409, detail='Agreement criteria cannot be revised after invoice history exists; preserve the payment record and create a new pilot version.')
    selected_template = db.scalar(select(AgreementTemplate).where(
        AgreementTemplate.template_key == latest.template_key,
        AgreementTemplate.published.is_(True),
    ).order_by(AgreementTemplate.version.desc()))
    for milestone in db.scalars(select(Milestone).where(Milestone.agreement_id == agreement_id)):
        db.delete(milestone)
    version = _make_version(db, agreement_id, latest.template_key, payload.clauses, user_id=UUID(current_user.sub),
                            change_note=payload.change_note, version_number=latest.version + 1,
                            template_version=selected_template.version if selected_template else latest.template_version,
                            measurement_plan=payload.measurement_plan or {
                                'baseline_minutes': latest.baseline_minutes,
                                'target_reduction_pct': latest.target_pct,
                                'max_error_rate_pct': latest.error_limit_pct,
                                'min_marathi_accuracy_pct': latest.marathi_accuracy_pct,
                                'min_total_observations': latest.min_observations,
                                'min_marathi_samples': latest.min_marathi_observations,
                                'max_bandwidth_mbps': latest.bandwidth_mbps,
                                'capacity_per_day': latest.capacity_per_day,
                            })
    _create_milestones(db, agreement_id, payload.milestones, version.start_date)
    agreement.status = 'Draft'
    agreement.terms_accepted = False
    agreement.approval_chain = [{**item, 'approved': False, 'approved_at': None} for item in (agreement.approval_chain or [])]
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.version_created', 'AgreementVersion', str(version.id), f'Agreement {agreement_id} revised to v{version.version}: {payload.change_note}')
    return {'id': agreement_id, 'status': agreement.status, 'version': _version_dict(version), 'approval_chain': agreement.approval_chain}


@router.post('/{agreement_id}/approvals', tags=['Officer', 'Validator', 'Finance'])
def approve_agreement(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    if agreement.status not in {'Draft', 'Approved'}:
        raise HTTPException(status_code=409, detail='Only a draft agreement can be approved.')
    from app.core.permissions import enforce_action
    enforce_action(current_user, 'agreement.approve.named')
    chain = deepcopy(agreement.approval_chain or [])
    matching = next((item for item in chain if item['user_id'] == current_user.sub), None)
    if matching is None or matching['role'] != current_user.role:
        raise HTTPException(status_code=403, detail='You are not a matching named approver on this agreement.')
    matching['approved'] = True
    matching['approved_at'] = date.today().isoformat()
    agreement.approval_chain = chain
    all_approved = bool(chain) and all(item['approved'] for item in chain)
    invalidated = 0
    latest = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id).order_by(AgreementVersion.version.desc()))
    if not latest:
        raise HTTPException(status_code=409, detail='Agreement version is missing.')
    if all_approved:
        agreement.status = 'Approved'
        agreement.approved_by = UUID(current_user.sub)
        if latest:
            latest.approved = True
            invalidated = invalidate_current_evidence(db, agreement_id, reason='approved_measurement_plan_changed')
        for milestone in db.scalars(select(Milestone).where(Milestone.agreement_id == agreement_id)):
            milestone.lifecycle_state = 'Agreement Approved'
        lifecycle = db.get(PilotRecord, agreement_id)
        if lifecycle and lifecycle.state == 'Agreement Drafted':
            transition_pilot(db, agreement_id, 'Agreement Approved', actor=current_user.sub, role=current_user.role, reason='All named approvers completed review.')
    else:
        db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.approver_recorded', 'PilotAgreement', agreement_id,
                      f'Named approver recorded approval; all_approved={all_approved}; current_evidence_invalidated={invalidated if all_approved else 0}.')
    return {'id': agreement_id, 'status': agreement.status, 'all_approved': all_approved, 'approval_chain': chain}


@router.post('/{agreement_id}/terms', tags=['Startup Applicant'])
def accept_agreement_terms(agreement_id: str, request: TermsAcceptance, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('startup', 'agreement.accept_terms'))):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    _verify_startup_access(db, agreement, current_user)
    latest = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id).order_by(AgreementVersion.version.desc()))
    if agreement.status != 'Approved' or not latest or not latest.approved:
        raise HTTPException(status_code=409, detail='Terms can only be accepted after the current agreement version is approved.')
    if agreement.status == 'Pilot Running':
        raise HTTPException(status_code=409, detail='Terms cannot be changed after pilot start.')
    if not request.accepted:
        raise HTTPException(status_code=400, detail='Terms must be explicitly accepted or raised as a question.')
    agreement.terms_accepted = True
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.terms_accepted', 'PilotAgreement', agreement_id, 'Startup explicitly accepted the displayed agreement version.')
    return {'id': agreement_id, 'terms_accepted': True, 'status': agreement.status}


@router.post('/{agreement_id}/start', tags=['Officer'])
def start_pilot(agreement_id: str, request: PilotStartRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.approve'))):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    latest = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id).order_by(AgreementVersion.version.desc()))
    if agreement.status != 'Approved' or not latest or not latest.approved:
        raise HTTPException(status_code=409, detail='An approved agreement version is required before the pilot can start.')
    if not agreement.terms_accepted:
        raise HTTPException(status_code=409, detail='Startup must accept the agreement terms before the pilot can start.')
    try:
        lifecycle = transition_pilot(db, agreement_id, 'Pilot Running', actor=current_user.sub, role=current_user.role, reason=request.reason)
    except LifecycleError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    agreement.status = 'Pilot Running'
    for milestone in db.scalars(select(Milestone).where(Milestone.agreement_id == agreement_id)):
        milestone.lifecycle_state = 'Pilot Running'
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'pilot.started', 'PilotAgreement', agreement_id, request.reason)
    return {'id': agreement_id, 'status': agreement.status, 'lifecycle_state': lifecycle.state}


@router.get('/{agreement_id}/milestones')
def milestone_board(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    _verify_agreement_read_access(db, agreement, current_user)
    return {'agreement_id': agreement_id, 'agreement_status': agreement.status, 'milestones': _milestone_list(db, agreement_id)}


@router.get('/{agreement_id}/questions', tags=['Startup Applicant'])
def list_questions(agreement_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    if current_user.role == 'startup':
        _verify_startup_access(db, agreement, current_user)
    elif current_user.role != 'officer':
        raise HTTPException(status_code=403, detail='Only the startup and officer can view this thread.')
    messages = db.scalars(select(StartupOfficerQuestion).where(StartupOfficerQuestion.agreement_id == agreement_id).order_by(StartupOfficerQuestion.created_at)).all()
    return [{'id': str(item.id), 'author_id': str(item.author_id), 'author_role': item.author_role, 'body': item.body, 'created_at': item.created_at.isoformat()} for item in messages]


@router.post('/{agreement_id}/questions', tags=['Startup Applicant'])
def post_question(agreement_id: str, request: QuestionRequest, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(get_current_user)):
    agreement = db.get(PilotAgreement, agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail='Agreement not found.')
    if current_user.role == 'startup':
        _verify_startup_access(db, agreement, current_user)
    elif current_user.role != 'officer':
        raise HTTPException(status_code=403, detail='Only the startup and officer can post to this thread.')
    message = StartupOfficerQuestion(id=uuid4(), agreement_id=agreement_id, author_id=UUID(current_user.sub), author_role=current_user.role, body=request.body.strip())
    db.add(message); db.commit(); db.refresh(message)
    write_audit_event(db, current_user.sub, current_user.role, 'agreement.question_posted', 'StartupOfficerQuestion', str(message.id), request.body)
    return {'id': str(message.id), 'author_role': message.author_role, 'body': message.body}


@router.post('')
def approve_pilot(id: str, challenge_id: str, startup_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.approve'))):
    raise HTTPException(status_code=409, detail='Use the versioned agreement draft and approval chain before pilot approval.')


@router.post('/{id}/revise')
def revise_pilot(id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('officer', 'pilot.revise_plan'))):
    raise HTTPException(status_code=409, detail='Use the versioned agreement revision endpoint.')
