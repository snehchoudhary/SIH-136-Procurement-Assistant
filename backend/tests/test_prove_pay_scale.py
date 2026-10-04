from datetime import date
from uuid import UUID, uuid4

from app.models.challenge import Challenge
from app.models.evidence_verification import EvidenceUpload, EvidenceVersion2, KPIResult2, ValidatorDecision
from app.services.evidence_invalidation import measurement_plan_fingerprint, measurement_plan_for_version
from app.models.organisation import Organisation
from app.models.payment import Invoice, PaymentRecord
from app.models.pilot import AgreementVersion, Milestone, PilotAgreement
from app.models.startup import Startup
from app.models.user import User
from app.api.routes.transfer_assessment import _evaluate
from app.workflow.models import PilotRecord


def _demo_conditions(bandwidth):
    source = {
        'capacity_per_day': 100, 'bandwidth_mbps': 2.0,
        'language_mix': {'Marathi': .8, 'Hindi': .2},
        'language_sample_counts': {'Marathi': 40, 'Hindi': 40}, 'min_marathi_observations': 30,
        'demonstrated_infrastructure': ['desktop', '4g'], 'demonstrated_staffing_level': 4,
        'demonstrated_security_requirements': ['role-based access'], 'product_version': 'v1.0',
    }
    receiving = {
        'daily_case_volume': 90, 'bandwidth_mbps': bandwidth,
        'language_mix': {'Marathi': .8, 'Hindi': .2}, 'infrastructure': ['desktop', '4g'],
        'staffing_level': 4, 'security_requirements': ['role-based access'], 'product_version': 'v1.0',
    }
    return source, receiving


def test_gadchiroli_bandwidth_what_if_changes_only_connectivity_to_retest():
    source, receiving = _demo_conditions(2.0)
    baseline = _evaluate(source, receiving)
    receiving['bandwidth_mbps'] = .8
    constrained = _evaluate(source, receiving)
    before = next(row for row in baseline['findings'] if row['dimension'] == 'connectivity')
    after = next(row for row in constrained['findings'] if row['dimension'] == 'connectivity')
    assert before['decision'] == 'Evidence reusable'
    assert after['decision'] == 'Additional test needed'
    assert after['additional_test'] == 'Low-bandwidth retest'
    assert '0.8 Mbps is below' in after['reason']
    assert constrained['technical_suitability'] == 'Additional test needed'


def test_excluded_evidence_is_not_misreported_as_reusable():
    source, receiving = _demo_conditions(2.0)
    result = _evaluate(source, receiving, {'connectivity': False})
    row = next(item for item in result['findings'] if item['dimension'] == 'connectivity')
    assert row['decision'] == 'Not demonstrated'


def test_payment_states_cannot_be_set_by_generic_lifecycle_endpoint(client, db, auth_headers):
    db.add(PilotRecord(id='blocked-payment-shortcut', state='Accepted'))
    db.commit()
    response = client.post('/api/pilots/blocked-payment-shortcut/transition',
        json={'target': 'Invoice Approved'}, headers=auth_headers('finance'))
    assert response.status_code == 409
    assert 'dedicated evidence or finance endpoint' in response.json()['detail']


def test_legacy_payment_endpoint_requires_a_milestone_invoice(client, db, auth_headers):
    db.add(PilotRecord(id='blocked-legacy-payment', state='Invoice Approved'))
    db.commit()
    response = client.post('/api/pilots/blocked-legacy-payment/payments',
        json={'idempotency_key': 'legacy-test-token'}, headers=auth_headers('finance'))
    assert response.status_code == 409
    assert 'approved milestone invoice' in response.json()['detail']


