import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from app.core.security import create_access_token
from app.models.audit import AuditEvent
from app.models.evaluation import ConflictDeclaration, Evaluation, RubricVersion
from app.models.evidence import EvidenceFile
from app.models.startup import Startup
from app.models.challenge import Challenge
from app.models.user import User
from app.models.organisation import Organisation
from app.models.pilot import PilotAgreement
from app.models.challenge import Challenge
from app.models.startup import Application
from app.workflow.models import PilotRecord

def test_startup_cannot_publish_challenge(client, auth_headers):
    r = client.post('/api/challenges', json={
        "id": "C1", "title": "T1", "department": "D1", "district": "D1",
        "sector": "S1", "budget": 100, "target_pct": 10.0,
        "deadline": "2026-12-01", "metric": "M1", "description": "Desc"
    }, headers=auth_headers('startup'))
    assert r.status_code == 403

def test_evaluator_cannot_publish_challenge(client, auth_headers):
    r = client.post('/api/challenges', json={
        "id": "C2", "title": "T2", "department": "D2", "district": "D2",
        "sector": "S2", "budget": 100, "target_pct": 10.0,
        "deadline": "2026-12-01", "metric": "M2", "description": "Desc"
    }, headers=auth_headers('evaluator'))
    assert r.status_code == 403

def test_only_finance_can_approve_invoice(client, auth_headers):
    mid = "123e4567-e89b-12d3-a456-426614174000"
    for role in ['officer', 'startup', 'evaluator', 'validator', 'district']:
        r = client.post(f'/api/milestones/{mid}/approve-invoice', headers=auth_headers(role))
        assert r.status_code == 403

def test_unauthenticated_gets_401(client):
    r = client.get('/api/challenges')
    assert r.status_code == 200
    r = client.get('/api/audit')
    assert r.status_code == 401


def test_evaluator_with_declared_conflict_cannot_score(client, db, auth_headers):
    evaluator = db.query(User).filter_by(role='evaluator').first()
    startup = Startup(id=uuid4(), name='Conflict test (Synthetic)', city='Pune', sector='Water', founded_year=2020,
                      annual_turnover_lakhs=10, dpiit_recognised=True)
    challenge = Challenge(id='CONFLICT-CH', title='Conflict Test', department='Demo', district='Pune',
                          sector='Water', status='Open', published_by=db.query(User).filter_by(role='officer').first().id)
    db.add_all([startup, challenge]); db.flush()
    declaration = ConflictDeclaration(id=uuid4(), evaluator_id=evaluator.id, startup_id=startup.id,
                                      challenge_id=challenge.id, has_conflict=True, note='Synthetic declared conflict')
    db.add(declaration); db.commit()
    rubric = RubricVersion(id=uuid4(), challenge_id=challenge.id, version=1,
                           weights={'capability_evidence': 100},
                           criteria=[{'key': 'capability_evidence', 'label': 'Capability evidence', 'weight': 100}],
                           published_by=challenge.published_by)
    application = Application(id=uuid4(), startup_id=startup.id, challenge_id=challenge.id, status='Submitted')
    db.add_all([rubric, application]); db.commit()
    response = client.post('/api/evaluations/score', json={
        'application_id': str(application.id), 'rubric_version_id': str(rubric.id),
        'conflict_declaration_id': str(declaration.id),
        'scores': {'capability_evidence': {'score': 3, 'reason': 'Synthetic score reason.'}},
        'overall_rationale': 'A sufficiently detailed overall rationale.',
    }, headers=auth_headers('evaluator'))
    assert response.status_code == 403


