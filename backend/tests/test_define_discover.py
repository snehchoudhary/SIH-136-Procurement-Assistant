from datetime import date
import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.main import app
from app.models.challenge import Challenge, ChallengeVersion
from app.models.policy import PolicySource
from app.models.startup import ManualVerificationUpload, Startup


@pytest.fixture()
def define_client(db_session):
    previous_overrides = app.dependency_overrides.copy()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: OIDCUserInfo(
        sub='123e4567-e89b-12d3-a456-426614174000',
        email='officer@example.test', name='Test Officer', role='officer',
    )
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


def test_ai_fallback_never_invents_baseline(define_client):
    response = define_client.post('/api/challenges/ai-draft', json={
        'problem_statement': 'Residents cannot report water leaks quickly.', 'input_language': 'en',
    })
    assert response.status_code == 200
    proposal = response.json()['proposal']
    assert proposal['baseline'] == 'Baseline unavailable'
    assert proposal['test_duration_days'] is None
    assert response.json()['review_required'] is True


def test_challenge_draft_requires_officer_approval_and_locks_after_publish(define_client, db_session):
    payload = {
        'challenge_id': 'CH-TEST-1', 'title': 'Water reporting improvement',
        'problem_statement': 'Residents currently wait too long to report local water service issues.',
        'department': 'Demo Department', 'district': 'Pune', 'sector': 'Water',
        'outcomes': ['Make reporting easier'], 'metrics': ['Time from report to acknowledgement'],
        'baseline': 'Baseline unavailable', 'test_plan': 'Run a supervised ward-level pilot.',
        'acceptance_criteria': ['A named reviewer can trace each submitted measurement.'],
        'input_language': 'en',
    }
    created = define_client.post('/api/challenges/draft', json=payload)
    assert created.status_code == 200
    assert created.json()['version']['version'] == 1

    denied = define_client.post('/api/challenges/CH-TEST-1/publish', json={'officer_approved': False})
    assert denied.status_code == 400

    published = define_client.post('/api/challenges/CH-TEST-1/publish', json={'officer_approved': True})
    assert published.status_code == 200
    assert published.json()['measurement_locked'] is True

    edit = define_client.put('/api/challenges/CH-TEST-1/draft', json=payload)
    assert edit.status_code == 409

    new_version = define_client.post('/api/challenges/CH-TEST-1/versions', json={**payload, 'change_note': 'Update metric definition'})
    assert new_version.status_code == 200
    assert new_version.json()['version']['version'] == 2
    versions = define_client.get('/api/challenges/CH-TEST-1/versions')
    assert [item['version'] for item in versions.json()] == [1, 2]
    assert db_session.scalar(select(Challenge).where(Challenge.id == 'CH-TEST-1')).measurement_locked is True
    assert db_session.scalar(select(ChallengeVersion).where(ChallengeVersion.version == 2)).change_note == 'Update metric definition'


def test_published_measurement_plan_requires_outcomes_and_acceptance(define_client):
    payload = {
        'challenge_id': 'CH-TEST-2', 'title': 'Safe challenge title',
        'problem_statement': 'A sufficiently detailed public service issue description.',
        'outcomes': [], 'metrics': [], 'baseline': 'Baseline unavailable', 'acceptance_criteria': [],
    }
    created = define_client.post('/api/challenges/draft', json=payload)
    assert created.status_code == 200
    response = define_client.post('/api/challenges/CH-TEST-2/publish', json={'officer_approved': True})
    assert response.status_code == 400


def test_discovery_separates_eligibility_buckets_and_explains_rules(define_client, db_session):
    source = PolicySource(
        id=uuid4(), title='Synthetic eligibility rules', jurisdiction='Demo', version='SYN-3',
        effective_date=date(2026, 1, 1), url='https://example.invalid/policy', policy_type='eligibility',
        notes='Synthetic condition: recognition and turnover are checked separately.',
    )
    db_session.add(source)
    profiles = [
        Startup(id=uuid4(), name='Eligible Synthetic Co', city='Pune', sector='Water', founded_year=2021,
                annual_turnover_lakhs=45, dpiit_recognised=True, capability_tags=['water sensing'],
                domain_experience='One district deployment', languages_supported=['Marathi'],
                deployment_readiness='Pilot ready', evidence_snippets=['Synthetic evidence: water sensing pilot log.']),
        Startup(id=uuid4(), name='Verify Synthetic Co', city='Nashik', sector='Health', founded_year=2022,
                annual_turnover_lakhs=60, dpiit_recognised=False, capability_tags=['clinic workflow'],
                domain_experience='Not documented', languages_supported=[], deployment_readiness='Prototype', evidence_snippets=[]),
        Startup(id=uuid4(), name='Over Threshold Synthetic Co', city='Nagpur', sector='Water', founded_year=2018,
                annual_turnover_lakhs=200, dpiit_recognised=False, capability_tags=['water services'],
                domain_experience='Not documented', languages_supported=[], deployment_readiness='Not documented', evidence_snippets=[]),
    ]
    db_session.add_all(profiles)
    db_session.commit()

    response = define_client.get('/api/discovery/startups')
    assert response.status_code == 200
    items = response.json()['items']
    by_name = {item['name']: item for item in items}
    assert by_name['Eligible Synthetic Co']['eligibility']['bucket'] == 'Eligible'
    assert by_name['Verify Synthetic Co']['eligibility']['bucket'] == 'Needs verification'
    ineligible = by_name['Over Threshold Synthetic Co']['eligibility']
    assert ineligible['bucket'] == 'Not eligible'
    turnover_rule = next(rule for rule in ineligible['rules'] if rule['rule'] == 'Turnover condition')
    assert turnover_rule['source'] == 'Synthetic eligibility rules'
    assert turnover_rule['version'] == 'SYN-3'
    assert turnover_rule['fix_document']
    assert set(by_name['Eligible Synthetic Co']['fit_breakdown']) == {
        'capability_evidence', 'domain_experience', 'language_support', 'deployment_readiness',
    }


def test_manual_adapter_upload_is_stored_as_pending_human_verification(define_client, db_session, tmp_path, monkeypatch):
    monkeypatch.setenv('MANUAL_UPLOAD_DIR', str(tmp_path))
    startup = Startup(
        id=uuid4(), name='Upload Test Synthetic', city='Pune', sector='Water', founded_year=2022,
        annual_turnover_lakhs=12, dpiit_recognised=True, capability_tags=[], domain_experience='Not documented',
        languages_supported=[], deployment_readiness='Prototype', evidence_snippets=[],
    )
    db_session.add(startup)
    db_session.commit()

    response = define_client.post(
        f'/api/discovery/startups/{startup.id}/manual-verification-upload',
        params={'source_adapter': 'DigiLocker'},
        files={'document': ('certificate.pdf', b'synthetic document content', 'application/pdf')},
    )
    assert response.status_code == 200
    body = response.json()
    assert body['adapter_status'] == 'Simulated'
    assert body['status'] == 'Pending human verification'
    assert body['sha256'] == hashlib.sha256(b'synthetic document content').hexdigest()
    stored = db_session.query(ManualVerificationUpload).one()
    assert stored.filename == 'certificate.pdf'
    assert stored.status == 'Pending human verification'
