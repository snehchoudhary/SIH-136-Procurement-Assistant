from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, JSON
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
