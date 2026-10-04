from sqlalchemy import Column, String, Date, DateTime, text, func
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
