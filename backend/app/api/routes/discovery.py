"""Explainable, policy-linked applicant eligibility and capability discovery."""

import hashlib
import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit_helper import write_audit_event
from app.core.permissions import require
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.models.policy import PolicySource
from app.models.startup import ManualVerificationUpload, Startup

router = APIRouter(prefix='/api/discovery', tags=['discovery'])
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ADAPTERS = {'GeM', 'Startup India', 'DigiLocker'}

FACTOR_LABELS = {
    'capability_evidence': 'Capability evidence',
    'domain_experience': 'Domain experience',
    'language_support': 'Language support',
    'deployment_readiness': 'Deployment readiness',
}
DEMO_POLICY = {
    'source': 'PilotProof synthetic demo eligibility rules',
    'version': 'DEMO-1.0',
    'condition': 'DPIIT recognition is documented and annual turnover is at or below ₹100 lakh; any claimed relaxation requires source-linked human review.',
}
TAG_ALIASES = {
    'water': {'water', 'leak', 'quality', 'irrigation'},
    'health': {'health', 'clinic', 'diagnostic', 'patient'},
    'education': {'education', 'learning', 'school', 'attendance'},
    'mobility': {'mobility', 'transport', 'traffic', 'route'},
    'agriculture': {'agriculture', 'farm', 'crop', 'soil'},
    'public service': {'service', 'citizen', 'government', 'workflow'},
}


def _source_payload(policy: PolicySource | None) -> dict[str, str]:
    if policy:
        return {'source': policy.title, 'version': policy.version, 'condition': policy.notes or policy.policy_type}
    return DEMO_POLICY.copy()


def _eligibility(startup: Startup, sources: list[PolicySource]) -> dict:
    primary_policy = next((s for s in sources if s.policy_type in {'eligibility', 'startup_eligibility'}), None)
    source = _source_payload(primary_policy)
    rules: list[dict] = []
    exceptions: list[dict] = []

    if startup.dpiit_recognised:
        rules.append({
            'rule': 'DPIIT recognition', 'status': 'Eligible',
            'reason': 'Recognition is recorded for this synthetic startup profile.',
            'source': source['source'], 'version': source['version'],
            'condition': source['condition'], 'fix_document': None,
        })
    else:
        rules.append({
            'rule': 'DPIIT recognition', 'status': 'Needs verification',
            'reason': 'Recognition is not recorded. This is not treated as proof of ineligibility.',
            'source': source['source'], 'version': source['version'],
            'condition': source['condition'],
            'fix_document': 'Upload a current DPIIT recognition certificate or supporting registration record.',
        })

    turnover = startup.annual_turnover_lakhs
    if turnover <= 100:
        rules.append({
            'rule': 'Turnover condition', 'status': 'Eligible',
            'reason': f'Recorded annual turnover is ₹{turnover:g} lakh, within the synthetic demo threshold.',
            'source': source['source'], 'version': source['version'],
            'condition': source['condition'], 'fix_document': None,
        })
    else:
        rules.append({
            'rule': 'Turnover condition', 'status': 'Not eligible',
            'reason': f'Recorded annual turnover is ₹{turnover:g} lakh, above the synthetic demo threshold.',
            'source': source['source'], 'version': source['version'],
            'condition': source['condition'],
            'fix_document': 'Submit audited turnover evidence if the recorded figure is inaccurate; otherwise ask an officer to review any applicable relaxation.',
        })

    if startup.dpiit_recognised and turnover > 100:
        exceptions.append({
            'exception': 'Startup relaxation claim',
            'source': source['source'], 'version': source['version'],
            'condition': 'A relaxation must be supported by an applicable source and reviewed by an officer.',
            'human_review_required': True,
            'status': 'Needs verification',
        })

    statuses = {item['status'] for item in rules}
    bucket = 'Not eligible' if 'Not eligible' in statuses else 'Needs verification' if 'Needs verification' in statuses else 'Eligible'
    return {'bucket': bucket, 'rules': rules, 'exceptions': exceptions}