def test_invoice_and_payment_states_advance_only_in_order(client, db, auth_headers, monkeypatch, tmp_path):
    import app.api.routes.payments as finance_routes
    monkeypatch.setattr(finance_routes, '_INVOICE_DIR', tmp_path)
    startup_user = db.query(User).filter_by(role='startup').first()
    validator = db.query(User).filter_by(role='validator').first()
    officer = db.query(User).filter_by(role='officer').first()
    if startup_user.organisation_id is None:
        org = Organisation(id=uuid4(), name=f'Payment integration {uuid4()}', org_type='startup')
        db.add(org); db.flush(); startup_user.organisation_id = org.id
    startup = Startup(id=uuid4(), name='Synthetic Payment Applicant', city='Gadchiroli', sector='Public service',
        founded_year=2022, annual_turnover_lakhs=10, dpiit_recognised=True,
        organisation_id=startup_user.organisation_id)
    challenge = Challenge(id=f'PAY-{uuid4().hex[:8]}', title='Payment order test', department='Demo', district='Gadchiroli',
        sector='Public service', status='Open', published_by=officer.id)
    db.add_all([startup, challenge]); db.flush()
    agreement = PilotAgreement(id=f'payment-{uuid4()}', challenge_id=challenge.id, startup_id=startup.id,
        status='Approved', approved_by=officer.id, created_by=officer.id, terms_accepted=True, approval_chain=[])
    db.add(agreement); db.flush()
    db.add(AgreementVersion(agreement_id=agreement.id, version=1, baseline_minutes=40, target_pct=20,
        error_limit_pct=5, marathi_accuracy_pct=80, min_observations=10, min_marathi_observations=5,
        bandwidth_mbps=2, capacity_per_day=100, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        revised_by=officer.id, approved=True))
    milestone = Milestone(agreement_id=agreement.id, code='PAY-M1', title='Synthetic accepted milestone', amount=10000,
        status='Accepted', evidence_requirements=[], acceptance_criteria=[], linked_kpis=[], lifecycle_state='Validated')
    db.add(milestone); db.flush()
    upload_id = str(uuid4())
    upload = EvidenceUpload(id=upload_id, pilot_agreement_id=agreement.id, submitted_by=str(startup_user.id),
        original_filename='accepted.csv', sha256_hash='a'*64, file_path='unused.csv', row_count=10,
        file_size_bytes=120, upload_status='ready')
    db.add(upload); db.flush()
    agreement_version = db.query(AgreementVersion).filter_by(agreement_id=agreement.id).one()
    db.add(EvidenceVersion2(upload_id=upload_id, agreement_id=agreement.id, version_number=1,
        sha256_hash='a'*64, is_current=True,
        metric_definition_hash=measurement_plan_fingerprint(measurement_plan_for_version(agreement_version))))
    db.add(KPIResult2(upload_id=upload_id, kpi_key='reduction_pct', kpi_label='Reduction', outcome='passed',
        unit='%', explanation='Synthetic passed result.'))
    db.add(ValidatorDecision(upload_id=upload_id, validator_id=str(validator.id), action='accepted'))
    db.commit()
    finance_headers = auth_headers('finance')

    accepted = client.post(f'/api/milestones/{milestone.id}/accept-evidence', headers=auth_headers('officer'))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['state'] == 'Accepted'
    version_record = db.query(EvidenceVersion2).filter_by(upload_id=upload_id).one()
    version_record.is_current = False
    db.query(KPIResult2).filter_by(upload_id=upload_id).update({KPIResult2.is_stale: True})
    db.commit()
    stale_invoice = client.post(f'/api/milestones/{milestone.id}/invoice', headers=auth_headers('startup'),
        data={'amount': '10000'}, files={'file': ('stale.pdf', b'%PDF synthetic invoice', 'application/pdf')})
    assert stale_invoice.status_code == 409
    version_record.is_current = True
    db.query(KPIResult2).filter_by(upload_id=upload_id).update({KPIResult2.is_stale: False})
    db.query(Milestone).filter(Milestone.id == milestone.id).update({Milestone.lifecycle_state: 'Accepted'})
    db.commit()
    early_payment = client.post(f'/api/milestones/{milestone.id}/initiate-payment?invoice_id={uuid4()}&idempotency_key=early', headers=finance_headers)
    assert early_payment.status_code == 404

    uploaded = client.post(f'/api/milestones/{milestone.id}/invoice', headers=auth_headers('startup'),
        data={'amount': '10000', 'reference': 'SYN-INV-001'}, files={'file': ('invoice.pdf', b'%PDF synthetic invoice', 'application/pdf')})
    assert uploaded.status_code == 200, uploaded.text
    invoice_id = uploaded.json()['invoice_id']
    approved = client.post(f'/api/milestones/{milestone.id}/approve-invoice?invoice_id={invoice_id}', headers=finance_headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()['state'] == 'Invoice Approved'

    initiated = client.post(f'/api/milestones/{milestone.id}/initiate-payment?invoice_id={invoice_id}&idempotency_key=payment-once', headers=finance_headers)
    assert initiated.status_code == 200, initiated.text
    payment_id = initiated.json()['payment_id']
    assert initiated.json()['simulated'] is True
    assert initiated.json()['banner'] == 'Simulated settlement. No real funds move.'
    retried = client.post(f'/api/milestones/{milestone.id}/initiate-payment?invoice_id={invoice_id}&idempotency_key=payment-once', headers=finance_headers)
    assert retried.json()['payment_id'] == payment_id
    confirmed = client.post(f'/api/milestones/{milestone.id}/confirm-payment?payment_id={payment_id}', headers=finance_headers)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['state'] == 'Payment Confirmed'
    assert db.get(PaymentRecord, UUID(payment_id)).status == 'Confirmed'
    assert db.get(Invoice, UUID(invoice_id)).approval_status == 'Approved'
    public = client.get(f'/api/verify/{agreement.id}')
    assert public.status_code == 200, public.text
    assert public.json()['summary']['project'] == 'Payment order test'
    assert 'startup_id' not in public.json()
    package = client.get(f'/api/passports/{agreement.id}/decision-package.pdf', headers=finance_headers)
    assert package.status_code == 200
    assert package.content.startswith(b'%PDF-1.4') and package.content.endswith(b'%%EOF')
    portable = client.get(f'/api/passports/{agreement.id}/export.json', headers=finance_headers)
    assert portable.status_code == 200
    assert portable.json()['milestones_and_payments'][0]['payment']['simulated'] is True
