"""Receiving-district transfer checks with a reproducible what-if preview."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit_helper import write_audit_event
from app.core.permissions import require
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.evidence_verification import EvidenceUpload, EvidenceVersion2
from app.models.pilot import AgreementVersion, Milestone, PilotAgreement
from app.models.transfer import DistrictProfile, TransferAssessment

router = APIRouter(prefix='/api/transfer', tags=['Receiving District'])
DECISIONS = {'Evidence reusable', 'Additional test needed', 'Not demonstrated'}


class DistrictInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    district_type: str = 'Rural'
    daily_case_volume: int = Field(ge=0)
    bandwidth_mbps: float = Field(ge=0)
    primary_language: str = 'Marathi'
    language_mix: dict[str, float] = Field(default_factory=dict)
    infrastructure: list[str] = Field(default_factory=list)
    staffing_level: int = Field(default=0, ge=0)
    security_requirements: list[str] = Field(default_factory=list)
    product_version: str = 'unknown'
    notes: str | None = None
    simulated: bool = False


class AssessmentInput(BaseModel):
    agreement_id: str
    district_id: str
    procurement_route_status: str = 'Not assessed'
    procurement_note: str = ''


class PreviewInput(BaseModel):
    agreement_id: str = 'demo-agreement'
    district_id: str | None = None
    bandwidth_mbps: float = Field(ge=0)
    daily_case_volume: int | None = Field(default=None, ge=0)
    language_mix: dict[str, float] | None = None
    infrastructure: list[str] | None = None
    staffing_level: int | None = Field(default=None, ge=0)
    security_requirements: list[str] | None = None
    product_version: str | None = None
    included_evidence: dict[str, bool] = Field(default_factory=dict)


def _context(db: Session, agreement_id: str, profile: DistrictProfile | None = None) -> tuple[dict, dict]:
    agreement = db.get(PilotAgreement, agreement_id)
    plan = db.scalar(select(AgreementVersion).where(AgreementVersion.agreement_id == agreement_id,
        AgreementVersion.approved.is_(True)).order_by(AgreementVersion.version.desc()))
    if agreement is None or plan is None:
        raise HTTPException(404, detail='Approved pilot agreement was not found.')
    upload = db.scalar(select(EvidenceUpload).join(EvidenceVersion2, EvidenceVersion2.upload_id == EvidenceUpload.id)
        .where(EvidenceUpload.pilot_agreement_id == agreement_id, EvidenceVersion2.is_current.is_(True))
        .order_by(EvidenceVersion2.version_number.desc()))
    source = {
        'agreement_id': agreement_id, 'version': plan.version, 'capacity_per_day': plan.capacity_per_day,
        'bandwidth_mbps': plan.bandwidth_mbps, 'min_observations': plan.min_observations,
        'min_marathi_observations': plan.min_marathi_observations,
        **(plan.clauses or {}),
    }
    if upload:
        try:
            frame = pd.read_csv(upload.file_path)
            if 'language' in frame.columns:
                counts = frame['language'].dropna().astype(str).str.strip().value_counts()
                total = int(counts.sum()) or 1
                source['language_mix'] = {key: float(value / total) for key, value in counts.items()}
                source['language_sample_counts'] = {key: int(value) for key, value in counts.items()}
            source['evidence_version'] = int(db.scalar(select(EvidenceVersion2.version_number).where(EvidenceVersion2.upload_id == upload.id)) or 0)
            source['evidence_upload_id'] = upload.id
        except Exception:
            source['language_mix'] = {}
    source.setdefault('language_mix', {})
    receiving = ({'name': profile.name, 'daily_case_volume': profile.daily_case_volume,
        'bandwidth_mbps': profile.bandwidth_mbps, 'primary_language': profile.primary_language,
        'language_mix': profile.language_mix or {profile.primary_language: 1.0},
        'infrastructure': profile.infrastructure or [], 'staffing_level': profile.staffing_level,
        'security_requirements': profile.security_requirements or [], 'product_version': profile.product_version}
        if profile else {})
    return source, receiving


def _evaluate(source: dict, receiving: dict, included: dict[str, bool] | None = None) -> dict:
    included = included or {}
    findings: list[dict[str, Any]] = []

    def add(dimension: str, decision: str, reason: str, test: str | None = None):
        findings.append({'dimension': dimension, 'decision': decision, 'reason': reason, 'additional_test': test})

    volume = int(receiving.get('daily_case_volume', 0))
    capacity = int(source.get('capacity_per_day', 0))
    if included.get('load', True) is False:
        add('load', 'Not demonstrated', 'The load evidence row is excluded from this what-if run.')
    elif capacity <= 0:
        add('load', 'Not demonstrated', 'The locked pilot plan does not record a tested daily capacity.')
    elif volume <= capacity:
        add('load', 'Evidence reusable', f'Receiving load is {volume:,}/day, within the tested {capacity:,}/day capacity.')
    else:
        add('load', 'Additional test needed', f'Receiving load {volume:,}/day exceeds the demonstrated {capacity:,}/day.', 'Higher-volume load test')

    bandwidth = float(receiving.get('bandwidth_mbps', 0))
    tested_bandwidth = float(source.get('bandwidth_mbps', 0))
    if included.get('connectivity', True) is False:
        add('connectivity', 'Not demonstrated', 'Connectivity evidence is excluded from this what-if run.')
    elif tested_bandwidth <= 0:
        add('connectivity', 'Not demonstrated', 'The locked pilot plan has no recorded connectivity baseline.')
    elif bandwidth >= tested_bandwidth:
        add('connectivity', 'Evidence reusable', f'{bandwidth:g} Mbps meets the tested minimum of {tested_bandwidth:g} Mbps.')
    else:
        add('connectivity', 'Additional test needed', f'{bandwidth:g} Mbps is below the demonstrated {tested_bandwidth:g} Mbps pilot condition.', 'Low-bandwidth retest')

    tested_languages = source.get('language_mix') or {}
    receiving_languages = receiving.get('language_mix') or {receiving.get('primary_language', ''): 1.0}
    untested_languages = [lang for lang, share in receiving_languages.items() if float(share) > 0 and lang not in tested_languages]
    if included.get('language', True) is False or not tested_languages:
        add('language', 'Not demonstrated', 'The pilot record does not demonstrate this receiving language mix.')
    elif untested_languages:
        add('language', 'Additional test needed', f"Receiving mix includes untested language(s): {', '.join(untested_languages)}.", 'Language-mix accuracy test')
    else:
        small = [lang for lang, share in receiving_languages.items()
                 if float(share) >= .1 and int(source.get('language_sample_counts', {}).get(lang, 0)) < int(source.get('min_marathi_observations', 30))]
        if small:
            add('language', 'Additional test needed', f"{', '.join(small)} has fewer than {source.get('min_marathi_observations', 30)} source observations.", 'Segment sample-size retest')
        else:
            add('language', 'Evidence reusable', 'Every language in the receiving mix is represented in the pilot evidence at the locked minimum sample size.')

    comparisons = (
        ('infrastructure', 'infrastructure', 'infrastructure', 'Infrastructure compatibility test'),
        ('staffing', 'staffing_level', 'staffing_level', 'Staffing workflow test'),
        ('security', 'security_requirements', 'security_requirements', 'Security requirements review'),
    )
    for dimension, recv_key, source_key, test in comparisons:
        source_key = {'staffing': 'demonstrated_staffing_level', 'security': 'demonstrated_security_requirements'}.get(dimension, f'demonstrated_{dimension}')
        demonstrated = source.get(source_key)
        current = receiving.get(recv_key) or []
        if included.get(dimension, True) is False or demonstrated is None:
            add(dimension, 'Not demonstrated', f'The pilot record does not document demonstrated {dimension} conditions.')
        elif dimension == 'infrastructure':
            missing = sorted(set(current) - set(demonstrated))
            if missing: add(dimension, 'Additional test needed', f"Receiving site needs infrastructure not covered in the pilot: {', '.join(missing)}.", test)
            else: add(dimension, 'Evidence reusable', 'Receiving infrastructure is covered by the documented pilot setup.')
        elif dimension == 'staffing':
            if int(current or 0) < int(demonstrated): add(dimension, 'Additional test needed', f'Receiving staffing ({current}) is below the demonstrated minimum ({demonstrated}).', test)
            else: add(dimension, 'Evidence reusable', f'Receiving staffing meets the demonstrated minimum of {demonstrated}.')
        else:
            missing = sorted(set(current) - set(demonstrated))
            if missing: add(dimension, 'Additional test needed', f"Receiving security requirements are not covered: {', '.join(missing)}.", test)
            else: add(dimension, 'Evidence reusable', 'Receiving security requirements are covered by the pilot record.')

    source_version = source.get('product_version')
    target_version = receiving.get('product_version')
    if included.get('product_version', True) is False or not source_version:
        add('product_version', 'Not demonstrated', 'The pilot record does not identify the version used for its evidence.')
    elif target_version != source_version:
        add('product_version', 'Additional test needed', f'Receiving product version {target_version} differs from tested version {source_version}.', 'Version regression test')
    else:
        add('product_version', 'Evidence reusable', f'Both pilot and receiving district use version {source_version}.')

    outcomes = {item['decision'] for item in findings}
    overall = 'Not demonstrated' if 'Not demonstrated' in outcomes else ('Additional test needed' if 'Additional test needed' in outcomes else 'Evidence reusable')
    return {'findings': findings, 'technical_suitability': overall,
            'additional_tests': list(dict.fromkeys(item['additional_test'] for item in findings if item['additional_test']))}


@router.get('/districts')
def list_districts(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('transfer.assess'))):
    items = db.scalars(select(DistrictProfile).order_by(DistrictProfile.name)).all()
    if not items:
        item = DistrictProfile(name='Gadchiroli', district_type='Rural', daily_case_volume=120,
            bandwidth_mbps=2.0, primary_language='Marathi', language_mix={'Marathi': .78, 'Hindi': .15, 'Gondi': .07},
            infrastructure=['desktop', '4g'], staffing_level=4, security_requirements=['role-based access'],
            product_version='v1.0', notes='Synthetic receiving-district scenario.', simulated=True)
        db.add(item); db.commit(); db.refresh(item); items = [item]
    return [{'id': str(x.id), 'name': x.name, 'district_type': x.district_type,
        'daily_case_volume': x.daily_case_volume, 'bandwidth_mbps': x.bandwidth_mbps,
        'primary_language': x.primary_language, 'language_mix': x.language_mix,
        'infrastructure': x.infrastructure, 'staffing_level': x.staffing_level,
        'security_requirements': x.security_requirements, 'product_version': x.product_version,
        'simulated': x.simulated} for x in items]


@router.post('/districts')
def create_district(payload: DistrictInput, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('transfer.profile.manage'))):
    item = DistrictProfile(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return {'id': str(item.id), 'name': item.name}


@router.post('/assess')
def assess_transfer(payload: AssessmentInput, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('transfer.assess'))):
    try: profile = db.get(DistrictProfile, UUID(payload.district_id))
    except ValueError as exc: raise HTTPException(404, detail='Receiving district not found.') from exc
    if profile is None: raise HTTPException(404, detail='Receiving district not found.')
    source, receiving = _context(db, payload.agreement_id, profile)
    result = _evaluate(source, receiving)
    assessment = TransferAssessment(agreement_id=payload.agreement_id, receiving_district_id=profile.id,
        assessed_by=UUID(current_user.sub), status=result['technical_suitability'], findings=result['findings'],
        procurement_note=payload.procurement_note, technical_suitability=result['technical_suitability'],
        procurement_route_status=payload.procurement_route_status, source_snapshot=source,
        receiving_snapshot=receiving, created_milestone_ids=[])
    db.add(assessment); db.commit(); db.refresh(assessment)
    write_audit_event(db, current_user.sub, current_user.role, 'transfer.assessed', 'TransferAssessment', str(assessment.id),
        f"Technical suitability: {assessment.technical_suitability}; procurement route: {assessment.procurement_route_status} (separate assessment).")
    return {'id': str(assessment.id), 'agreement_id': assessment.agreement_id, 'district': receiving,
        'source': source, **result, 'procurement_route_status': assessment.procurement_route_status,
        'procurement_note': assessment.procurement_note, 'created_milestone_ids': []}


@router.post('/assess/preview')
def preview_transfer(payload: PreviewInput, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('transfer.assess'))):
    profile = None
    if payload.district_id:
        try: profile = db.get(DistrictProfile, UUID(payload.district_id))
        except ValueError as exc: raise HTTPException(404, detail='Receiving district not found.') from exc
        if profile is None: raise HTTPException(404, detail='Receiving district not found.')
    source, receiving = _context(db, payload.agreement_id, profile)
    if profile is None:
        receiving = {'name': 'Gadchiroli', 'daily_case_volume': 120, 'bandwidth_mbps': 2,
            'primary_language': 'Marathi', 'language_mix': {'Marathi': .78, 'Hindi': .15, 'Gondi': .07},
            'infrastructure': ['desktop', '4g'], 'staffing_level': 4,
            'security_requirements': ['role-based access'], 'product_version': 'v1.0'}
    receiving.update({'bandwidth_mbps': payload.bandwidth_mbps})
    if payload.daily_case_volume is not None: receiving['daily_case_volume'] = payload.daily_case_volume
    for key in ('language_mix', 'infrastructure', 'staffing_level', 'security_requirements', 'product_version'):
        value = getattr(payload, key)
        if value is not None: receiving[key] = value
    return {'source': source, 'receiving': receiving, **_evaluate(source, receiving, payload.included_evidence),
        'procurement_route_status': 'Not assessed',
        'notice': 'Technical suitability does not approve a procurement route.'}


@router.get('/assessments')
def list_assessments(db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('transfer.assess'))):
    items = db.scalars(select(TransferAssessment).order_by(TransferAssessment.assessed_at.desc())).all()
    return [{'id': str(item.id), 'agreement_id': item.agreement_id,
        'district_id': str(item.receiving_district_id), 'status': item.status,
        'technical_suitability': item.technical_suitability,
        'procurement_route_status': item.procurement_route_status,
        'findings': item.findings, 'created_milestone_ids': item.created_milestone_ids}
        for item in items]


@router.post('/assessments/{assessment_id}/create-tests')
def create_tests(assessment_id: str, db: Session = Depends(get_db), current_user: OIDCUserInfo = Depends(require('pilot.revise_plan'))):
    try: assessment = db.get(TransferAssessment, UUID(assessment_id))
    except ValueError as exc: raise HTTPException(404, detail='Assessment not found.') from exc
    if assessment is None: raise HTTPException(404, detail='Assessment not found.')
    created = []
    existing = set(assessment.created_milestone_ids or [])
    already_created = set(db.scalars(select(Milestone.title).where(
        Milestone.agreement_id == assessment.agreement_id,
        Milestone.note.contains(f'transfer assessment {assessment_id}'))).all())
    for index, test in enumerate(dict.fromkeys(f['additional_test'] for f in assessment.findings if f.get('additional_test')), 1):
        if test in already_created: continue
        row = Milestone(agreement_id=assessment.agreement_id, code=f'SCALE-{uuid4().hex[:6].upper()}',
            title=test, amount=0, status='Pending', note=f"Created from transfer assessment {assessment_id}.",
            evidence_requirements=[test], acceptance_criteria=['Receiving-district test evidence reviewed'],
            linked_kpis=[], lifecycle_state='Agreement Approved', updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
        db.add(row); db.flush(); created.append({'id': str(row.id), 'title': row.title})
        existing.add(str(row.id))
        already_created.add(test)
    assessment.created_milestone_ids = sorted(existing)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'transfer.tests_created', 'TransferAssessment', assessment_id,
        f'{len(created)} receiving-district test milestone(s) created.')
    return {'created': created, 'created_milestone_ids': [row['id'] for row in created]}