def _factor_breakdown(startup: Startup, query: str) -> dict[str, dict]:
    wanted = set(query.lower().replace('-', ' ').split())
    tags = {str(tag).lower() for tag in (startup.capability_tags or [])}
    if not wanted:
        wanted = TAG_ALIASES.get(startup.sector.lower(), {startup.sector.lower()})
    matched = sorted(tag for tag in tags if any(word in tag or tag in word for word in wanted))
    capability = min(100, 25 + 25 * len(matched)) if tags else 0
    experience_text = (startup.domain_experience or '').lower()
    experience = 85 if 'year' in experience_text or 'district' in experience_text or 'deployment' in experience_text else 45 if experience_text != 'not documented' else 15
    languages = startup.languages_supported or []
    language_score = min(100, 35 + 35 * sum(1 for language in languages if language.lower() in {'marathi', 'मराठी', 'english'}))
    readiness_text = (startup.deployment_readiness or '').lower()
    readiness = 90 if any(word in readiness_text for word in ('live', 'production', 'ready', 'deployed')) else 60 if 'pilot' in readiness_text else 20

    def factor(score: int, explanation: str, evidence: str | None = None) -> dict:
        return {'label': '', 'value': score, 'explanation': explanation, 'evidence': evidence}

    snippets = startup.evidence_snippets or []
    capability_evidence = next((str(snippet) for snippet in snippets if any(term in str(snippet).lower() for term in matched)), None)
    return {
        'capability_evidence': {**factor(capability, f'{len(matched)} relevant capability tag(s) matched: {", ".join(matched) if matched else "no direct tag match"}.', capability_evidence), 'label': FACTOR_LABELS['capability_evidence']},
        'domain_experience': {**factor(experience, startup.domain_experience or 'No domain experience evidence recorded.'), 'label': FACTOR_LABELS['domain_experience']},
        'language_support': {**factor(language_score, f"Documented languages: {', '.join(languages) if languages else 'none recorded'}.", 'Language claims require documentary confirmation.'), 'label': FACTOR_LABELS['language_support']},
        'deployment_readiness': {**factor(readiness, startup.deployment_readiness or 'No deployment readiness evidence recorded.'), 'label': FACTOR_LABELS['deployment_readiness']},
    }


@router.get('/startups')
def discover_startups(
    q: str = Query(default='', max_length=120),
    sector: str = '',
    eligibility: str = '',
    challenge_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(get_current_user),
) -> dict:
    statement = select(Startup)
    if current_user.role == 'startup':
        if not current_user.org_id:
            return {'items': [], 'count': 0, 'policy_sources': [], 'notice': 'No startup profile is linked to this account.'}
        try:
            own_org_id = UUID(current_user.org_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail='Invalid organization identifier on account.') from error
        statement = statement.where(Startup.organisation_id == own_org_id)
    elif current_user.role not in {'officer', 'evaluator', 'validator'}:
        raise HTTPException(status_code=403, detail='This role cannot discover applicant profiles.')
    if sector:
        statement = statement.where(func.lower(Startup.sector) == sector.lower())
    if q and db.bind and db.bind.dialect.name == 'postgresql':
        search_document = (
            func.coalesce(Startup.name, '') + ' ' + func.coalesce(Startup.sector, '')
            + ' ' + func.coalesce(Startup.domain_experience, '')
            + ' ' + cast(Startup.capability_tags, String)
        )
        searchable = func.to_tsvector(
            'simple',
            search_document,
        )
        statement = statement.where(searchable.match(q, postgresql_regconfig='simple'))
    startups = list(db.scalars(statement.order_by(Startup.name)))
    if q and (not db.bind or db.bind.dialect.name != 'postgresql'):
        terms = q.lower().split()
        startups = [startup for startup in startups if all(
            term in ' '.join([startup.name, startup.sector, startup.domain_experience or '', *[str(tag) for tag in (startup.capability_tags or [])]]).lower()
            for term in terms
        )]

    sources = list(db.scalars(select(PolicySource).order_by(PolicySource.effective_date.desc())))
    ranked = []
    for startup in startups:
        eligibility_result = _eligibility(startup, sources)
        if eligibility and eligibility_result['bucket'].lower() != eligibility.lower():
            continue
        factors = _factor_breakdown(startup, q)
        evidence = startup.evidence_snippets or []
        ranked.append({
            'id': str(startup.id), 'name': startup.name, 'city': startup.city, 'sector': startup.sector,
            'founded_year': startup.founded_year, 'turnover_lakhs': startup.annual_turnover_lakhs,
            'capability_tags': startup.capability_tags or [], 'evidence_snippets': evidence,
            'eligibility': eligibility_result, 'fit_breakdown': factors,
            'matched_evidence': [factor['evidence'] for factor in factors.values() if factor.get('evidence')],
            'synthetic': True,
        })
    ranked.sort(key=lambda item: (
        {'Eligible': 0, 'Needs verification': 1, 'Not eligible': 2}[item['eligibility']['bucket']],
        -sum(factor['value'] for factor in item['fit_breakdown'].values()),
        item['name'].lower(),
    ))
    return {
        'items': ranked,
        'count': len(ranked),
        'policy_sources': [
            {'title': source.title, 'version': source.version, 'effective_date': source.effective_date.isoformat(), 'url': source.url, 'policy_type': source.policy_type}
            for source in sources
        ] or [{'title': DEMO_POLICY['source'], 'version': DEMO_POLICY['version'], 'policy_type': 'eligibility'}],
        'notice': 'All startup profiles and fit indicators are synthetic demo data. Fit factors are evidence summaries, not a procurement decision.',
    }


