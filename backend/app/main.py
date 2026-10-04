from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import ColumnDefault, text
from sqlalchemy.orm import Session
from app.api.routes import health, auth, challenges, startups, evaluations, pilots, evidence, payments, policies, audit, discovery
from app.api.routes.evidence_verification import router as evidence_v2_router
from app.api.routes.demo_evidence import router as demo_evidence_router
from app.api.routes.transfer_assessment import router as transfer_router
from app.api.routes.passport import router as passport_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.user import Role, User
from app.models.challenge import Challenge
from app.models.startup import Startup
from app.models.pilot import PilotAgreement, AgreementVersion, Milestone
from app.models.organisation import Organisation
from app.core.passwords import hash_password
from uuid import uuid4
from datetime import date
from app.workflow import models as workflow_models  # noqa: F401
from app.workflow.routes import router as workflow_router
tags_metadata = [
    {"name": "Officer", "description": "Officer workflows: challenge publication, eligibility verification, pilot approval, and recorded decisions."},
    {"name": "Startup Applicant", "description": "Applicant workflows: organization-scoped applications, evidence submissions, and invoices."},
    {"name": "Evaluator", "description": "Evaluator workflows: conflict-guarded scoring and evaluation review."},
    {"name": "Validator", "description": "Validator workflows: independent evidence checks and transfer assessments."},
    {"name": "Finance", "description": "Finance workflows: invoice approval and payment status recording."},
    {"name": "Receiving District", "description": "Receiving district workflows: transfer readiness and local adoption review."},
    {"name": "auth", "description": "Authentication — all roles"},
    {"name": "challenges", "description": "Challenges — Officer publishes, all read"},
    {"name": "startups", "description": "Startups — Officer verifies eligibility"},
    {"name": "evaluations", "description": "Evaluations — Evaluator only (conflict-guarded)"},
    {"name": "pilots", "description": "Pilots — Officer approves and revises"},
    {"name": "evidence", "description": "Evidence — Startup submits, Validator reviews"},
    {"name": "payments", "description": "Payments — Finance approves (startup invoices)"},
    {"name": "policies", "description": "Policies — All roles read-only"},
    {"name": "audit", "description": "Audit log — Officer, Validator, Finance"},
    {"name": "health", "description": "Health check"},
]

app = FastAPI(
    title='PilotProof API',
    version='1.0.0',
    docs_url='/api/docs',
    redoc_url='/api/redoc',
    openapi_url='/api/openapi.json',
    openapi_tags=tags_metadata,
)

