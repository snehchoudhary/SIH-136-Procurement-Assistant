from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, JSON
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
    capability_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    domain_experience: Mapped[str] = mapped_column(String, default='Not documented', nullable=False)
    languages_supported: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deployment_readiness: Mapped[str] = mapped_column(String, default='Not documented', nullable=False)
    evidence_snippets: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ManualVerificationUpload(Base):
    __tablename__ = 'manual_verification_uploads'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'), nullable=False)
    source_adapter: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status: Mapped[str] = mapped_column(String, default='Pending human verification', nullable=False)
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
