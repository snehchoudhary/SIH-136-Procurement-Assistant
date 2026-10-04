import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\backend")
files = {}

files["alembic.ini"] = """[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = sqlite:///./test.db
"""

files["alembic/env.py"] = """import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.db.base import Base
import app.models  # imports all models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

files["alembic/versions/0001_initial.py"] = """\"\"\"initial

Revision ID: 0001
Revises: 
Create Date: 2026-10-03 01:00:00.000000

\"\"\"
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Let alembic autogenerate schema typically, but we also add the triggers manually
    op.execute(\"\"\"
    CREATE OR REPLACE FUNCTION audit_immutable() RETURNS trigger LANGUAGE plpgsql AS
    $$ BEGIN RAISE EXCEPTION 'audit_event rows are immutable'; END; $$;
    \"\"\")
    op.execute(\"\"\"
    CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_event FOR EACH ROW EXECUTE FUNCTION audit_immutable();
    \"\"\")
    op.execute(\"\"\"
    CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_event FOR EACH ROW EXECUTE FUNCTION audit_immutable();
    \"\"\")

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_no_delete ON audit_event")
    op.execute("DROP TRIGGER IF EXISTS audit_no_update ON audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit_immutable()")
"""

files["scripts/seed.py"] = """import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
import app.models
from app.core.config import settings
from app.models.user import User
from app.models.challenge import Challenge, ChallengeVersion
from app.models.startup import Startup, EligibilityCheck
from app.models.transfer import DistrictProfile
from app.models.policy import PolicySource
from app.core.audit_helper import write_audit_event

engine = create_engine(settings.database_url)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

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
"""

files["tests/conftest.py"] = """import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.security import create_access_token

os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

engine = create_engine(os.environ["TEST_DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def db():
    db = TestingSessionLocal()
    
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
        token = create_access_token(data={"sub": str(user.id), "email": user.email, "name": user.full_name, "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    return _get_headers
"""

files["tests/test_permissions.py"] = """import pytest

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
"""

for path, content in files.items():
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
print("Fifth batch created.")