_cors_origins = ['*'] if settings.app_env.lower() in {'development', 'dev', 'local'} else ['http://localhost:5173', 'http://127.0.0.1:5173']
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["challenges"])
app.include_router(discovery.router)
app.include_router(startups.router, prefix="/api/startups", tags=["startups"])
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["evaluations"])
app.include_router(pilots.router, prefix="/api/pilots", tags=["pilots"])
app.include_router(evidence.router, prefix="/api", tags=["evidence"])
app.include_router(payments.router, prefix="/api/milestones", tags=["payments"])
app.include_router(policies.router, prefix="/api/policies", tags=["policies"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(workflow_router)
app.include_router(evidence_v2_router)
app.include_router(demo_evidence_router)
app.include_router(transfer_router)
app.include_router(passport_router)


@app.on_event("startup")
def create_database_tables() -> None:
    settings.validate_runtime_configuration()
    if settings.app_env != "test":
        if engine.dialect.name == 'sqlite':
            for table in Base.metadata.tables.values():
                for column in table.columns:
                    if column.server_default is not None and str(column.server_default.arg) == 'gen_random_uuid()':
                        column.server_default = None
                        column.default = ColumnDefault(uuid4)
        Base.metadata.create_all(bind=engine)
        if engine.dialect.name == 'sqlite':
            # create_all does not evolve an existing local demo database.
            with engine.begin() as connection:
                columns = {row[1] for row in connection.execute(text('PRAGMA table_info(evidence_versions2)'))}
                if columns and 'metric_definition_hash' not in columns:
                    connection.execute(text("ALTER TABLE evidence_versions2 ADD COLUMN metric_definition_hash VARCHAR(64) NOT NULL DEFAULT ''"))
                if columns and 'measurement_plan_snapshot' not in columns:
                    connection.execute(text("ALTER TABLE evidence_versions2 ADD COLUMN measurement_plan_snapshot JSON NOT NULL DEFAULT '{}'"))
                kpi_columns = {row[1] for row in connection.execute(text('PRAGMA table_info(kpi_results2)'))}
                if kpi_columns and 'python_code' not in kpi_columns:
                    connection.execute(text("ALTER TABLE kpi_results2 ADD COLUMN python_code VARCHAR NOT NULL DEFAULT ''"))
                if kpi_columns and 'is_stale' not in kpi_columns:
                    connection.execute(text("ALTER TABLE kpi_results2 ADD COLUMN is_stale BOOLEAN NOT NULL DEFAULT 0"))
                connection.execute(text("CREATE TABLE IF NOT EXISTS evidence_review_threads (id VARCHAR(36) PRIMARY KEY, upload_id VARCHAR(36) NOT NULL REFERENCES evidence_uploads(id), agreement_id VARCHAR NOT NULL REFERENCES pilot_agreements(id), created_by VARCHAR(36) NOT NULL REFERENCES users(id), subject VARCHAR NOT NULL, initial_message VARCHAR NOT NULL, status VARCHAR NOT NULL DEFAULT 'open', created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"))
                additions = {
                    'district_profiles': {'language_mix': "JSON NOT NULL DEFAULT '{}'", 'infrastructure': "JSON NOT NULL DEFAULT '[]'", 'staffing_level': 'INTEGER NOT NULL DEFAULT 0', 'security_requirements': "JSON NOT NULL DEFAULT '[]'", 'product_version': "VARCHAR NOT NULL DEFAULT 'unknown'", 'simulated': 'BOOLEAN NOT NULL DEFAULT 0'},
                    'transfer_assessments': {'technical_suitability': "VARCHAR NOT NULL DEFAULT 'Not demonstrated'", 'procurement_route_status': "VARCHAR NOT NULL DEFAULT 'Not assessed'", 'source_snapshot': "JSON NOT NULL DEFAULT '{}'", 'receiving_snapshot': "JSON NOT NULL DEFAULT '{}'", 'created_milestone_ids': "JSON NOT NULL DEFAULT '[]'"},
                    'invoices': {'storage_path': 'VARCHAR', 'content_sha256': 'VARCHAR(64)', 'approval_status': "VARCHAR NOT NULL DEFAULT 'Submitted'", 'approved_by': 'CHAR(32)', 'approved_at': 'DATETIME'},
                    'payment_records': {'reference': 'VARCHAR', 'simulated': 'BOOLEAN NOT NULL DEFAULT 1', 'details': "JSON NOT NULL DEFAULT '{}'"},
                    'payment_attempts': {'reference': 'VARCHAR(100)', 'simulated': 'BOOLEAN NOT NULL DEFAULT 1'},
                }
                for table, fields in additions.items():
                    existing = {row[1] for row in connection.execute(text(f'PRAGMA table_info({table})'))}
                    if existing:
                        for name, definition in fields.items():
                            if name not in existing:
                                connection.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
        if settings.seed_demo_users:
            seed_demo_accounts()
            seed_demo_evidence_agreement()
        if engine.dialect.name == 'sqlite':
            with engine.begin() as connection:
                connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
                connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
                connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))
                connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))


def seed_demo_accounts() -> None:
    if not settings.is_local:
        raise RuntimeError('Synthetic demo accounts may only be seeded in local development.')
    """Ensure the documented demo credentials work in a fresh local install."""
    accounts = [
        ('officer', 'Officer', 'officer@pilotproof.dev', 'Officer Priya Sharma', 'MSInS Demo Department', 'department'),
        ('startup', 'Startup Applicant', 'startup@pilotproof.dev', 'Startup Arjun Mehta', 'Vidarbha Civic Tech (Synthetic)', 'startup'),
        ('evaluator', 'Evaluator', 'evaluator@pilotproof.dev', 'Expert Kavita Nair', 'MSInS Evaluation Panel', 'department'),
        ('validator', 'Validator', 'validator@pilotproof.dev', 'Validator Rajan Patel', 'Independent Validation Body', 'department'),
        ('finance', 'Finance', 'finance@pilotproof.dev', 'Finance Deepa Rao', 'MSInS Finance Desk', 'department'),
        ('district', 'Receiving District', 'district@pilotproof.dev', 'District Collector Suresh Bhat', 'Pune Urban Receiving District', 'department'),
    ]
    with Session(engine) as db:
        for role, label, email, name, organisation_name, organisation_type in accounts:
            if db.get(Role, role) is None:
                db.add(Role(name=role, label=label, description=f'{label} synthetic demonstration account.'))
        db.flush()
        for role, _, email, name, organisation_name, organisation_type in accounts:
            organisation = db.query(Organisation).filter_by(name=organisation_name).first()
            if organisation is None:
                organisation = Organisation(id=uuid4(), name=organisation_name, org_type=organisation_type, district='Maharashtra')
                db.add(organisation)
                db.flush()
            user = db.query(User).filter_by(email=email).first()
            if user is None:
                db.add(User(id=uuid4(), email=email, full_name=name, role=role,
                            hashed_password=hash_password('demo1234'), organisation_id=organisation.id))
            else:
                user.role = role
                user.organisation_id = organisation.id
                if not user.hashed_password or not user.hashed_password.startswith('pbkdf2_sha256$'):
                    user.hashed_password = hash_password('demo1234')
        db.commit()


