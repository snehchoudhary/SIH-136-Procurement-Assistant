from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PilotRecord(Base):
    __tablename__ = 'pilot_records'

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default='Draft')
    agreement_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    kpi_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    result_status: Mapped[str] = mapped_column(String(80), default='Current', nullable=False)
    procurement_route: Mapped[str] = mapped_column(String(50), default='Unresolved', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    __table_args__ = (UniqueConstraint('pilot_id', 'sequence', name='uq_audit_pilot_sequence'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pilot_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default='')
    before_state: Mapped[str] = mapped_column(String(80), nullable=False)
    after_state: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, default='transition')
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False, default='0' * 64)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PaymentAttempt(Base):
    __tablename__ = 'payment_attempts'
    __table_args__ = (UniqueConstraint('pilot_id', 'idempotency_key', name='uq_payment_pilot_idempotency'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pilot_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='Initiated')
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    simulated: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
