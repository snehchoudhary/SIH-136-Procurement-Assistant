from sqlalchemy import Column, String, DateTime, ForeignKey, text, func
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
