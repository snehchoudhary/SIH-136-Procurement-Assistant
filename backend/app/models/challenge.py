from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, text, func, Boolean, JSON
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
    measurement_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ChallengeVersion(Base):
    __tablename__ = 'challenge_versions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    version: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String)
    budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    metric: Mapped[str] = mapped_column(String)
    problem_statement: Mapped[str] = mapped_column(String, default='', nullable=False)
    outcomes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    baseline: Mapped[str] = mapped_column(String, default='Baseline unavailable', nullable=False)
    test_plan: Mapped[str] = mapped_column(String, default='', nullable=False)
    test_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acceptance_criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    input_language: Mapped[str] = mapped_column(String, default='en', nullable=False)
    change_note: Mapped[str] = mapped_column(String, default='Initial version', nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
