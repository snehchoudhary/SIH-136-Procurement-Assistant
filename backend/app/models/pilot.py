from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, text, func, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from datetime import date, datetime
from uuid import UUID as PythonUUID
from app.db.base import Base

class PilotAgreement(Base):
    __tablename__ = 'pilot_agreements'
    id: Mapped[str] = mapped_column(String, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    startup_id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('startups.id'))
    status: Mapped[str] = mapped_column(String)
    approved_by: Mapped[PythonUUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_chain: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[PythonUUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class AgreementVersion(Base):
    __tablename__ = 'agreement_versions'
    id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
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
    revised_by: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('users.id'))
    revised_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    revision_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    template_key: Mapped[str] = mapped_column(String, default='standard-pilot', nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    clauses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    change_note: Mapped[str] = mapped_column(String, default='Initial agreement draft', nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class Milestone(Base):
    __tablename__ = 'milestones'
    id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    code: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_requirements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    acceptance_criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    linked_kpis: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    planned_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    lifecycle_state: Mapped[str] = mapped_column(String, default='Agreement Approved', nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgreementTemplate(Base):
    __tablename__ = 'agreement_templates'
    id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    template_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    clauses: Mapped[dict] = mapped_column(JSON, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StartupOfficerQuestion(Base):
    __tablename__ = 'startup_officer_questions'
    id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'), nullable=False)
    author_id: Mapped[PythonUUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    author_role: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
