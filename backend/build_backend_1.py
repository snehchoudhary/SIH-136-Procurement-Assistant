import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\backend")

files = {}

files["requirements.txt"] = """fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
sqlalchemy==2.0.35
alembic==1.13.3
psycopg[binary]==3.2.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.12
httpx==0.27.2
pytest==8.3.3
pytest-asyncio==0.24.0
anyio==4.6.0
"""

files["app/db/__init__.py"] = ""

files["app/db/base.py"] = """from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
"""

files["app/db/session.py"] = """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""

files["app/models/__init__.py"] = """from app.db.base import Base
from .user import User
from .organisation import Organisation
from .challenge import Challenge, ChallengeVersion
from .startup import Startup, EligibilityCheck, Application
from .evaluation import RubricVersion, ConflictDeclaration, Evaluation
from .pilot import PilotAgreement, AgreementVersion, Milestone
from .evidence import EvidenceFile, EvidenceVersion, KPIResult
from .payment import ValidationReview, Invoice, PaymentRecord
from .transfer import DistrictProfile, TransferAssessment
from .policy import PolicySource
from .audit import AuditEvent
"""

files["app/models/user.py"] = """from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    organisation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organisations.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/organisation.py"] = """from sqlalchemy import Column, String, DateTime, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class Organisation(Base):
    __tablename__ = 'organisations'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String)
    org_type: Mapped[str] = mapped_column(String)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/challenge.py"] = """from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import date, datetime
from app.db.base import Base

class Challenge(Base):
    __tablename__ = 'challenges'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String)
    district: Mapped[str] = mapped_column(String)
    sector: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    published_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ChallengeVersion(Base):
    __tablename__ = 'challenge_versions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    version: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String)
    budget: Mapped[int] = mapped_column(Integer)
    target_pct: Mapped[float] = mapped_column(Float)
    deadline: Mapped[date] = mapped_column(Date)
    metric: Mapped[str] = mapped_column(String)
    effective_from: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
"""

for path, content in files.items():
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
print("First batch of models created.")