def test_applicant_cannot_validate_own_evidence(client, db):
    applicant = db.query(User).filter_by(role='startup').first()
    evidence = EvidenceFile(id=uuid4(), agreement_id='OWN-EVIDENCE-AGREEMENT', agreement_version=1,
                            submitted_by=applicant.id, filename='synthetic.csv', status='Submitted')
    db.add(evidence); db.commit()
    # Use the same identity with the Validator role to prove that ownership, not just role, blocks approval.
    token = create_access_token(data={'sub': str(applicant.id), 'email': applicant.email, 'name': applicant.full_name, 'role': 'validator'})
    response = client.post(f'/api/evidence/{evidence.id}/validate', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403


def test_only_officer_can_publish_challenge(client, auth_headers):
    payload = {
        'id': f'FORBIDDEN-{uuid4().hex[:8]}', 'title': 'Synthetic challenge', 'department': 'Demo',
        'district': 'Pune', 'sector': 'Water', 'budget': 100, 'target_pct': 10.0,
        'deadline': '2026-12-01', 'metric': 'Count', 'description': 'Synthetic description',
    }
    for role in ('startup', 'evaluator', 'validator', 'finance', 'district'):
        response = client.post('/api/challenges', json=payload, headers=auth_headers(role))
        assert response.status_code == 403


def test_finance_is_only_role_that_can_approve_payment(client, auth_headers):
    milestone_id = str(uuid4())
    for role in ('officer', 'startup', 'evaluator', 'validator', 'district'):
        response = client.post(f'/api/milestones/{milestone_id}/approve-invoice', headers=auth_headers(role))
        assert response.status_code == 403


def test_audit_event_database_rows_are_append_only(client, db):
    event = AuditEvent(actor_id=None, actor_role='officer', action='test', resource_type='test',
                       resource_id='test-1', detail='synthetic', previous_hash='genesis', event_hash='a' * 64)
    db.add(event); db.commit()
    event.detail = 'changed'
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.query(AuditEvent).filter_by(resource_id='test-1').one().detail == 'synthetic'
    db.delete(db.query(AuditEvent).filter_by(resource_id='test-1').one())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.query(AuditEvent).filter_by(resource_id='test-1').count() == 1


def test_api_docs_are_available_and_grouped_by_role(client):
    docs = client.get('/api/docs')
    openapi = client.get('/api/openapi.json')
    assert docs.status_code == 200
    assert openapi.status_code == 200
    tag_names = {tag['name'] for tag in openapi.json()['tags']}
    assert {'Officer', 'Startup Applicant', 'Evaluator', 'Validator', 'Finance', 'Receiving District'} <= tag_names


def test_declared_conflict_blocks_scoring_even_with_full_rubric_payload(client, db, auth_headers):
    evaluator = db.query(User).filter_by(role='evaluator').first()
    officer = db.query(User).filter_by(role='officer').first()
    challenge = Challenge(id='SCORE-GUARD', title='Score guard', department='Demo', district='Pune', sector='Water', status='Open', published_by=officer.id)
    startup = Startup(id=uuid4(), name='Conflict Score Synthetic', city='Pune', sector='Water', founded_year=2021, annual_turnover_lakhs=10, dpiit_recognised=True)
    db.add_all([challenge, startup]); db.flush()
    application = Application(id=uuid4(), startup_id=startup.id, challenge_id=challenge.id, status='Submitted')
    rubric = RubricVersion(id=uuid4(), challenge_id=challenge.id, version=1,
                           weights={'capability_evidence': 35, 'domain_experience': 25, 'language_support': 20, 'deployment_readiness': 20},
                           criteria=[{'key': key, 'label': key, 'weight': weight} for key, weight in [('capability_evidence', 35), ('domain_experience', 25), ('language_support', 20), ('deployment_readiness', 20)]], published_by=officer.id)
    db.add_all([application, rubric]); db.commit()
    conflict_response = client.post('/api/evaluations/conflicts', json={'startup_id': str(startup.id), 'challenge_id': challenge.id, 'has_conflict': True, 'details': 'Declared prior financial relationship.'}, headers=auth_headers('evaluator'))
    assert conflict_response.status_code == 200
    declaration_id = conflict_response.json()['id']
    payload = {'application_id': str(application.id), 'rubric_version_id': str(rubric.id), 'conflict_declaration_id': declaration_id,
               'scores': {key: {'score': 4, 'reason': 'Evidence supports this rating.'} for key in rubric.weights},
               'overall_rationale': 'Synthetic overall assessment with sufficient reasoning.'}
    response = client.post('/api/evaluations/score', json=payload, headers=auth_headers('evaluator'))
    assert response.status_code == 403


def test_unapproved_agreement_cannot_start_pilot_api(client, db, auth_headers):
    officer = db.query(User).filter_by(role='officer').first()
    startup_user = db.query(User).filter_by(role='startup').first()
    startup = Startup(id=uuid4(), name='Agreement guard synthetic', city='Pune', sector='Water', founded_year=2021,
                      annual_turnover_lakhs=10, dpiit_recognised=True, organisation_id=startup_user.organisation_id)
    challenge = Challenge(id='AGREEMENT-GUARD', title='Agreement guard', department='Demo', district='Pune', sector='Water', status='Open', published_by=officer.id)
    db.add_all([startup, challenge]); db.flush()
    application = Application(id=uuid4(), startup_id=startup.id, challenge_id=challenge.id, status='Shortlisted')
    db.add(application); db.commit()
    approvals = [str(db.query(User).filter_by(role=role).first().id) for role in ('officer', 'validator', 'finance')]
    draft_payload = {'startup_id': str(startup.id), 'challenge_id': challenge.id, 'approver_user_ids': approvals}
    draft = client.post('/api/pilots/drafts', json=draft_payload, headers=auth_headers('officer'))
    assert draft.status_code == 200
    agreement_id = draft.json()['id']
    assert client.post(f'/api/pilots/{agreement_id}/start', json={'reason': 'Begin test pilot.'}, headers=auth_headers('officer')).status_code == 409
    assert db.get(PilotAgreement, agreement_id).status == 'Draft'
    assert db.get(PilotRecord, agreement_id).state == 'Agreement Drafted'


def test_shortlisted_agreement_approval_acceptance_start_path(client, db, auth_headers):
    officer = db.query(User).filter_by(role='officer').first()
    startup_user = db.query(User).filter_by(role='startup').first()
    if startup_user.organisation_id is None:
        organization = Organisation(id=uuid4(), name='Agreement Test Startup Organization', org_type='startup', district='Pune')
        db.add(organization); db.flush(); startup_user.organisation_id = organization.id
    startup = Startup(id=uuid4(), name='Full Path Synthetic', city='Pune', sector='Water', founded_year=2021,
                      annual_turnover_lakhs=10, dpiit_recognised=True, organisation_id=startup_user.organisation_id)
    challenge = Challenge(id='FULL-PATH', title='Full path', department='Demo', district='Pune', sector='Water', status='Open', published_by=officer.id)
    db.add_all([startup, challenge]); db.flush()
    db.add(Application(id=uuid4(), startup_id=startup.id, challenge_id=challenge.id, status='Shortlisted')); db.commit()
    approval_users = [db.query(User).filter_by(role=role).first() for role in ('officer', 'validator', 'finance')]
    draft = client.post('/api/pilots/drafts', json={'startup_id': str(startup.id), 'challenge_id': challenge.id,
                         'approver_user_ids': [str(user.id) for user in approval_users]}, headers=auth_headers('officer'))
    assert draft.status_code == 200
    agreement_id = draft.json()['id']
    assert len(draft.json()['milestones']) == 3
    for user in approval_users:
        token = create_access_token(data={'sub': str(user.id), 'email': user.email, 'name': user.full_name, 'role': user.role})
        approval = client.post(f'/api/pilots/{agreement_id}/approvals', headers={'Authorization': f'Bearer {token}'})
        assert approval.status_code == 200
    assert client.post(f'/api/pilots/{agreement_id}/start', json={'reason': 'Begin the approved synthetic pilot.'}, headers=auth_headers('officer')).status_code == 409
    startup_token = create_access_token(data={'sub': str(startup_user.id), 'email': startup_user.email, 'name': startup_user.full_name, 'role': startup_user.role, 'org_id': str(startup_user.organisation_id)})
    accepted = client.post(f'/api/pilots/{agreement_id}/terms', json={'accepted': True}, headers={'Authorization': f'Bearer {startup_token}'})
    assert accepted.status_code == 200, accepted.text
    started = client.post(f'/api/pilots/{agreement_id}/start', json={'reason': 'All approvals and startup acceptance are recorded.'}, headers=auth_headers('officer'))
    assert started.status_code == 200
    assert started.json()['lifecycle_state'] == 'Pilot Running'


def test_agreement_version_redline_data_preserves_each_clause_version(client, db, auth_headers):
    officer = db.query(User).filter_by(role='officer').first()
    startup_user = db.query(User).filter_by(role='startup').first()
    if startup_user.organisation_id is None:
        organization = Organisation(id=uuid4(), name='Redline Test Startup Organization', org_type='startup', district='Pune')
        db.add(organization); db.flush(); startup_user.organisation_id = organization.id
    startup = Startup(id=uuid4(), name='Redline Synthetic', city='Pune', sector='Water', founded_year=2022,
                      annual_turnover_lakhs=20, dpiit_recognised=True, organisation_id=startup_user.organisation_id)
    challenge = Challenge(id='REDLINE-CH', title='Redline test', department='Demo', district='Pune', sector='Water', status='Open', published_by=officer.id)
    db.add_all([startup, challenge]); db.flush()
    db.add(Application(id=uuid4(), startup_id=startup.id, challenge_id=challenge.id, status='Shortlisted')); db.commit()
    approvers = [db.query(User).filter_by(role=role).first() for role in ('officer', 'validator', 'finance')]
    draft = client.post('/api/pilots/drafts', json={'startup_id': str(startup.id), 'challenge_id': challenge.id,
                         'approver_user_ids': [str(user.id) for user in approvers]}, headers=auth_headers('officer'))
    assert draft.status_code == 200
    agreement_id = draft.json()['id']
    for user in approvers:
        token = create_access_token(data={'sub': str(user.id), 'email': user.email, 'name': user.full_name, 'role': user.role})
        assert client.post(f'/api/pilots/{agreement_id}/approvals', headers={'Authorization': f'Bearer {token}'}).status_code == 200
    changed_clauses = dict(draft.json()['version']['clauses'])
    changed_clauses['acceptance'] = 'Revised acceptance criteria with independent validation.'
    revised = client.post(f'/api/pilots/{agreement_id}/versions', json={'clauses': changed_clauses, 'change_note': 'Clarified validation acceptance'}, headers=auth_headers('officer'))
    assert revised.status_code == 200, revised.text
    versions = client.get(f'/api/pilots/{agreement_id}/versions', headers=auth_headers('officer')).json()
    assert [version['version'] for version in versions] == [1, 2]
    assert versions[0]['clauses']['acceptance'] != versions[1]['clauses']['acceptance']
    assert versions[0]['approved'] is True and versions[1]['approved'] is False


def test_evaluator_rubric_exposes_criteria_and_weights(client, db, auth_headers):
    officer = db.query(User).filter_by(role='officer').first()
    challenge = Challenge(id='RUBRIC-CH', title='Rubric test', department='Demo', district='Pune', sector='Water', status='Open', published_by=officer.id)
    db.add(challenge)
    db.add(RubricVersion(id=uuid4(), challenge_id=challenge.id, version=1,
                         weights={'evidence': 100}, criteria=[{'key': 'evidence', 'label': 'Evidence quality', 'weight': 100}],
                         published_by=officer.id))
    db.commit()
    response = client.get('/api/evaluations/rubrics/RUBRIC-CH', headers=auth_headers('evaluator'))
    assert response.status_code == 200
    assert response.json()['criteria'][0]['label'] == 'Evidence quality'
