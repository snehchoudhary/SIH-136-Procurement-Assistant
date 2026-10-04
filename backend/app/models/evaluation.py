from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, text, func, JSON
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
    criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    published_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ConflictDeclaration(Base):
    __tablename__ = 'conflict_declarations'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    evaluator_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'))
    has_conflict: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str] = mapped_column(String, default='', nullable=False)
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
    submitted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CommitteeDecision(Base):
    __tablename__ = 'committee_decisions'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    challenge_id: Mapped[str] = mapped_column(String, ForeignKey('challenges.id'), nullable=False)
    startup_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('startups.id'), nullable=False)
    recorded_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    dissent: Mapped[str] = mapped_column(String, default='', nullable=False)
    responsibilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
