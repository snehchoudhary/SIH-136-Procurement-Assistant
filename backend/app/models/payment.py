from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, text, func, JSON
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
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_status: Mapped[str] = mapped_column(String, default='Submitted', nullable=False)
    approved_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class PaymentRecord(Base):
    __tablename__ = 'payment_records'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    invoice_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('invoices.id'))
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    approved_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
