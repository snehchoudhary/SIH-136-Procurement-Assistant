import io
import json
from uuid import uuid4
from datetime import date

import pytest
from sqlalchemy import ColumnDefault

from app.core.security import create_access_token
from app.models.challenge import Challenge
from app.models.evidence_verification import EvidenceUpload, EvidenceVersion2, KPIResult2, ValidatorDecision, EvidenceReviewThread
from app.models.organisation import Organisation
from app.models.pilot import AgreementVersion, Milestone, PilotAgreement
from app.models.startup import Startup
from app.models.user import User
from app.services.evidence_engine import generate_demo_datasets, get_claimed_values_for_demo


@pytest.fixture
def evidence_fixture(db):
    startup_user = db.query(User).filter_by(role='startup').first()
    validator_user = db.query(User).filter_by(role='validator').first()
    officer = db.query(User).filter_by(role='officer').first()
    if startup_user.organisation_id is None:
        organization = Organisation(id=uuid4(), name=f'Synthetic Evidence Org {uuid4()}', org_type='startup')
        db.add(organization)
        db.flush()
        startup_user.organisation_id = organization.id
    startup = Startup(id=uuid4(), name='Evidence Demo Startup (Synthetic)', city='Pune', sector='Public service',
        founded_year=2022, annual_turnover_lakhs=20, dpiit_recognised=True, organisation_id=startup_user.organisation_id)
    challenge = Challenge(id=f'EV-{uuid4().hex[:8]}', title='Evidence engine test', department='Demo', district='Pune',
        sector='Public service', status='Open', published_by=officer.id)
    db.add_all([startup, challenge]); db.flush()
    agreement = PilotAgreement(id=f'evidence-{uuid4()}', challenge_id=challenge.id, startup_id=startup.id,
        status='Approved', approved_by=officer.id, created_by=officer.id, terms_accepted=True, approval_chain=[])
    db.add(agreement); db.flush()
    db.add(AgreementVersion(agreement_id=agreement.id, version=1, baseline_minutes=45, target_pct=30,
        error_limit_pct=5, marathi_accuracy_pct=85, min_observations=100, min_marathi_observations=30,
        bandwidth_mbps=2, capacity_per_day=100, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        revised_by=officer.id, approved=True))
    milestone = Milestone(agreement_id=agreement.id, code='M1', title='Evidence', amount=1, status='Pending',
        evidence_requirements=[], acceptance_criteria=[], linked_kpis=[], lifecycle_state='Pilot Running')
    db.add(milestone); db.commit()
    return db, startup_user, validator_user, agreement, milestone


def _headers(user, role=None):
    token = create_access_token(data={'sub': str(user.id), 'email': user.email, 'name': user.full_name,
        'role': role or user.role, 'org_id': str(user.organisation_id) if user.organisation_id else None})
    return {'Authorization': f'Bearer {token}'}


def _upload(client, headers, agreement_id, scenario):
    content = generate_demo_datasets()[scenario].encode()
    claims = get_claimed_values_for_demo(scenario)
    return client.post('/api/v2/evidence/upload', headers=headers,
        data={'agreement_id': agreement_id, 'claimed_values': json.dumps(claims)},
        files={'file': ('evidence.csv', io.BytesIO(content), 'text/csv')})


def test_upload_versions_marks_old_results_stale_and_can_correct_and_accept(client, evidence_fixture):
    db, startup, validator, agreement, milestone = evidence_fixture
    first = _upload(client, _headers(startup), agreement.id, 'hero_problematic')
    assert first.status_code == 200, first.text
    hero = first.json()
    assert hero['kpi_results'][0]['claimed_value'] == 40.0
    assert hero['kpi_results'][0]['recomputed_value'] < 30
    assert hero['overall_outcome'] == 'missing_evidence'
    assert hero['milestone_status'] == 'Pending'
    assert db.get(Milestone, milestone.id).status == 'Pending'
    assert db.query(KPIResult2).filter_by(upload_id=hero['upload_id']).count() == 4

    blocked = client.post(f"/api/v2/evidence/{hero['upload_id']}/decision", headers=_headers(validator), json={'action': 'accepted'})
    assert blocked.status_code == 409
    requested = client.post(f"/api/v2/evidence/{hero['upload_id']}/decision", headers=_headers(validator),
        json={'action': 'correction_requested', 'reason': 'Please include every failed case and expand the Marathi sample.'})
    assert requested.status_code == 200, requested.text
    assert db.query(EvidenceReviewThread).filter_by(upload_id=hero['upload_id']).count() == 1
    db.expire_all()
    assert db.get(Milestone, milestone.id).lifecycle_state == 'Correction Requested'

    second = _upload(client, _headers(startup), agreement.id, 'corrected_resubmission')
    assert second.status_code == 200, second.text
    corrected = second.json()
    assert corrected['previous_version_marked_stale'] is True
    assert all(k['outcome'] == 'passed' for k in corrected['kpi_results'])
    assert all(k.is_stale for k in db.query(KPIResult2).filter_by(upload_id=hero['upload_id']).all())
    accepted = client.post(f"/api/v2/evidence/{corrected['upload_id']}/decision", headers=_headers(validator), json={'action': 'accepted'})
    assert accepted.status_code == 200, accepted.text
    db.expire_all()
    assert db.get(Milestone, milestone.id).lifecycle_state == 'Validated'


