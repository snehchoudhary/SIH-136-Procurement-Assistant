from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy import text

from app.api.deps import get_current_user
from app.core.security import OIDCUserInfo
from app.db.session import get_db
from app.main import app
from app.workflow.engine import (
    LIFECYCLE_STATES,
    LifecycleError,
    create_pilot,
    initiate_payment,
    transition_pilot,
    update_kpi,
    verify_audit_chain,
)
from app.workflow.models import AuditEvent, PaymentAttempt, PilotRecord
from app.core.audit_helper import verify_record_audit_chain, write_audit_event
from app.models.audit import AuditEvent as RecordAuditEvent
from app.core.permissions import LIFECYCLE_TRANSITION_ACTIONS, POLICY, enforce_action


@pytest.fixture()
def client(db_session):
    previous_overrides = app.dependency_overrides.copy()
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: OIDCUserInfo(
        sub='test-officer', email='officer@example.test', name='Test Officer', role='officer'
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


def _create(db_session, pilot_id='P-1'):
    return create_pilot(db_session, pilot_id, actor='Tester', role='Officer')


def test_lifecycle_declares_all_required_main_states():
    assert LIFECYCLE_STATES == (
        'Draft', 'Published', 'Applications Open', 'Evaluating', 'Shortlisted',
        'Agreement Drafted', 'Agreement Approved', 'Pilot Running', 'Evidence Submitted',
        'Validated', 'Accepted', 'Invoice Approved', 'Payment Initiated',
        'Payment Confirmed', 'Scale-up Review', 'Decision Recorded',
    )


def test_standard_lifecycle_can_advance_in_order(db_session):
    pilot = _create(db_session)
    for state in LIFECYCLE_STATES[1:]:
        pilot = transition_pilot(db_session, pilot.id, state, actor='Reviewer', role='Officer')
    assert pilot.state == 'Decision Recorded'
    assert pilot.agreement_approved is True


def test_transition_guard_rejects_skipped_or_unknown_state(db_session):
    _create(db_session)
    with pytest.raises(LifecycleError, match='not allowed'):
        transition_pilot(db_session, 'P-1', 'Validated', actor='A', role='Officer')
    with pytest.raises(LifecycleError, match='Unknown lifecycle state'):
        transition_pilot(db_session, 'P-1', 'Unknown', actor='A', role='Officer')


def test_pilot_cannot_start_before_approved_agreement(db_session):
    _create(db_session)
    for state in ('Published', 'Applications Open', 'Evaluating', 'Shortlisted', 'Agreement Drafted'):
        transition_pilot(db_session, 'P-1', state, actor='A', role='Officer')
    with pytest.raises(LifecycleError, match='approved agreement'):
        transition_pilot(db_session, 'P-1', 'Pilot Running', actor='A', role='Officer')
    transition_pilot(db_session, 'P-1', 'Agreement Approved', actor='A', role='Officer')
    assert transition_pilot(db_session, 'P-1', 'Pilot Running', actor='A', role='Officer').state == 'Pilot Running'


@pytest.mark.parametrize('side_state', ['Disputed', 'Correction Requested'])
def test_reason_is_required_for_dispute_and_correction(db_session, side_state):
    _create(db_session)
    transition_pilot(db_session, 'P-1', 'Published', actor='A', role='Officer')
    with pytest.raises(LifecycleError, match='reason is required'):
        transition_pilot(db_session, 'P-1', side_state, actor='A', role='Officer')
    assert transition_pilot(db_session, 'P-1', side_state, actor='A', role='Officer', reason='Evidence needs review').state == side_state


def test_kpi_change_increments_version_and_marks_dependent_results_stale(db_session):
    _create(db_session)
    pilot = update_kpi(db_session, 'P-1', actor='Officer A', role='Officer', reason='Clarified response-time measurement')
    assert pilot.kpi_version == 2
    assert pilot.result_status == 'Stale, re-review needed'
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.event_type == 'kpi_changed'))
    assert event is not None
    assert event.before_state == 'KPI v1; results Current'
    assert event.after_state == 'KPI v2; results Stale, re-review needed'


def test_payment_retries_with_same_idempotency_key_return_original_record(db_session):
    pilot = _create(db_session)
    for state in LIFECYCLE_STATES[1:12]:
        pilot = transition_pilot(db_session, pilot.id, state, actor='Reviewer', role='Officer')
    first = initiate_payment(db_session, 'P-1', 'retry-token-1', actor='Finance', role='finance')
    retry = initiate_payment(db_session, 'P-1', 'retry-token-1', actor='Finance', role='finance')
    assert first.id == retry.id
    assert db_session.query(PaymentAttempt).count() == 1
    assert db_session.get(PilotRecord, 'P-1').state == 'Payment Initiated'