def seed_demo_evidence_agreement() -> None:
    """Create the stable synthetic pilot used by the evidence workspace."""
    with Session(engine) as db:
        startup_user = db.query(User).filter_by(email='startup@pilotproof.dev').first()
        officer = db.query(User).filter_by(email='officer@pilotproof.dev').first()
        if not startup_user or not officer:
            return
        agreement = db.get(PilotAgreement, 'demo-agreement')
        if agreement is not None:
            plan = db.query(AgreementVersion).filter_by(agreement_id=agreement.id, approved=True).order_by(AgreementVersion.version.desc()).first()
            if plan is not None:
                clauses = dict(plan.clauses or {})
                clauses.setdefault('product_version', 'v1.0')
                clauses.setdefault('demonstrated_infrastructure', ['desktop', '4g'])
                clauses.setdefault('demonstrated_staffing_level', 4)
                clauses.setdefault('demonstrated_security_requirements', ['role-based access'])
                plan.clauses = clauses
                db.commit()
            milestone = db.query(Milestone).filter_by(agreement_id=agreement.id, code='M1').first()
            if milestone is not None and milestone.amount == 0:
                milestone.amount = 125000
                db.commit()
            return
        challenge_id = 'MH-MUNI-SC-001'
        if db.get(Challenge, challenge_id) is None:
            db.add(Challenge(id=challenge_id, title='Municipal Service-Centre Wait-Time Pilot (Synthetic)',
                department='Maharashtra State Innovation Society', district='Pune Urban', sector='Public service',
                status='Open', published_by=officer.id, measurement_locked=True))
            db.flush()
        startup = db.query(Startup).filter_by(organisation_id=startup_user.organisation_id).first()
        if startup is None:
            startup = Startup(name='Vidarbha Civic Tech (Synthetic)', city='Nagpur', sector='Public service',
                founded_year=2022, annual_turnover_lakhs=32, dpiit_recognised=True,
                organisation_id=startup_user.organisation_id, capability_tags=['service routing'],
                domain_experience='Synthetic demo profile', languages_supported=['Marathi', 'Hindi', 'English'],
                deployment_readiness='Synthetic demo only', evidence_snippets=[])
            db.add(startup)
            db.flush()
        agreement = PilotAgreement(id='demo-agreement', challenge_id=challenge_id, startup_id=startup.id,
            status='Approved', approved_by=officer.id, created_by=officer.id, terms_accepted=True, approval_chain=[])
        db.add(agreement)
        db.flush()
        db.add(AgreementVersion(agreement_id=agreement.id, version=1, baseline_minutes=45,
            target_pct=30, error_limit_pct=5, marathi_accuracy_pct=85, min_observations=100,
            min_marathi_observations=30, bandwidth_mbps=2, capacity_per_day=100,
            start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), revised_by=officer.id,
            template_key='evidence-demo', template_version=1, clauses={
                'product_version': 'v1.0', 'demonstrated_infrastructure': ['desktop', '4g'],
                'demonstrated_staffing_level': 4, 'demonstrated_security_requirements': ['role-based access'],
            },
            change_note='Locked synthetic evidence demo measurement plan', approved=True))
        db.add(Milestone(agreement_id=agreement.id, code='M1', title='Verified pilot outcomes', amount=125000,
            status='Pending', evidence_requirements=['CSV evidence'],
            acceptance_criteria=['All locked KPIs pass'], linked_kpis=['reduction_pct', 'error_rate_pct', 'marathi_accuracy_pct', 'low_bandwidth_pct'],
            lifecycle_state='Pilot Running'))
        db.commit()