def test_v2_backend_forbids_applicant_from_validating_own_upload(client, evidence_fixture):
    db, applicant, _, agreement, _ = evidence_fixture
    upload = _upload(client, _headers(applicant), agreement.id, 'corrected_resubmission')
    assert upload.status_code == 200, upload.text
    response = client.post(f"/api/v2/evidence/{upload.json()['upload_id']}/decision",
        headers=_headers(applicant, role='validator'), json={'action': 'accepted'})
    assert response.status_code == 403


def test_dispute_and_correction_require_a_reason(client, evidence_fixture):
    _, startup, validator, agreement, _ = evidence_fixture
    upload = _upload(client, _headers(startup), agreement.id, 'hero_problematic')
    assert upload.status_code == 200, upload.text
    response = client.post(f"/api/v2/evidence/{upload.json()['upload_id']}/decision",
        headers=_headers(validator), json={'action': 'disputed', 'reason': 'No'})
    assert response.status_code == 400


def test_latest_upload_endpoint_returns_flagged_rows_and_saved_calculation_code(client, evidence_fixture):
    _, startup, validator, agreement, _ = evidence_fixture
    uploaded = _upload(client, _headers(startup), agreement.id, 'hero_problematic')
    assert uploaded.status_code == 200, uploaded.text
    latest = client.get(f'/api/v2/evidence/agreement/{agreement.id}/latest', headers=_headers(validator))
    assert latest.status_code == 200, latest.text
    body = latest.json()
    assert body['upload_id'] == uploaded.json()['upload_id']
    assert len(body['rows']) == body['row_count']
    assert any(row['_flagged'] for row in body['rows'])
    assert "df['processing_time_after'].median()" in body['kpi_results'][0]['python_code']
    assert body['overall_outcome'] == 'missing_evidence'


def test_approving_changed_measurement_plan_marks_current_evidence_stale(client, evidence_fixture, auth_headers):
    from app.services.evidence_invalidation import invalidate_current_evidence
    from app.services.evidence_invalidation import measurement_plan_fingerprint, measurement_plan_for_version, comparable_measurement_plan

    db, startup, validator, agreement, _ = evidence_fixture
    uploaded = _upload(client, _headers(startup), agreement.id, 'corrected_resubmission')
    assert uploaded.status_code == 200, uploaded.text
    upload_id = uploaded.json()['upload_id']
    accepted = client.post(f'/api/v2/evidence/{upload_id}/decision', headers=_headers(validator), json={'action': 'accepted'})
    assert accepted.status_code == 200, accepted.text
    previous_version = db.query(AgreementVersion).filter_by(agreement_id=agreement.id, version=1).one()
    prior_fingerprint = measurement_plan_fingerprint(measurement_plan_for_version(previous_version))
    evidence_version = db.query(EvidenceVersion2).filter_by(upload_id=upload_id).one()
    # Exact same fingerprint is what upload persisted.
    assert evidence_version.metric_definition_hash == prior_fingerprint
    previous_version.approved = False
    evidence_snapshot = dict(evidence_version.measurement_plan_snapshot)
    evidence_snapshot.pop('calculator_version', None)
    expected_previous = measurement_plan_fingerprint(evidence_snapshot)
    assert expected_previous == evidence_version.metric_definition_hash
    changed_version = AgreementVersion(agreement_id=agreement.id, version=2, baseline_minutes=45,
        target_pct=40, error_limit_pct=5, marathi_accuracy_pct=85, min_observations=100,
        min_marathi_observations=30, bandwidth_mbps=2, capacity_per_day=100,
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), revised_by=previous_version.revised_by,
        approved=True)
    db.add(changed_version)
    db.flush()
    assert measurement_plan_fingerprint(measurement_plan_for_version(changed_version)) != evidence_version.metric_definition_hash
    invalidated = invalidate_current_evidence(db, agreement.id, reason='approved_measurement_plan_changed')
    db.commit()
    assert invalidated == 1
    assert evidence_version.is_current is False
    assert all(result.is_stale for result in db.query(KPIResult2).filter_by(upload_id=upload_id).all())