def test_payment_cannot_be_initiated_before_invoice_approval(db_session):
    _create(db_session)
    with pytest.raises(LifecycleError, match='after invoice approval'):
        initiate_payment(db_session, 'P-1', 'early-key', actor='Finance', role='finance')


def test_technically_successful_pilot_can_keep_procurement_route_unresolved(db_session):
    pilot = _create(db_session)
    for state in LIFECYCLE_STATES[1:10]:
        pilot = transition_pilot(db_session, pilot.id, state, actor='Reviewer', role='Officer')
    pilot.procurement_route = 'Unresolved'
    db_session.commit()
    assert pilot.state == 'Validated'
    assert pilot.procurement_route == 'Unresolved'


def test_audit_chain_verifies_and_tampering_is_detected(db_session):
    _create(db_session)
    transition_pilot(db_session, 'P-1', 'Published', actor='Officer A', role='Officer', reason='Approved for publication')
    assert verify_audit_chain(db_session, 'P-1').valid is True

    event = db_session.scalar(select(AuditEvent).where(AuditEvent.sequence == 1))
    assert event is not None
    db_session.execute(text('DROP TRIGGER lifecycle_audit_no_update'))
    event.reason = 'Tampered reason'
    db_session.commit()

    verification = verify_audit_chain(db_session, 'P-1')
    assert verification.valid is False
    assert verification.first_broken_sequence == 1


def test_audit_verify_endpoint_reports_tamper(db_session, client):
    _create(db_session)
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.sequence == 1))
    assert event is not None
    db_session.execute(text('DROP TRIGGER lifecycle_audit_no_update'))
    event.actor = 'modified in database'
    db_session.commit()

    response = client.get('/api/audit/verify', params={'pilot_id': 'P-1'})
    assert response.status_code == 200
    assert response.json()['valid'] is False
    assert response.json()['first_broken_sequence'] == 1


def test_audit_event_records_actor_role_reason_and_states(db_session):
    _create(db_session)
    transition_pilot(db_session, 'P-1', 'Published', actor='Reviewer', role='Evaluator', reason='Brief checked')
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.sequence == 2))
    assert event is not None
    assert (event.actor, event.role, event.reason) == ('Reviewer', 'Evaluator', 'Brief checked')
    assert (event.before_state, event.after_state) == ('Draft', 'Published')
    assert len(event.previous_hash) == 64
    assert len(event.event_hash) == 64


def test_audit_verify_endpoint_note(client):
    response = client.get('/api/audit/verify')
    assert response.status_code == 200
    assert response.json()['note'] == 'Hashes detect changes. They do not prove a measurement was truthful.'


def test_policy_matrix_and_lifecycle_roles_are_explicit():
    role_names = {'officer', 'startup', 'evaluator', 'validator', 'finance', 'district'}
    assert set(LIFECYCLE_TRANSITION_ACTIONS.values()) <= set(POLICY)
    for action, allowed in POLICY.items():
        assert allowed <= role_names
        for role in role_names:
            user = OIDCUserInfo(sub='test-user', email='user@example.test', name='Test User', role=role)
            if role in allowed:
                enforce_action(user, action)
            else:
                with pytest.raises(Exception):
                    enforce_action(user, action)


def test_application_audit_hash_chain_detects_changes_and_keeps_rows_append_only(db_session):
    write_audit_event(db_session, None, 'system', 'test.one', 'Test', '1', 'Original')
    write_audit_event(db_session, None, 'system', 'test.two', 'Test', '2', 'Next')
    assert verify_record_audit_chain(db_session).valid
    event = db_session.query(RecordAuditEvent).order_by(RecordAuditEvent.occurred_at, RecordAuditEvent.id).first()
    db_session.execute(text('DROP TRIGGER audit_no_update'))
    event.detail = 'changed'
    db_session.commit()
    report = verify_record_audit_chain(db_session)
    assert report.valid is False
    assert report.checked_events == 0
    assert report.first_broken_event_id == str(event.id)


def test_application_audit_rows_reject_update_and_delete(db_session):
    event = write_audit_event(db_session, None, 'system', 'test.one', 'Test', '1', 'Original')
    with pytest.raises(Exception):
        event.detail = 'overwrite'
        db_session.commit()
    db_session.rollback()
    with pytest.raises(Exception):
        db_session.delete(event)
        db_session.commit()
    db_session.rollback()
