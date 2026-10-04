import pytest
import os
import uuid
os.environ["APP_ENV"] = "test"
from fastapi.testclient import TestClient
from sqlalchemy import ColumnDefault, create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import Role, User
from app.core.security import create_access_token
from app.workflow.models import AuditEvent, PaymentAttempt, PilotRecord

os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

engine = create_engine(
    os.environ["TEST_DATABASE_URL"],
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# PostgreSQL UUID server defaults are replaced with Python-side UUID defaults in
# this SQLite-only test schema. Production metadata and migrations are unchanged.
for table in Base.metadata.tables.values():
    for column in table.columns:
        if column.server_default is not None and str(column.server_default.arg) == 'gen_random_uuid()':
            column.server_default = None
            column.default = ColumnDefault(uuid.uuid4)

Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))
    connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db_session():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    with test_engine.begin() as connection:
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))
        connection.execute(text("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END"))
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()

@pytest.fixture(scope="session")
def db():
    db = TestingSessionLocal()

    role_rows = [
        ('officer', 'Officer', 'Publishes challenges.'),
        ('startup', 'Startup Applicant', 'Submits applications and evidence.'),
        ('evaluator', 'Evaluator', 'Scores applications.'),
        ('validator', 'Validator', 'Reviews evidence.'),
        ('finance', 'Finance', 'Approves payments.'),
        ('district', 'Receiving District', 'Reviews transfer readiness.'),
    ]
    for role_name, label, description in role_rows:
        if db.get(Role, role_name) is None:
            db.add(Role(name=role_name, label=label, description=description))
    db.commit()
    
    # seed users
    users_data = [
        ("officer@pilotproof.dev", "Officer Priya Sharma", "officer"),
        ("startup@pilotproof.dev", "Startup Arjun Mehta", "startup"),
        ("evaluator@pilotproof.dev", "Expert Kavita Nair", "evaluator"),
        ("validator@pilotproof.dev", "Validator Rajan Patel", "validator"),
        ("finance@pilotproof.dev", "Finance Deepa Rao", "finance"),
        ("district@pilotproof.dev", "District Collector Suresh Bhat", "district")
    ]
    for email, name, role in users_data:
        if not db.query(User).filter_by(email=email).first():
            u = User(email=email, full_name=name, role=role, hashed_password="demo1234")
            db.add(u)
    db.commit()
    
    yield db
    db.close()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers(db):
    def _get_headers(role: str):
        user = db.query(User).filter_by(role=role).first()
        token = create_access_token(data={"sub": str(user.id), "email": user.email, "name": user.full_name,
                                         "role": user.role,
                                         "org_id": str(user.organisation_id) if user.organisation_id else None})
        return {"Authorization": f"Bearer {token}"}
    return _get_headers
