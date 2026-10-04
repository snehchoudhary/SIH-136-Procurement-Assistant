from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from uuid import uuid4
from app.db.base import Base


class EvidenceUpload(Base):
    """Represents a single uploaded CSV evidence file with its integrity metadata."""

    __tablename__ = "evidence_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pilot_agreement_id: Mapped[str] = mapped_column(String, ForeignKey("pilot_agreements.id"), nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # 'processing' | 'ready' | 'failed'
    upload_status: Mapped[str] = mapped_column(String, nullable=False, default="processing")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvidenceVersion2(Base):
    """Immutable snapshot per upload. Each new upload supersedes the previous version."""

    __tablename__ = "evidence_versions2"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_uploads.id"), nullable=False)
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey("pilot_agreements.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String, nullable=False)
    metric_definition_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    measurement_plan_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QualityFinding(Base):
    """A structured data-quality finding produced by the evidence engine."""

    __tablename__ = "quality_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_uploads.id"), nullable=False)
    # 'critical' | 'major' | 'minor' | 'info'
    severity: Mapped[str] = mapped_column(String, nullable=False)
    check_name: Mapped[str] = mapped_column(String, nullable=False)
    rows_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    # JSON list of int row indices (0-based, matching the uploaded CSV)
    row_indices: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KPIResult2(Base):
    """Engine-computed KPI result for a single upload, including delta vs claimed value."""

    __tablename__ = "kpi_results2"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_uploads.id"), nullable=False)
    kpi_key: Mapped[str] = mapped_column(String, nullable=False)
    kpi_label: Mapped[str] = mapped_column(String, nullable=False)
    claimed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    recomputed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 'passed' | 'failed' | 'missing_evidence'
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False, default="%")
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    # JSON list of human-readable strings
    calculation_steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rows_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    python_code: Mapped[str] = mapped_column(String, nullable=False, default="")
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ValidatorDecision(Base):
    """A validator's formal decision (accept / dispute / request correction) on an upload."""

    __tablename__ = "validator_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_uploads.id"), nullable=False)
    validator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    # 'accepted' | 'disputed' | 'correction_requested'
    action: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    thread_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EvidenceReviewThread(Base):
    """Persisted correction discussion opened by a validator decision."""

    __tablename__ = "evidence_review_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    upload_id: Mapped[str] = mapped_column(String(36), ForeignKey("evidence_uploads.id"), nullable=False)
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey("pilot_agreements.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    initial_message: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