@router.get('/eligibility/me')
def explain_own_eligibility(
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(get_current_user),
) -> dict:
    if current_user.role == 'startup':
        if not current_user.org_id:
            return {'items': [], 'count': 0, 'notice': 'No startup profile is linked to this account. Ask an officer to link the organization before reviewing eligibility.'}
        try:
            organisation_id = UUID(current_user.org_id)
        except ValueError as error:
            raise HTTPException(status_code=400, detail='Invalid organization identifier on account.') from error
        profiles = list(db.scalars(select(Startup).where(Startup.organisation_id == organisation_id)))
    elif current_user.role in {'officer', 'evaluator', 'validator'}:
        profiles = list(db.scalars(select(Startup).order_by(Startup.name)))
    else:
        raise HTTPException(status_code=403, detail='This role cannot view eligibility explanations.')

    sources = list(db.scalars(select(PolicySource).order_by(PolicySource.effective_date.desc())))
    items = []
    for startup in profiles:
        items.append({
            'id': str(startup.id), 'name': startup.name, 'city': startup.city, 'sector': startup.sector,
            'eligibility': _eligibility(startup, sources),
        })
    return {
        'items': items,
        'count': len(items),
        'notice': 'Eligibility explanations are source-linked synthetic demo checks. They are not an official determination.',
    }


@router.post('/startups/{startup_id}/manual-verification-upload')
async def upload_manual_verification(
    startup_id: str,
    source_adapter: str = Query(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: OIDCUserInfo = Depends(get_current_user),
) -> dict:
    if current_user.role not in {'startup', 'officer'}:
        raise HTTPException(status_code=403, detail='Only the startup or an officer can submit a manual verification document.')
    if source_adapter not in ADAPTERS:
        raise HTTPException(status_code=422, detail='Choose GeM, Startup India, or DigiLocker (simulated adapters).')
    try:
        startup_uuid = UUID(startup_id)
        uploader_uuid = UUID(current_user.sub)
    except ValueError as error:
        raise HTTPException(status_code=422, detail='Invalid startup or user identifier.') from error
    startup = db.get(Startup, startup_uuid)
    if startup is None:
        raise HTTPException(status_code=404, detail='Startup profile not found.')
    if current_user.role == 'startup' and (not current_user.org_id or str(startup.organisation_id) != current_user.org_id):
        raise HTTPException(status_code=403, detail='Startup users may only submit documents for their own organization profile.')

    contents = await document.read(MAX_UPLOAD_BYTES + 1)
    if not contents:
        raise HTTPException(status_code=400, detail='The selected document is empty.')
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail='Documents must be 5 MB or smaller.')

    safe_filename = Path((document.filename or 'supporting-document').replace('\\', '/')).name.replace('\x00', '')[:180]
    digest = hashlib.sha256(contents).hexdigest()
    upload_id = uuid4()
    upload_root = Path(os.getenv('MANUAL_UPLOAD_DIR', './uploads')).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_path = upload_root / f'{upload_id.hex}.upload'
    stored_path.write_bytes(contents)

    record = ManualVerificationUpload(
        id=upload_id,
        startup_id=startup_uuid,
        source_adapter=source_adapter,
        filename=safe_filename,
        content_type=document.content_type or 'application/octet-stream',
        sha256=digest,
        storage_path=str(stored_path),
        uploaded_by=uploader_uuid,
        status='Pending human verification',
    )
    db.add(record)
    db.commit()
    write_audit_event(db, current_user.sub, current_user.role, 'startup.manual_document_submitted', 'ManualVerificationUpload', str(upload_id), f'{source_adapter} simulated-adapter supporting file stored for human review; sha256={digest}.')
    return {
        'id': str(upload_id), 'startup_id': str(startup_uuid), 'source_adapter': source_adapter,
        'filename': safe_filename, 'sha256': digest, 'status': record.status,
        'adapter_status': 'Simulated',
        'note': 'The file is stored for manual verification. The hash detects changes; it does not prove the document is truthful.',
    }
