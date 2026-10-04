import os
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Hp\Documents\Codex\2026-09-25\referenced-chatgpt-conversation-this-is-an\work\backend")

files = {}

files["app/models/startup.py"] = """from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class Startup(Base):
    __tablename__ = 'startups'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    sector: Mapped[str] = mapped_column(String)
    founded_year: Mapped[int] = mapped_column(Integer)
    annual_turnover_lakhs: Mapped[float] = mapped_column(Float)
    dpiit_recognised: Mapped[bool] = mapped_column(Boolean)
    organisation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organisations.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class EligibilityCheck(Base):
    __tablename__ = 'eligibility_checks'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    checked_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    passed: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(String)
    evidence_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Application(Base):
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    status: Mapped[str] = mapped_column(String)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/evaluation.py"] = """from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class RubricVersion(Base):
    __tablename__ = 'rubric_versions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    version: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict] = mapped_column(JSON)
    published_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ConflictDeclaration(Base):
    __tablename__ = 'conflict_declarations'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    evaluator_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    has_conflict: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(String)
    declared_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Evaluation(Base):
    __tablename__ = 'evaluations'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    application_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('applications.id'))
    rubric_version_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('rubric_versions.id'))
    evaluator_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    conflict_declaration_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('conflict_declarations.id'))
    scores: Mapped[dict] = mapped_column(JSON)
    total_score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/pilot.py"] = """from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import date, datetime
from app.db.base import Base

class PilotAgreement(Base):
    __tablename__ = 'pilot_agreements'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'))
    status: Mapped[str] = mapped_column(String)
    approved_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class AgreementVersion(Base):
    __tablename__ = 'agreement_versions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    version: Mapped[int] = mapped_column(Integer)
    baseline_minutes: Mapped[float] = mapped_column(Float)
    target_pct: Mapped[float] = mapped_column(Float)
    error_limit_pct: Mapped[float] = mapped_column(Float)
    marathi_accuracy_pct: Mapped[float] = mapped_column(Float)
    min_observations: Mapped[int] = mapped_column(Integer)
    min_marathi_observations: Mapped[int] = mapped_column(Integer)
    bandwidth_mbps: Mapped[float] = mapped_column(Float)
    capacity_per_day: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    revised_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    revised_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    revision_reason: Mapped[str | None] = mapped_column(String, nullable=True)

class Milestone(Base):
    __tablename__ = 'milestones'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    code: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
"""

files["app/models/evidence.py"] = """from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class EvidenceFile(Base):
    __tablename__ = 'evidence_files'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    agreement_version: Mapped[int] = mapped_column(Integer)
    submitted_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    filename: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class EvidenceVersion(Base):
    __tablename__ = 'evidence_versions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    evidence_file_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('evidence_files.id'))
    version: Mapped[int] = mapped_column(Integer)
    row_count: Mapped[int] = mapped_column(Integer)
    reduction_pct: Mapped[float] = mapped_column(Float)
    error_rate_pct: Mapped[float] = mapped_column(Float)
    marathi_accuracy_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    all_checks_passed: Mapped[bool] = mapped_column(Boolean)
    check_results: Mapped[list] = mapped_column(JSON)
    sha256_hash: Mapped[str] = mapped_column(String)
    limitations: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class KPIResult(Base):
    __tablename__ = 'kpi_results'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    evidence_version_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('evidence_versions.id'))
    kpi_name: Mapped[str] = mapped_column(String)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    passed: Mapped[bool] = mapped_column(Boolean)
    detail: Mapped[str] = mapped_column(String)
"""

files["app/models/payment.py"] = """from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class ValidationReview(Base):
    __tablename__ = 'validation_reviews'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    evidence_file_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('evidence_files.id'))
    reviewer_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    accepted: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(String)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Invoice(Base):
    __tablename__ = 'invoices'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    milestone_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('milestones.id'))
    submitted_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    amount: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class PaymentRecord(Base):
    __tablename__ = 'payment_records'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    invoice_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('invoices.id'))
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    approved_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/transfer.py"] = """from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class DistrictProfile(Base):
    __tablename__ = 'district_profiles'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String)
    district_type: Mapped[str] = mapped_column(String)
    daily_case_volume: Mapped[int] = mapped_column(Integer)
    bandwidth_mbps: Mapped[float] = mapped_column(Float)
    primary_language: Mapped[str] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class TransferAssessment(Base):
    __tablename__ = 'transfer_assessments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    receiving_district_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('district_profiles.id'))
    assessed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String)
    findings: Mapped[list] = mapped_column(JSON)
    procurement_note: Mapped[str] = mapped_column(String)
    assessed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/policy.py"] = """from sqlalchemy import Column, String, Date, DateTime, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import date, datetime
from app.db.base import Base

class PolicySource(Base):
    __tablename__ = 'policy_sources'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    title: Mapped[str] = mapped_column(String)
    jurisdiction: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    effective_date: Mapped[date] = mapped_column(Date)
    url: Mapped[str] = mapped_column(String)
    policy_type: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

files["app/models/audit.py"] = """from sqlalchemy import Column, String, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class AuditEvent(Base):
    __tablename__ = 'audit_event'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    actor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    actor_role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource_type: Mapped[str] = mapped_column(String)
    resource_id: Mapped[str] = mapped_column(String)
    detail: Mapped[str] = mapped_column(String)
    previous_hash: Mapped[str] = mapped_column(String)
    event_hash: Mapped[str] = mapped_column(String)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
"""

for path, content in files.items():
    full_path = BASE_DIR / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
print("Second batch of models created.")
